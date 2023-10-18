import sys
from datetime import datetime
from typing import Optional, Union, List
from pathlib import Path

import json

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory
from orbit.core.bunch import Bunch

from bpm_child_node import BPMclass

from interface_lib import nodeDict, PVDict


class OrbitModel:
    def __init__(self, lattice_file: Path, subsections_list: List[str] = None, pv_file: Path = None):
        # read lattice
        if subsections_list is None or len(subsections_list) == 0:
            subsections_list = ["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4",
                                "SCLMed", "SCLHigh", "HEBT1", "HEBT2"]
        sns_linac_factory = SNS_LinacLatticeFactory()
        sns_linac_factory.setMaxDriftLength(0.01)
        xml_file_name = lattice_file
        self.accLattice = sns_linac_factory.getLinacAccLattice(subsections_list, xml_file_name)
        self.pv_dict = PVDict(self.accLattice)

        cav_nodes = self.accLattice.getRF_Cavities()
        blanked_key = 'blanked'
        for node in cav_nodes:
            node.addParam(blanked_key, False)

        list_of_nodes = self.accLattice.getNodes()
        for node in list_of_nodes:
            node_type = node.getType()
            # Set up BPMs to actually do something and attach their PVs
            if node_type == 'markerLinacNode':
                node_name = node.getName()
                if 'BPM' in node_name:
                    node.addChildNode(BPMclass(node_name), node.ENTRANCE)

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.
        self.node_dict = nodeDict(self.accLattice, ignored_nodes={'drift', 'tilt', 'fringe', 'markerLinacNode'})
        self.pv_dict = PVDict(self.node_dict)

        # setup initial bunch
        self.bunch_in = Bunch()
        bunch_file = "../SCL_Wizard/SCL_in.dat"
        self.bunch_in.readBunch(bunch_file)
        self.bunch_in.getSyncParticle().time(0.0)
        init_tracked_bunch = Bunch()
        self.bunch_in.copyBunchTo(init_tracked_bunch)
        for n in range(init_tracked_bunch.getSizeGlobal()):
            if n + 1 > 1000:
                init_tracked_bunch.deleteParticleFast(n)
        init_tracked_bunch.compress()

        # set up dictionary of bunches and the childnode to populate it
        self.bunch_dict = {'initial_bunch': Bunch()}
        self.bunch_in.copyBunchTo(self.bunch_dict['initial_bunch'])

        class BunchCopy:
            def trackActions(actionsContainer, paramsDict):
                bunch = paramsDict["bunch"]
                part_num = bunch.getSizeGlobal()
                if part_num > 0:
                    node = paramsDict["parentNode"]
                    if node.getType() == "baserfgap":
                        node_name = node.getRF_Cavity().getName()
                        bunch.copyBunchTo(self.bunch_dict[node_name])
                        # self.bunch_dict[node_name].getSyncParticle().time(0.0)
                    else:
                        node_name = node.getName()
                        bunch.copyBunchTo(self.bunch_dict[node_name])
                        # self.bunch_dict[node_name].getSyncParticle().time(0.0)

        for node in self.accLattice.getNodes():
            node_type = node.getType()
            if "drift" not in node_type and "marker" not in node_type:
                if node_type == "baserfgap":
                    rf_node = node.getRF_Cavity()
                    node_name = rf_node.getName()
                    if node_name not in self.bunch_dict:
                        self.bunch_dict[node_name] = Bunch()
                        rf_entrance_node = rf_node.getRF_GapNodes()[0]
                        rf_entrance_node.addChildNode(BunchCopy, rf_entrance_node.ENTRANCE)
                else:
                    node_name = node.getName()
                    self.bunch_dict[node_name] = Bunch()
                    node.addChildNode(BunchCopy, node.ENTRANCE)

        # run design particle
        self.accLattice.trackDesignBunch(init_tracked_bunch)
        self.accLattice.trackBunch(init_tracked_bunch)
        self.upstream_change = None

        # store initial settings
        self.initial_settings = {}
        for pv_name, pv_ref in self.pv_dict.get_pvref_dict().items():
            if any('setting' for pv_type in pv_ref.get_types()):
                self.initial_settings[pv_name] = pv_ref.get_value()

    def add_pv(self, pv_name: str, pv_types: list[str], pyorbit_name: str, param_key: str) -> None:
        self.pv_dict.add_pv(pv_name, pv_types, pyorbit_name, param_key)

    def order_pvs(self):
        self.pv_dict.order_pvs()

    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None) -> dict[str, ]:
        return_dict = {}
        if setting_names is None:
            for pv_name, pv_ref in self.pv_dict.get_pvref_dict().items():
                if pv_ref.get_type() == "setting":
                    return_dict[pv_name] = pv_ref.get_value()
        elif isinstance(setting_names, list):
            for pv_name in setting_names:
                return_dict[pv_name] = self.pv_dict.get_pv(pv_name)
        elif isinstance(setting_names, str):
            return_dict[setting_names] = self.pv_dict.get_pv(setting_names)
        return return_dict

    def get_measurements(self, measurement_names: Optional[Union[str, List[str]]] = None) -> dict[str, ]:
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        return_dict = {}
        if measurement_names is None:
            for pv_name, pv_ref in self.pv_dict.get_pvref_dict().items():
                if pv_ref.get_type() == "diagnostics" or "physics":
                    return_dict[pv_name] = pv_ref.get_value()
        elif isinstance(measurement_names, list):
            for pv_name in measurement_names:
                return_dict[pv_name] = self.pv_dict.get_pv(pv_name)
        elif isinstance(measurement_names, str):
            return_dict[measurement_names] = self.pv_dict.get_pv(measurement_names)
        return return_dict

    def track(self, number_of_particles=1000) -> dict[str, float]:
        if self.upstream_change is not None:
            # freeze optics (clone)
            start_node_name = self.pv_dict.get_node_name(self.upstream_change)
            start_ind = self.node_dict.get_node_index(start_node_name)
            start_bunch_name = self.node_dict.get_location_node_name(start_node_name)
            frozen_lattice = self.accLattice
            bunch_dict = self.bunch_dict

            # setup initial bunch
            tracked_bunch = Bunch()
            if start_bunch_name in bunch_dict:
                self.bunch_dict[start_bunch_name].copyBunchTo(tracked_bunch)
                for n in range(tracked_bunch.getSizeGlobal()):
                    if n + 1 > number_of_particles:
                        tracked_bunch.deleteParticleFast(n)
            else:
                self.bunch_dict['initial_bunch'].copyBunchTo(tracked_bunch)
                for n in range(tracked_bunch.getSizeGlobal()):
                    if n + 1 > number_of_particles:
                        tracked_bunch.deleteParticleFast(n)
            tracked_bunch.compress()

            # and track new setup
            # frozen_lattice.trackDesignBunch(tracked_bunch, index_start=start_ind)
            frozen_lattice.trackBunch(tracked_bunch, index_start=start_ind)
            self.upstream_change = None

        else:
            print("No changes to track through.")
            # if nothing changed do not track

    def update_optics(self, changed_optics: dict[str,]) -> None:
        # update optics
        # figure out the most upstream element that changed
        # do not track here yet
        if self.upstream_change is None:
            upstream_check = float('inf')
        else:
            upstream_node = self.pv_dict.get_node_name(self.upstream_change)
            upstream_check = self.node_dict.get_node_index(upstream_node)
        temp_upstream_check = upstream_check
        upstream_name = None
        change_flag = False
        pv_dict = self.pv_dict
        node_dict = self.node_dict
        for pv_name, new_value in changed_optics.items():
            pv_type = pv_dict.get_pv_type(pv_name)
            current_value = pv_dict.get_pv(pv_name)
            if pv_type == "setting" and new_value != current_value:
                pv_dict.set_pv(pv_name, new_value)
                change_flag = True
                node_name = pv_dict.get_node_name(pv_name)
                pv_index = node_dict.get_node_index(node_name)
                if pv_index < temp_upstream_check:
                    temp_upstream_check = pv_index
                    upstream_name = pv_name
                print(f'New value of {pv_name} is {new_value}')
        if change_flag is True and 0 < temp_upstream_check < upstream_check:
            self.upstream_change = upstream_name

    def reset_optics(self) -> None:
        self.update_optics(self.initial_settings)

    def save_optics(self, filename: Path = None) -> None:
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"optics_{timestamp}.json")
        saved_optics = {}
        for pv_name, pv_ref in self.pv_dict.get_pvref_dict().items():
            if pv_ref.get_type() == "setting":
                saved_optics[pv_name] = pv_ref.get_value()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)

    def load_optics(self, filename: Path) -> None:
        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)

    def save_pvs(self, filename: Path = None) -> None:
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        saved_optics = {}
        for pv_name, pv_ref in self.pv_dict.get_pvref_dict().items():
            saved_optics[pv_name] = pv_ref.get_value()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)


class BrandonModel(OrbitModel):
    pass
