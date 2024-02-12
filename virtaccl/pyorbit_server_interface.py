from datetime import datetime
from typing import Optional, Union, List, Dict
from pathlib import Path
import json

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.core.bunch import Bunch

from .interface_lib import PyorbitNode, PyorbitChild, PyorbitCavity
from .server_child_nodes import BPMclass, WSclass, BunchCopyClass, RF_Gap_Aperture


class Model:
    def __init__(self):
        pass

    def get_measurements(self) -> dict[str, dict[str,]]:
        # Output values from the model. This needs to return a dictionary with the model name of the element as a key
        # to a dictionary of the element's parameters.
        return {}

    def track(self) -> None:
        # update values within your model
        pass

    def update_optics(self, changed_optics: dict[str, dict[str,]]) -> None:
        # Take external values and update the model. Needs an input of a dictionary with the model name of the element
        # as a key to a dictionary of the element's parameters with their new values.
        pass


# This is a model using PyORBIT. It requires a LinacAccLattice as input. The input bunch can also be defined here.
class OrbitModel(Model):
    # This creates a hint for the element dictionary for easier development.
    element_ref_hint = Union[PyorbitNode, PyorbitCavity, PyorbitChild]
    element_dict_hint = Dict[str, element_ref_hint]

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
        element_dict: OrbitModel.element_dict_hint = {}

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
            gap_ent = cavity.getRF_GapNodes()[0]
            beta_min, beta_max = gap_ent.getBetaMinMax()
            gap_ent.addChildNode(RF_Gap_Aperture('long_apt', beta_min, beta_max), gap_ent.ENTRANCE)

        self.pyorbit_dictionary = element_dict

        # Sets up a dictionary of bunches at each optics element. This dictionary is referenced whenever an optic
        # changes so that the bunch can be retracked from that optic instead of the beginning. It also attaches to each
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

    # Designate an input bunch for the lattice. This bunch is then tracked through the lattice.
    def set_initial_bunch(self, initial_bunch: Bunch, beam_current: float = 40e-3):
        initial_bunch.getSyncParticle().time(0.0)
        initial_bunch.copyBunchTo(self.bunch_dict['initial_bunch'])
        self.set_beam_current(beam_current)
        self.model_params['initial_particle_number'] = initial_bunch.getSizeGlobal()
        self.bunch_flag = True

        self.accLattice.trackDesignBunch(initial_bunch)
        self.force_track()

    # Set the beam current for the initial bunch.
    def set_beam_current(self, beam_current: float):
        self.model_params['beam_current'] = beam_current

    # Returns a list of all element keys currently maintained in the model.
    def get_element_list(self) -> list[str]:
        key_list = []
        for element_key in self.pyorbit_dictionary.keys():
            key_list.append(element_key)
        return key_list

    # Returns the element dictionary
    def get_element_dictionary(self) -> element_dict_hint:
        return self.pyorbit_dictionary

    # Returns a dictionary all the current setting parameters in a dictionary of elements. The number of elements
    # depends on the input provided. If nothing, the returned dictionary includes all current optics within the model.
    # If a list of element names, the returned dictionary only includes those elements. And if just an element name, the
    # dictionary only includes that element.
    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None) -> dict[str, dict[str,]]:
        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        if setting_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                if element_ref.is_optic():
                    return_dict[element_name] = element_ref.get_parameter_dict()

        elif isinstance(setting_names, list):
            bad_names = []
            for element_name in setting_names:
                if element_name in pyorbit_dict.keys():
                    return_dict[element_name] = pyorbit_dict[element_name].get_parameter_dict()
                else:
                    bad_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model: {", ".join(bad_names)}.')

        elif isinstance(setting_names, str):
            if setting_names in pyorbit_dict.keys():
                return_dict[setting_names] = pyorbit_dict[setting_names].get_parameter_dict()
            else:
                print(f'The element "{setting_names}" is not in the model.')
        return return_dict

    # Returns a dictionary all the current measurement readings in a dictionary of elements. The number of elements
    # depends on the input provided. If nothing, the returned dictionary includes all current measurement devices within
    # the model. If a list of element names, the returned dictionary only includes those elements. And if just an
    # element name, the dictionary only includes that element.
    def get_measurements(self, measurement_names: Optional[Union[str, List[str]]] = None) -> dict[str, dict[str,]]:
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        pyorbit_dict = self.pyorbit_dictionary
        return_dict = {}
        if measurement_names is None:
            for element_name, element_ref in pyorbit_dict.items():
                if not element_ref.is_optic():
                    return_dict[element_name] = element_ref.get_parameter_dict()

        elif isinstance(measurement_names, list):
            bad_names = []
            for element_name in measurement_names:
                if element_name in pyorbit_dict.keys():
                    return_dict[element_name] = pyorbit_dict[element_name].get_parameter_dict()
                else:
                    bad_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model: {", ".join(bad_names)}.')

        elif isinstance(measurement_names, str):
            if measurement_names in pyorbit_dict.keys():
                return_dict[measurement_names] = pyorbit_dict[measurement_names].get_parameter_dict()
            else:
                print(f'The element "{measurement_names}" is not in the model.')
        return return_dict

    # Tracks the bunch through the lattice. If no changes were made since the last track, then nothing happens. If a
    # change has occurred since the last track, then tracking begins from that element.
    def track(self):
        if not self.bunch_flag:
            print('Create initial bunch in order to start tracking.')

        elif not self.current_changes:
            # print("No changes to track through.")
            pass

        else:
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
            if self.debug:
                print("Bunch tracked")

            # Clear the set of changes
            self.current_changes = set()

    # Tracks the bunch through the lattice. Always tracks from the beginning, even if no optics have been changed.
    def force_track(self):
        if not self.bunch_flag:
            print('Create initial bunch in order to start tracking.')

        else:
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
            frozen_lattice.trackBunch(tracked_bunch, paramsDict=self.model_params, )
            if self.debug:
                print("Bunch tracked")

            # Clear the set of changes
            self.current_changes = set()

    # Change optics setting. This only changes the parameters of the optics and does not retrack the bunch. For an
    # input, it needs a dictionary with a key for the name of each changed element linked to a dictionary of it's
    # changed PyORBIT parameter's keys linked to each parameter's new value.
    def update_optics(self, changed_optics: dict[str, dict[str,]]) -> None:
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

    # Returns optics to their original values when the model was initiated.
    def reset_optics(self) -> None:
        self.update_optics(self.initial_optics)

    # Saves the current optics as dictionary in a json file. The time stamp is used as the default name if none is
    # given. The dictionary is the same dictionary that get_settings outputs above.
    def save_optics(self, filename: Path = None) -> None:
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"optics_{timestamp}.json")
        saved_optics = self.get_settings()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)

    # Takes optics in a json file and updates the lattice parameters with them. The dictionary in the file needs to be
    # the same format as update_optics requires.
    def load_optics(self, filename: Path) -> None:
        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)

    # Saves the current diagnostic readings as a json file. The format is the same as the output from get_measurements.
    def save_diagnostics(self, filename: Path = None) -> None:
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        saved_diagnostics = self.get_measurements()
        with open(filename, "w") as json_file:
            json.dump(saved_diagnostics, json_file, indent=4)
