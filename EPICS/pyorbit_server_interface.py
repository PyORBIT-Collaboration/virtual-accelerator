from datetime import datetime
from typing import Optional, Union, List, Dict
from pathlib import Path
import json

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.core.bunch import Bunch

from interface_lib import PyorbitNode, PyorbitChild, PyorbitCavity
from server_child_nodes import BPMclass, WSclass, BunchCopyClass


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


class OrbitModel(Model):
    def __init__(self, input_lattice: LinacAccLattice, input_bunch: Bunch = None, ignored_nodes=None):
        super().__init__()

        self.accLattice = input_lattice
        if ignored_nodes is None:
            ignored_nodes = set()
        ignored_nodes |= {'baserfgap', 'drift', 'tilt', 'fringe', 'markerLinacNode', 'baseLinacNode'}
        unique_elements = set()

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.
        element_ref_hint = Union[PyorbitNode, PyorbitCavity, PyorbitChild]
        element_dict_hint = Dict[str, element_ref_hint]
        element_dict: element_dict_hint = {}

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

        list_of_cavities = self.accLattice.getRF_Cavities()
        for cavity in list_of_cavities:
            element_name = cavity.getName()
            unique_elements.add(element_name)
            element_dict[element_name] = PyorbitCavity(cavity)

        self.pyorbit_dictionary = element_dict

        # set up dictionary of bunches
        self.bunch_dict = {'initial_bunch': Bunch()}
        for element_name, element_ref in self.pyorbit_dictionary.items():
            location_node = element_ref.get_tracking_node()
            if element_name not in self.bunch_dict:
                self.bunch_dict[element_name] = Bunch()
                location_node.addChildNode(BunchCopyClass(element_name, self.bunch_dict), location_node.ENTRANCE)

        if input_bunch is not None:
            self.set_initial_bunch(input_bunch)

        # Set up variable to track where the most upstream change is located.
        self.current_changes = set()
        # store initial settings
        self.initial_optics = self.get_settings()

    def set_initial_bunch(self, initial_bunch: Bunch):
        initial_bunch.getSyncParticle().time(0.0)
        initial_bunch.copyBunchTo(self.bunch_dict['initial_bunch'])

        self.accLattice.trackDesignBunch(initial_bunch)
        self.accLattice.trackBunch(initial_bunch)
        self.current_changes = set()

    def get_element_list(self) -> list[str]:
        key_list = []
        for element_key in self.pyorbit_dictionary.keys():
            key_list.append(element_key)
        return key_list

    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None) -> dict[str, dict[str, ]]:
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

    def track(self, number_of_particles=1000):
        if self.bunch_dict['initial_bunch'].getSizeGlobal() == 0:
            print('Create initial bunch in order to start tracking.')

        elif not self.current_changes:
            # print("No changes to track through.")
            pass

        else:
            # freeze optics (clone)
            # frozen_lattice = copy.deepcopy(self.accLattice)
            frozen_lattice = self.accLattice
            frozen_changes = self.current_changes
            tracked_bunch = Bunch()

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

            # setup initial bunch
            if upstream_name in self.bunch_dict:
                self.bunch_dict[upstream_name].copyBunchTo(tracked_bunch)
                print("Tracking bunch from " + upstream_name + "...")
            else:
                upstream_index = -1
                self.bunch_dict['initial_bunch'].copyBunchTo(tracked_bunch)
                print("Tracking bunch from start...")

            for n in range(tracked_bunch.getSizeGlobal()):
                if n + 1 > number_of_particles:
                    tracked_bunch.deleteParticleFast(n)
            tracked_bunch.compress()

            # if rf_flag:
            #    tracked_bunch.getSyncParticle().time(0.0)
            #    frozen_lattice.trackDesignBunch(tracked_bunch, index_start=upstream_index)
            frozen_lattice.trackBunch(tracked_bunch, index_start=upstream_index)
            print("Bunch tracked")

            self.current_changes = set()

    def update_optics(self, changed_optics: dict[str, dict[str,]]) -> None:
        # update optics
        # Keep track of changed elements
        # do not track here yet
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
                        if abs(new_value - current_value) > 1e-12:
                            element_ref.set_parameter(param, new_value)
                            self.current_changes.add(element_name)
                            print(
                                f'Value of "{param}" in "{element_name}" changed from {current_value} to {new_value}.')

    def reset_optics(self) -> None:
        self.update_optics(self.initial_optics)

    def save_optics(self, filename: Path = None) -> None:
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"optics_{timestamp}.json")
        saved_optics = self.get_settings()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)

    def load_optics(self, filename: Path) -> None:
        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)

    def save_diagnostics(self, filename: Path = None) -> None:
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        saved_diagnostics = self.get_measurements()
        with open(filename, "w") as json_file:
            json.dump(saved_diagnostics, json_file, indent=4)


class BrandonModel(Model):
    def __init__(self):
        super().__init__()
