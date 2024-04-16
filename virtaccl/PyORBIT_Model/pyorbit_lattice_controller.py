import sys
import time
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
import json

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.core.bunch import Bunch

from .pyorbit_element_controllers import PyorbitNode, PyorbitChild, PyorbitCavity
from .pyorbit_child_nodes import BPMclass, WSclass, BunchCopyClass, RF_Gap_Aperture

from virtaccl.model import Model


class OrbitModel(Model):
    """
    This is a controller that automates using the PyORBIT model for the virtual accelerator.

        Parameters
        ----------
        input_lattice : LinacAccLattice
            PyORBIT linac lattice the model uses for tracking.
        input_bunch : Bunch, optional
            PyORBIT bunch that the model will track from the entrance of the input_lattice.
        debug : bool, optional, default = False
            Setting to True has the model print additional information when used
            (when the lattice is updated, the bunch is tracked, etc.).
    """

    # This creates a hint for the element dictionary for easier development.
    _element_ref_hint = Union[PyorbitNode, PyorbitCavity, PyorbitChild]
    _element_dict_hint = Dict[str, _element_ref_hint]

    def __init__(self, input_lattice: LinacAccLattice, input_bunch: Bunch = None, debug: bool = False):
        super().__init__()
        self.debug = debug

        self.accLattice = input_lattice
        # Here we specify the node types in PyORBIT we don't need to worry about and start a set to make sure each
        # element we do care about has a unique name.
        ignored_nodes = {'baserfgap', 'drift', 'tilt', 'fringe', 'markerLinacNode', 'baseLinacNode'}
        unique_elements = set()

        # Set up a dictionary to reference different objects within the lattice by their name. Not all elements are
        # readily available in LinacAccLattice, so this lets us easily reference them.
        element_dict: OrbitModel._element_dict_hint = {}

        # This function is for digging into child nodes in PyORBIT to find nodes we need to reference. This is mainly
        # for correctors and some BPMs. If a BPM or wire scanner markerLinacNode is found, the appropriate child node is
        # attached. Waring: This uses recursion to also look at child nodes of child nodes.
        def add_child_nodes(ancestor_node, children_nodes, element_dictionary):
            for child in children_nodes:
                child_type = child.getType()
                if child_type == 'markerLinacNode':
                    child_name = child.getName()
                    if 'BPM' in child_name:
                        child.addChildNode(BPMclass(child_name), child.ENTRANCE)
                    if 'WS' in child_name:
                        child.addChildNode(WSclass(child_name), child.ENTRANCE)
                if not any(substring in child_type for substring in ignored_nodes):
                    child_name = child.getName()
                    if child_name not in unique_elements:
                        unique_elements.add(child_name)
                        element_dictionary[child_name] = PyorbitChild(child, ancestor_node)
                grandchildren = child.getAllChildren()
                if len(grandchildren) > 0:
                    add_child_nodes(ancestor_node, grandchildren, element_dictionary)

        # Goes through the list of nodes in the LinacAccLattice and adds them to the dictionary. If a BPM or wire
        # scanner markerLinacNode is found, the appropriate child node is attached. If the node has any child nodes, the
        # add_child_nodes function is called.
        list_of_nodes = self.accLattice.getNodes()
        for node in list_of_nodes:
            node_type = node.getType()
            if node_type == 'markerLinacNode':
                node_name = node.getName()
                if 'BPM' in node_name:
                    node.addChildNode(BPMclass(node_name), node.ENTRANCE)
                if 'WS' in node_name:
                    node.addChildNode(WSclass(node_name), node.ENTRANCE)
            if not any(substring in node_type for substring in ignored_nodes):
                element_name = node.getName()
                if element_name not in unique_elements:
                    unique_elements.add(element_name)
                    element_dict[element_name] = PyorbitNode(node)
            children = node.getAllChildren()
            if len(children) > 0:
                add_child_nodes(node, children, element_dict)

        # Goes through the list of accelerating cavities in the LinacAccLattice and adds them to the dictionary.
        list_of_cavities = self.accLattice.getRF_Cavities()
        for cavity in list_of_cavities:
            element_name = cavity.getName()
            unique_elements.add(element_name)
            element_dict[element_name] = PyorbitCavity(cavity)

            # Adds a longitudinal aperture for the bunch based on the xml files allowed beta range.
            # gap_ent = element_dict[element_name].get_first_node()
            # beta_min, beta_max = gap_ent.getBetaMinMax()
            # gap_ent.addChildNode(RF_Gap_Aperture('long_apt', beta_min, beta_max), gap_ent.BEFORE)

        self.pyorbit_dictionary = element_dict

        # Sets up a dictionary of bunches at each optics element. This dictionary is referenced whenever an optic
        # changes so that the bunch can be re-tracked from that optic instead of the beginning. It also attaches to each
        # optic the BunchCopyClass as a child node which saves the bunch within the dictionary.
        self.bunch_dict = {'initial_bunch': Bunch()}
        for element_name, element_ref in self.pyorbit_dictionary.items():
            location_node = element_ref.get_tracking_node()
            if element_name not in self.bunch_dict:
                self.bunch_dict[element_name] = Bunch()
                location_node.addChildNode(BunchCopyClass(element_name, self.bunch_dict), location_node.ENTRANCE)

        # A dictionary used in tracking to keep track of parameters useful to the model.
        self.model_params = {}
        self.bunch_flag = False

        if input_bunch is not None:
            self.set_initial_bunch(input_bunch)

        # Set up variable to track where the most upstream change is located.
        self.current_changes = set()
        # Store initial settings
        self.initial_optics = self.get_settings()

    def set_initial_bunch(self, initial_bunch: Bunch, beam_current: float = 40e-3):
        """Designate an input PyORBIT bunch for the lattice. This bunch is then tracked through the lattice from the
        beginning.

        Parameters
        ----------
        initial_bunch : Bunch
            PyORBIT bunch that the model will track from the entrance of the input_lattice.
        beam_current : float, optional
            The beam current in Amps.
        """

        initial_bunch.getSyncParticle().time(0.0)
        initial_bunch.copyBunchTo(self.bunch_dict['initial_bunch'])
        self.set_beam_current(beam_current)
        self.model_params['initial_particle_number'] = initial_bunch.getSizeGlobal()
        self.bunch_flag = True

        self.accLattice.trackDesignBunch(initial_bunch)
        self.force_track()

    def set_beam_current(self, beam_current: float):
        """Set the beam current for the initial bunch.

        Parameters
        ----------
        beam_current : float, optional
            The beam current in Amps.
        """

        self.model_params['beam_current'] = beam_current

    def get_element_list(self) -> list[str]:
        """Returns a list of all element key names currently maintained in the model.

        Results
        ----------
        out : list[string]
            List of all element names currently in the model.
        """

        key_list = []
        for element_key in self.pyorbit_dictionary.keys():
            key_list.append(element_key)
        return key_list

    def get_element_dictionary(self) -> _element_dict_hint:
        """Returns a dictionary of the PyORBIT model elements.

        Results
        ----------
        out : dictionary
            Dictionary with the element name as the key and the element model class (PyorbitNode, PyorbitChild, or
            PyorbitCavity) as the value.
        """

        return self.pyorbit_dictionary

    def get_parameter(self, element_name: str, parameter_key: str):
        """Returns a parameter value for an element in the model.

        Parameters
        ----------
        element_name : string
            The name of the element whose parameter you want.
        parameter_key : string
            The key for the parameter you want.

        Returns
        ----------
        out : parameter
            The value of the parameter in the element's dictionary.
        """

        pyorbit_dict = self.pyorbit_dictionary
        if element_name not in pyorbit_dict.keys():
            print(f'The element "{element_name}" is not in the model.')
        elif parameter_key not in pyorbit_dict[element_name].get_parameter_dict().keys():
            print(f'Parameter key "{parameter_key}" not found in PyORBIT element "{element_name}".')
        else:
            return pyorbit_dict[element_name].get_parameter(parameter_key)

    def get_element_parameters(self, element_name: str) -> Dict[str, Any]:
        """Returns a parameter dictionary for an element in the model.

        Parameters
        ----------
        element_name : string
            The name of the element whose parameter dictionary you want.

        Returns
        ----------
        out : dictionary
            The parameter dictionary for the element.
        """

        pyorbit_dict = self.pyorbit_dictionary
        if element_name not in pyorbit_dict.keys():
            print(f'The element "{element_name}" is not in the model.')
        else:
            return pyorbit_dict[element_name].get_parameter_dict()

    def get_model_parameters(self, element_names: list[str] = None) -> Dict[str, Dict[str, Any]]:
        """Returns a parameter dictionary for multiple elements in the model.

        Parameters
        ----------
        element_names : list[string], optional
            List of the names of the elements whose parameter dictionaries you want. If nothing is provided, the
            dictionary includes all elements in the model.

        Returns
        ----------
        out : dictionary
            A dictionary of element names as keys connected to that element's parameter dictionary.
        """

        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        bad_names = []
        good_names = []

        if element_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                good_names.append(element_name)
        else:
            for element_name in element_names:
                if element_name not in pyorbit_dict.keys():
                    bad_names.append(element_name)
                else:
                    good_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model: {", ".join(bad_names)}.')

        for element_name in good_names:
            return_dict[element_name] = pyorbit_dict[element_name].get_parameter_dict()

        return return_dict

    def get_settings(self, setting_names: list[str] = None) -> Dict[str, Dict[str, Any]]:
        """Returns a parameter dictionary for the setting elements in the model.

        Parameters
        ----------
        setting_names : list[string], optional
            List of the names of the optics elements whose parameter dictionaries you want. If nothing is provided, the
            dictionary includes all optics elements in the model.

        Returns
        ----------
        out : dictionary
            A dictionary of element names as keys connected to that element's parameter dictionary.
        """

        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        bad_names = []
        good_names = []

        if setting_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                if element_ref.is_optic():
                    good_names.append(element_name)
        else:
            for element_name in setting_names:
                if element_name not in pyorbit_dict.keys():
                    bad_names.append(element_name)
                elif not pyorbit_dict[element_name].is_optic():
                    bad_names.append(element_name)
                else:
                    good_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model or are not optics: {", ".join(bad_names)}.')

        for element_name in good_names:
            return_dict[element_name] = pyorbit_dict[element_name].get_parameter_dict()

        return return_dict

    def get_measurements(self, measurement_names: list[str] = None) -> Dict[str, Dict[str, Any]]:
        """Returns a parameter dictionary for the measurement elements in the model.

        Parameters
        ----------
        measurement_names : list[string], optional
            List of the names of the measurement elements whose parameter dictionaries you want. If nothing is provided,
            the dictionary includes all measurement elements in the model.

        Returns
        ----------
        out : dictionary
            A dictionary of element names as keys connected to that element's parameter dictionary.
        """

        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        bad_names = []
        good_names = []

        if measurement_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                if not element_ref.is_optic():
                    good_names.append(element_name)
        else:
            for element_name in measurement_names:
                if element_name not in pyorbit_dict.keys():
                    bad_names.append(element_name)
                elif pyorbit_dict[element_name].is_optic():
                    bad_names.append(element_name)
                else:
                    good_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model or are optics: {", ".join(bad_names)}.')

        for element_name in good_names:
            return_dict[element_name] = pyorbit_dict[element_name].get_parameter_dict()

        return return_dict

    def track(self):
        """Tracks the bunch through the lattice. Tracks from the most upstream change to the end."""

        if not self.bunch_flag:
            print('Create initial bunch in order to start tracking.')

        elif not self.current_changes:
            # print("No changes to track through.")
            pass

        else:
            track_start_time = time.time()

            # I wanted to freeze the lattice to make sure no modifications could be made to it while it is tracking.
            # Still trying to figure out the best way to do so.
            # frozen_lattice = copy.deepcopy(self.accLattice)
            frozen_lattice = self.accLattice
            frozen_changes = self.current_changes
            tracked_bunch = Bunch()

            # Determine the furthest upstream node where an optic has been changed.
            upstream_index = float('inf')
            upstream_name = None
            rf_flag = False
            for element_name in frozen_changes:
                location_node = self.pyorbit_dictionary[element_name].get_tracking_node()
                ind_check = frozen_lattice.getNodeIndex(location_node)
                if location_node.isRFGap():
                    rf_flag = True
                if ind_check < upstream_index:
                    upstream_index = ind_check
                    upstream_name = element_name

            # Use the bunch in the dictionary associated with the node that tracking with start with.
            if upstream_name in self.bunch_dict:
                self.bunch_dict[upstream_name].copyBunchTo(tracked_bunch)
                if self.debug:
                    print("Tracking bunch from " + upstream_name + "...")
            else:
                # If no bunch is found for that node, track from the beginning.
                upstream_index = -1
                self.bunch_dict['initial_bunch'].copyBunchTo(tracked_bunch)
                if self.debug:
                    print("Tracking bunch from start...")

            # Track bunch
            frozen_lattice.trackBunch(tracked_bunch, paramsDict=self.model_params, index_start=upstream_index)
            track_time_taken = time.time() - track_start_time
            if self.debug:
                print(f"Bunch tracked. Tracking time was {round(track_time_taken, 3)} seconds")

            # Clear the set of changes
            self.current_changes = set()

    def force_track(self):
        """Tracks the bunch through the lattice. Tracks from the beginning to the end."""

        if not self.bunch_flag:
            print('Create initial bunch in order to start tracking.')

        else:
            track_start_time = time.time()

            # I wanted to freeze the lattice to make sure no modifications could be made to it while it is tracking.
            # Still trying to figure out the best way to do so.
            # frozen_lattice = copy.deepcopy(self.accLattice)
            frozen_lattice = self.accLattice
            tracked_bunch = Bunch()

            # Track from beginning
            self.bunch_dict['initial_bunch'].copyBunchTo(tracked_bunch)
            if self.debug:
                print("Tracking bunch from start...")

            # Track bunch
            frozen_lattice.trackBunch(tracked_bunch, paramsDict=self.model_params)
            track_time_taken = time.time() - track_start_time
            if self.debug:
                print(f"Bunch tracked. Tracking time was {round(track_time_taken, 3)} seconds")

            # Clear the set of changes
            self.current_changes = set()

    def update_optics(self, changed_optics: Dict[str, Dict[str, Any]]) -> None:
        """Updates the optics in the lattice.

        Parameters
        ----------
        changed_optics : dictionary
            Dictionary using the element names as keys. Each key is connected to a parameter dictionary containing the
            new parameter values.
        """

        pyorbit_dict = self.pyorbit_dictionary
        for element_name, param_dict in changed_optics.items():
            if element_name not in pyorbit_dict.keys():
                print(f'PyORBIT element "{element_name}" not found.')
            elif pyorbit_dict[element_name].is_optic():
                element_ref = pyorbit_dict[element_name]
                for param, new_value in param_dict.items():
                    if param not in element_ref.get_parameter_dict():
                        print(f'Parameter key "{param}" not found in PyORBIT element "{element_name}".')
                    else:
                        current_value = element_ref.get_parameter(param)
                        # Resolution at which point the parameter will be changed.
                        if abs(new_value - current_value) > 1e-12:
                            element_ref.set_parameter(param, new_value)
                            self.current_changes.add(element_name)
                            if self.debug:
                                print(f'Value of "{param}" in "{element_name}" changed from {current_value} to '
                                      f'{new_value}.')

    def reset_optics(self) -> None:
        """Returns optics to their original values when the model was initiated."""

        self.update_optics(self.initial_optics)

    def save_optics(self, filename: Path = None) -> None:
        """Saves the optics as a dictionary in a json file.

        Parameters
        ----------
        filename : Path, optional
            Location and name for the optics file. If none is provided, the file saved using the time stamp.
        """

        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"optics_{timestamp}.json")
        saved_optics = self.get_settings()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)

    def load_optics(self, filename: Path) -> None:
        """Load an optics and update the lattice.

        Parameters
        ----------
        filename : Path
            Location and name for the optics file. The file needs to be a json file containing a dictionary.
        """

        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)

    def save_diagnostics(self, filename: Path = None) -> None:
        """Save the measurements dictionary to a json file.

        Parameters
        ----------
        filename : Path
            Location and name for the measurements file. If none is provided, the file saved using the time stamp.
        """

        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        saved_diagnostics = self.get_measurements()
        with open(filename, "w") as json_file:
            json.dump(saved_diagnostics, json_file, indent=4)
