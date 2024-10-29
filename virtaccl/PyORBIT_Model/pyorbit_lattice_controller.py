import time
from datetime import datetime
from typing import Union, List, Dict, Any
from pathlib import Path
import json

from orbit.py_linac.lattice import BaseLinacNode
from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.core.bunch import Bunch
from orbit.space_charge.sc3d import setUniformEllipsesSCAccNodes
from orbit.core.spacecharge import SpaceChargeCalcUnifEllipse

from .pyorbit_element_controllers import PyorbitNode, PyorbitChild, PyorbitCavity
from .pyorbit_child_nodes import BunchCopyClass

from virtaccl.model import Model


class OrbitModel(Model):
    """
    This is a controller that automates using the PyORBIT model for the virtual accelerator. If a PyORBIT lattice is
    given, that lattice is initialized as part of the model's initialization.

        Parameters
        ----------
        input_lattice : LinacAccLattice, optional
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

    def __init__(self, input_lattice: LinacAccLattice = None, input_bunch: Bunch = None, debug: bool = False,
                 save_bunch: str = None):
        super().__init__()
        self.debug = debug
        self.save_bunch = save_bunch

        # Flags to keep track of lattice and bunch initialization.
        self.lattice_flag = False
        self.bunch_flag = False

        # A dictionary used in tracking to keep track of parameters useful to the model.
        self.model_params = {}

        # Set up variable to track where the most upstream change is located.
        self.current_changes = set()
        # Store initial settings
        self.initial_optics = {}

        # Keys to designate different PyORBIT node types.
        quad_key = 'linacQuad'
        correctorH_key = 'dch'
        correctorV_key = 'dcv'
        bend_key = 'bend linac'
        self.cavity_key = 'RF_Cavity'
        self.marker_key = 'markerLinacNode'

        # PyORBIT keys for parameters we want to pass to the virtual accelerator.
        quad_params = ['dB/dr']
        corrector_params = ['B']
        bend_params = []
        cavity_params = ['phase', 'amp']
        marker_params = []

        # Dictionary to keep the above parameters with their designated classes.
        self.param_ref_dict = {quad_key: quad_params,
                               self.cavity_key: cavity_params,
                               correctorH_key: corrector_params,
                               correctorV_key: corrector_params,
                               bend_key: bend_params,
                               self.marker_key: marker_params}

        # Set of PyORBIT node types the model will keep track of.
        self.modeled_elements = {self.cavity_key, quad_key, correctorH_key, correctorV_key, bend_key}

        # Classes that can change the beam.
        self.optic_classes = {self.cavity_key, quad_key, correctorH_key, correctorV_key, bend_key}

        # Classes that measure the beam.
        self.diagnostic_classes = set()

        # Setup for when a lattice is initialized.
        self.accLattice = None
        self.accLattice: LinacAccLattice
        # Dictionary containing all elements the model is maintaining.
        self.pyorbit_dictionary: OrbitModel._element_dict_hint = {}
        # Dictionary of bunches that allow for tracking starting at changed optics.
        self.bunch_dict = {'initial_bunch': Bunch()}

        if input_lattice is not None:
            self.initialize_lattice(input_lattice)

        if input_bunch is not None:
            self.set_initial_bunch(input_bunch)

    def initialize_lattice(self, input_lattice: LinacAccLattice):
        """
        Designate the lattice used by the model. All nodes specified node types are registered with the model. If an
        initial bunch has already been designated, the bunch is then tracked. If a previous lattice was

            Parameters
            ----------
            input_lattice : LinacAccLattice
                PyORBIT linac lattice the model uses for tracking.
        """

        self.accLattice = input_lattice
        # Here we find the node types in PyORBIT we need to worry about and start a set to make sure each element we do
        # care about has a unique name.
        included_nodes = self.modeled_elements
        unique_elements = set()

        # Set up a dictionary to reference different objects within the lattice by their name. Not all elements are
        # readily available in LinacAccLattice, so this lets us easily reference them.
        element_dict = {}

        # This function is for digging into child nodes in PyORBIT to find nodes we need to reference. This is mainly
        # for correctors and some BPMs. If a BPM or wire scanner markerLinacNode is found, the appropriate child node is
        # attached. Waring: This uses recursion to also look at child nodes of child nodes.
        def add_child_nodes(ancestor_node, children_nodes, element_dictionary):
            for child in children_nodes:
                child_type = child.getType()
                if child_type in included_nodes:
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
            if node_type in included_nodes:
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
            element_dict[element_name] = PyorbitCavity(cavity, self.cavity_key)

        self.pyorbit_dictionary = element_dict

        # Sets up a dictionary of bunches at each optics element. This dictionary is referenced whenever an optic
        # changes so that the bunch can be re-tracked from that optic instead of the beginning. It also attaches to each
        # optic the BunchCopyClass as a child node which saves the bunch within the dictionary.
        for element_name, element_ref in self.pyorbit_dictionary.items():
            if element_name not in self.bunch_dict and element_ref.get_type() in self.optic_classes:
                location_node = element_ref.get_tracking_node()
                self.bunch_dict[element_name] = Bunch()
                location_node.addChildNode(BunchCopyClass(element_name + ':copyBunch', element_name, self.bunch_dict),
                                           location_node.ENTRANCE)

        # Set up variable to track where the most upstream change is located.
        self.current_changes.clear()
        # Store initial settings
        self.initial_optics = self.get_settings()
        self.lattice_flag = True

        if self.bunch_flag:
            self.accLattice.trackDesignBunch(self.bunch_dict['initial_bunch'])
            self.force_track()

    def add_space_charge_nodes(self, minimum_sc_length: float = 0.01):
        """Add space charge nodes to an initialized lattice. The nodes are the Uniform Ellipses SC accelerator nodes.

        Parameters
        ----------
        minimum_sc_length : float
            Minimum length in meters for distance between space charge nodes. The default 0.01 meters.
        """

        if self.lattice_flag:
            nEllipses = 1
            calcUnifEllips = SpaceChargeCalcUnifEllipse(nEllipses)
            setUniformEllipsesSCAccNodes(self.accLattice, minimum_sc_length, calcUnifEllips)
        else:
            print('Error: Initialize a lattice in order to add space charge nodes.')

        if self.bunch_flag:
            self.accLattice.trackDesignBunch(self.bunch_dict['initial_bunch'])
            self.force_track()

    def set_initial_bunch(self, initial_bunch: Bunch, beam_current: float = 40e-3):
        """Designate an input PyORBIT bunch for the lattice. If a lattice has already been initialized, this bunch is
        then tracked through the lattice from the beginning.

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

        if self.lattice_flag:
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

    def get_element_controller(self, element_name: str) -> _element_ref_hint:
        """Returns the controller for the given PyORBIT model.

        Results
        ----------
        out : PyorbitElement
            The controller for the named PyORBIT element.
        """

        return self.pyorbit_dictionary[element_name]

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
            element_type = pyorbit_dict[element_name].get_type()
            model_keys = self.param_ref_dict[element_type]
            pyorbit_params = pyorbit_dict[element_name].get_parameter_dict()
            element_dict = {key: pyorbit_params[key] for key in model_keys}
            return element_dict

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
            element_dict = self.get_element_parameters(element_name)
            return_dict[element_name] = element_dict
        return return_dict

    def add_child_node(self, parent_name: str, child_node: BaseLinacNode):
        """Adds a child node to a node in the lattice and a reference in the element dictionary. If the name of the
        child is taken by another node that is not a marker, the child will not be added.

        Parameters
        ----------
        parent_name: basestring
            Name of the parent node that the child will be attached to. Can be the name of a child node itself.
        child_node: PyORBIT class
            Instance of a class that will become the child. Needs to contain a "trackActions" function that defines how
            the bunch is tracked through the child and a "getName" function that returns a string of the node's name.
        """

        child_name = child_node.getName()
        if child_name in self.get_element_list():
            if self.get_element_controller(child_name).get_type() != self.marker_key:
                print(f'Warning: "{child_name}" has the same name as another element, which is not a marker node. '
                      f'{child_name} was not added to the model.')
                return

        parent = self.get_element_controller(parent_name)
        if isinstance(parent, PyorbitChild):
            ancestor = parent.get_ancestor_node()
        else:
            ancestor = parent.get_element()
        ancestor.addChildNode(child_node, ancestor.ENTRANCE)
        self.get_element_dictionary()[child_name] = PyorbitChild(child_node, ancestor)

        if child_node.getType() not in self.modeled_elements:
            print(f'Warning: The node type "{child_node.getType()}" is not in the current list of node types managed by'
                  f' the model. Define this node type for the model using the "define_custom_node" function.')

    def define_custom_node(self, node_type: str, parameter_list: List[str] = None,
                           optic: bool = False, diagnostic: bool = False):
        """Defines custom nodes for the model. This tells the model how to handle new nodes not built into PyORBIT.

        Parameters
        ----------
        node_type: basestring
            String identifying the new type of node. This needs to be unique to all node types. If it is already taken
            by either default PyORBIT nodes or another custom node, the new node type will NOT be added to the model.
        parameter_list: list[string], optional
            List of parameter keys in the node the model will reference. Include keys desired for the update_optics and
            get_measurements functions. The default is an empty list telling the model not to reference any parameters.
        optic: bool, optional
            Boolean designating if the new node type changes the tracking optics. The default is False.
        diagnostic: bool, optional
            Boolean designating if the new node type measures the beam. The default is False.
        """

        if node_type in self.modeled_elements:
            print(f'Error: Node type "{node_type}" is already in use. Node type cannot be added to the model.')
            return
        self.modeled_elements.add(node_type)
        if parameter_list is None:
            parameter_list = []
        self.param_ref_dict[node_type] = parameter_list

        if optic:
            self.optic_classes.add(node_type)
        if diagnostic:
            self.diagnostic_classes.add(node_type)

        if self.lattice_flag:
            print(f'Warning: Lattice already initialized. Reinitialize the lattice to make sure all current '
                  f'"{node_type}" nodes are registered with the model.')

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
                if element_ref.get_type() in self.optic_classes:
                    good_names.append(element_name)
        else:
            for element_name in setting_names:
                if element_name not in pyorbit_dict.keys():
                    bad_names.append(element_name)
                elif pyorbit_dict[element_name].get_type() not in self.optic_classes:
                    bad_names.append(element_name)
                else:
                    good_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model or are not optics: {", ".join(bad_names)}.')

        for element_name in good_names:
            element_dict = self.get_element_parameters(element_name)
            return_dict[element_name] = element_dict
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

        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        bad_names = []
        good_names = []

        if measurement_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                if element_ref.get_type() in self.diagnostic_classes:
                    good_names.append(element_name)
        else:
            for element_name in measurement_names:
                if element_name not in pyorbit_dict.keys():
                    bad_names.append(element_name)
                elif pyorbit_dict[element_name].get_type() not in self.diagnostic_classes:
                    bad_names.append(element_name)
                else:
                    good_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model or are not diagnostics: {", ".join(bad_names)}.')

        for element_name in good_names:
            element_dict = self.get_element_parameters(element_name)
            return_dict[element_name] = element_dict
        return return_dict

    def track(self) -> None:
        """Tracks the bunch through the lattice. Tracks from the most upstream change to the end."""

        if not self.lattice_flag:
            print('Error: Initialize a lattice in order to start tracking.')
        elif not self.bunch_flag:
            print('Error: Create an initial bunch in order to start tracking.')

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
            if 'initial_bunch' in frozen_changes:
                upstream_index = -1
                upstream_name = None

            else:
                upstream_index = float('inf')
                upstream_name = None
                for element_name in frozen_changes:
                    location_node = self.pyorbit_dictionary[element_name].get_tracking_node()
                    ind_check = frozen_lattice.getNodeIndex(location_node)
                    if ind_check < upstream_index:
                        upstream_index = ind_check
                        upstream_name = element_name

                if upstream_name not in self.bunch_dict:
                    upstream_index = -1
                    upstream_name = None

            if upstream_name is None:
                # If no bunch is found for that node, track from the beginning.
                self.bunch_dict['initial_bunch'].copyBunchTo(tracked_bunch)
                if self.debug:
                    print("Tracking bunch from start...")
            else:
                # Use the bunch in the dictionary associated with the node that tracking will start with.
                self.bunch_dict[upstream_name].copyBunchTo(tracked_bunch)
                if self.debug:
                    print("Tracking bunch from " + upstream_name + "...")

            # Track bunch
            frozen_lattice.trackBunch(tracked_bunch, paramsDict=self.model_params, index_start=upstream_index)
            track_time_taken = time.time() - track_start_time
            if self.debug:
                print(f"Bunch tracked. Tracking time was {round(track_time_taken, 3)} seconds")
            if self.save_bunch:
                tracked_bunch.dumpBunch(self.save_bunch)
                print(f'Final bunch saved as "{self.save_bunch}"')

            # Clear the set of changes
            self.current_changes = set()

    def force_track(self) -> None:
        """Tracks the bunch through the lattice. Tracks from the beginning to the end."""

        # Clear the set of changes to force tracking from the beginning of the lattice.
        self.current_changes.add('initial_bunch')
        self.track()

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
            elif pyorbit_dict[element_name].get_type() in self.optic_classes:
                element_ref = pyorbit_dict[element_name]
                element_type = pyorbit_dict[element_name].get_type()
                for param, new_value in param_dict.items():
                    if param not in self.param_ref_dict[element_type]:
                        print(f'Parameter key "{param}" not found in PyORBIT element "{element_name}".')
                    else:
                        current_value = element_ref.get_parameter(param)
                        if isinstance(new_value, str):
                            element_ref.set_parameter(param, new_value)
                        # Resolution at which point the parameter will be changed.
                        elif abs(new_value - current_value) > 1e-12:
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
