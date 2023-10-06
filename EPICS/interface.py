import math
import sys
from datetime import datetime
from typing import Optional, Union, List
from pathlib import Path
import json

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory
from orbit.core.bunch import Bunch

from bpm_child_node import BPMclass

from interface_pv_class import PV


class OrbitModel:
    def __init__(self, lattice_file: Path, subsections_list=None):
        # read lattice
        if subsections_list is None:
            subsections_list = []
        sns_linac_factory = SNS_LinacLatticeFactory()
        sns_linac_factory.setMaxDriftLength(0.01)
        xml_file_name = lattice_file
        if len(subsections_list) == 0:
            # subsections_list = ["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4", "SCLMed", "SCLHigh", "HEBT1", "HEBT2"]
            subsections_list = ["SCLMed", "SCLHigh"]
        self.accLattice = sns_linac_factory.getLinacAccLattice(subsections_list, xml_file_name)

        # Set up BPMs to actually do something
        bpm_nodes = self.accLattice.getNodesForSubstring("BPM", "drift")
        for node in bpm_nodes:
            node.addChildNode(BPMclass(), node.ENTRANCE)

        # connect PVs to lattice nodes
        self.pv_dict = {}
        for node in bpm_nodes:
            node_name = node.getName()
            bpm_node = node.getChildNodes(node.ENTRANCE)[0]
            pv_name = node_name + ":phaseAvg"
            self.pv_dict[pv_name] = PV(pv_name, "diagnostic", node, bpm_node.getPhaseAvg)
            pv_name = node_name + ":xAvg"
            self.pv_dict[pv_name] = PV(pv_name, "diagnostic", node, bpm_node.getXAvg)
            pv_name = node_name + ":yAvg"
            self.pv_dict[pv_name] = PV(pv_name, "diagnostic", node, bpm_node.getYAvg)
            pv_name = node_name.split(':')[1]
            pv_name = "SCL_Phys:" + pv_name + ":energy"
            self.pv_dict[pv_name] = PV(pv_name, "physics", node, bpm_node.getEnergy)

        cav_nodes = self.accLattice.getRF_Cavities()
        for node in cav_nodes:
            node_number = node.getName()[-3:]
            pv_name = "SCL_LLRF:FCM" + node_number + ":CtlPhaseSet"
            self.pv_dict[pv_name] = PV(pv_name, "setting", node, node.getPhase, node.setPhase)

        quad_nodes = self.accLattice.getQuads()
        for node in quad_nodes:
            node_name = node.getName()
            pv_name = node_name + ":B"
            self.pv_dict[pv_name] = PV(pv_name, "setting", node, node.getField, node.setField)

        self.pv_dict = dict(sorted(self.pv_dict.items(), key=lambda item: item[1].get_position()))

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
        self.bunch_dict = {}

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
        self.initial_pvs = {}
        for pv_name, pv in self.pv_dict.items():
            self.initial_pvs[pv_name] = pv.get_value()

    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None) -> dict[str, float]:
        return_dict = {}
        if setting_names is None:
            for pv_name, pv in self.pv_dict.items():
                if pv.get_pv_type() == "setting":
                    return_dict[pv_name] = pv.get_value()
        elif isinstance(setting_names, list):
            for pv_name in setting_names:
                return_dict[pv_name] = self.pv_dict[pv_name].get_value()
        elif isinstance(setting_names, str):
            return_dict[setting_names] = self.pv_dict[setting_names].get_value()
        return return_dict

    def get_measurements(self, measurement_names: Optional[Union[str, List[str]]] = None) -> dict[str, float]:
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        return_dict = {}
        if measurement_names is None:
            for pv_name, pv in self.pv_dict.items():
                if pv.get_pv_type() == "diagnostics" or "physics":
                    return_dict[pv_name] = pv.get_value()
        elif isinstance(measurement_names, list):
            for pv_name in measurement_names:
                return_dict[pv_name] = self.pv_dict[pv_name].get_value()
        elif isinstance(measurement_names, str):
            return_dict[measurement_names] = self.pv_dict[measurement_names].get_value()
        return return_dict

    def track(self, number_of_particles=1000) -> dict[str, float]:
        if self.upstream_change is not None:
            # freeze optics (clone)
            frozen_lattice = self.accLattice
            start_pv = self.pv_dict[self.upstream_change]
            if start_pv.get_node_type() == "RF_Cavity":
                start_node = self.accLattice.getRF_Cavity(start_pv.get_node_name()).getRF_GapNodes()[0]
            else:
                start_node = self.accLattice.getNodeForName(start_pv.get_node_name())
            start_ind = frozen_lattice.getNodeIndex(start_node)

            # setup initial bunch
            tracked_bunch = Bunch()
            self.bunch_dict[start_pv.get_node_name()].copyBunchTo(tracked_bunch)
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

    def update_optics(self, changed_optics: dict[str, float]):
        # update optics
        # figure out the most upstream element that changed
        # do not track here yet
        if self.upstream_change is None:
            upstream_check = self.accLattice.getLength()
        else:
            upstream_check = self.pv_dict[self.upstream_change].get_position()
        temp_upstream_check = upstream_check
        upstream_name = None
        change_flag = False
        for pv_name, new_value in changed_optics.items():
            pv = self.pv_dict[pv_name]
            if pv.get_pv_type() == "setting":
                current_value = pv.get_value()
                if new_value != current_value:
                    pv.set_value(new_value)
                    change_flag = True
                    pv_position = pv.get_position()
                    if pv_position < temp_upstream_check:
                        temp_upstream_check = pv_position
                        upstream_name = pv_name
                    print(f'New value of {pv_name} is {new_value}')
        if change_flag is True and 0 < temp_upstream_check < upstream_check:
            self.upstream_change = upstream_name

    def reset_optics(self):
        self.update_optics(self.initial_pvs)

    def save_optics(self, filename: Path = None):
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"optics_{timestamp}.json")
        saved_optics = {}
        for pv_name, pv in self.pv_dict.items():
            if pv.get_pv_type() == "setting":
                saved_optics[pv_name] = pv.get_value()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)

    def load_optics(self, filename: Path):
        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)

    def save_pvs(self, filename: Path = None):
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        saved_optics = {}
        for pv_name, pv in self.pv_dict.items():
            saved_optics[pv_name] = pv.get_value()
        with open(filename, "w") as json_file:
            json.dump(saved_optics, json_file, indent=4)


class BrandonModel(OrbitModel):
    pass
