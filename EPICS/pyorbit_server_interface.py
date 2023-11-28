from datetime import datetime
from typing import Optional, Union, List
from pathlib import Path
import json

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.core.bunch import Bunch

from interface_lib import PyorbitLibrary
from server_child_nodes import BPMclass, WSclass, BunchCopyClass


class OrbitModel:
    def __init__(self, input_lattice: LinacAccLattice, input_bunch: Bunch = None):
        self.accLattice = input_lattice

        list_of_nodes = self.accLattice.getNodes()
        for node in list_of_nodes:
            node_type = node.getType()
            # Set up BPMs to actually do something and attach their PVs
            if node_type == 'markerLinacNode':
                node_name = node.getName()
                if 'BPM' in node_name:
                    node.addChildNode(BPMclass(node_name), node.ENTRANCE)
                if 'WS' in node_name:
                    node.addChildNode(WSclass(node_name), node.ENTRANCE)

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.
        self.pyorbit_dict = PyorbitLibrary(self.accLattice)

        # set up dictionary of bunches
        self.bunch_dict = {'initial_bunch': Bunch()}
        for element_name, element_ref in self.pyorbit_dict.get_element_dictionary().items():
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

    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None) -> dict[str, dict[str,]]:
        pyorbit_dict = self.pyorbit_dict
        return_dict = {}
        if setting_names is None:
            for element_name, element_ref in pyorbit_dict.get_element_dictionary().items():
                if element_ref.is_optic():
                    return_dict[element_name] = element_ref.get_parameter_dict()

        elif isinstance(setting_names, list):
            bad_names = []
            for element_name in setting_names:
                if element_name in pyorbit_dict.get_element_names():
                    return_dict[element_name] = pyorbit_dict.get_element_parameters(element_name)
                else:
                    bad_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model: {", ".join(bad_names)}.')

        elif isinstance(setting_names, str):
            if setting_names in pyorbit_dict.get_element_names():
                return_dict[setting_names] = pyorbit_dict.get_element_parameters(setting_names)
            else:
                print(f'The element "{setting_names}" is not in the model.')
        return return_dict

    def get_measurements(self, measurement_names: Optional[Union[str, List[str]]] = None) -> dict[str, dict[str,]]:
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        pyorbit_dict = self.pyorbit_dict
        return_dict = {}
        if measurement_names is None:
            for element_name, element_ref in pyorbit_dict.get_element_dictionary().items():
                if not element_ref.is_optic():
                    return_dict[element_name] = element_ref.get_parameter_dict()

        elif isinstance(measurement_names, list):
            bad_names = []
            for element_name in measurement_names:
                if element_name in pyorbit_dict.get_element_names():
                    return_dict[element_name] = pyorbit_dict.get_element_parameters(element_name)
                else:
                    bad_names.append(element_name)
            if bad_names:
                print(f'These elements are not in the model: {", ".join(bad_names)}.')

        elif isinstance(measurement_names, str):
            if measurement_names in pyorbit_dict.get_element_names():
                return_dict[measurement_names] = pyorbit_dict.get_element_parameters(measurement_names)
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
                ind_check = self.pyorbit_dict.get_element_index(element_name)
                if self.pyorbit_dict.get_location_node(element_name).isRFGap():
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
        pyorbit_dict = self.pyorbit_dict
        for element_name, param_dict in changed_optics.items():
            if element_name not in pyorbit_dict.get_element_names():
                print(f'PyORBIT element "{element_name}" not found.')
            elif pyorbit_dict.get_element_reference(element_name).is_optic():
                element_ref = pyorbit_dict.get_element_reference(element_name)
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


class BrandonModel(OrbitModel):
    pass
