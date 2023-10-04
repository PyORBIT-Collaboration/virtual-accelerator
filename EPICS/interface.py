import math
from datetime import datetime
from typing import Optional, Union, List
import sys
from pathlib import Path
import json

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory
from orbit.core.bunch import Bunch


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

        # initialize all settings (cavity and measurements (BPM)
        self.pv_dict = {}
        self.position_dict = {}
        bpm_nodes = self.accLattice.getNodesForSubstring("BPM", "drift")
        for node in bpm_nodes:
            node_name = node.getName()
            position = node.getPosition()
            pv_name = node_name + ":phaseAvg"
            self.pv_dict[pv_name] = 23
            self.position_dict[pv_name] = position
            pv_name = node_name + ":xAvg"
            self.pv_dict[pv_name] = 0
            self.position_dict[pv_name] = position
            pv_name = node_name + ":yAvg"
            self.pv_dict[pv_name] = 0
            self.position_dict[pv_name] = position
            pv_name = node_name.split(':')[1]
            pv_name = "SCL_Phys:" + pv_name + ":energy"
            self.pv_dict[pv_name] = 188
            self.position_dict[pv_name] = position

        cav_nodes = self.accLattice.getRF_Cavities()
        for node in cav_nodes:
            rf_phase = node.getPhase()
            position = node.getPosition()
            node_number = node.getName()[-3:]
            pv_name = "SCL_LLRF:FCM" + node_number + ":CtlPhaseSet"
            self.pv_dict[pv_name] = rf_phase
            self.position_dict[pv_name] = position

        quad_nodes = self.accLattice.getQuads()
        for node in quad_nodes:
            field = node.getField()
            position = node.getPosition()
            node_name = node.getName()
            pv_name = node_name + ":B"
            self.pv_dict[pv_name] = field
            self.position_dict[pv_name] = position

        self.pv_dict = dict(sorted(self.pv_dict.items(), key=lambda item: self.position_dict.get(item[0], 0)))
        self.position_dict = dict(sorted(self.position_dict.items(), key=lambda item: item[1]))

        class BPMclass:
            def trackActions(actionsContainer, paramsDict):
                bunch = paramsDict["bunch"]
                part_num = bunch.getSizeGlobal()
                if part_num > 0:
                    rf_freq = 402.5e6
                    BPM_name = paramsDict["parentNode"].getName()
                    sync_part = bunch.getSyncParticle()
                    phase_coeff = 360.0 / (sync_part.beta() * 2.99792458e8 / rf_freq)
                    sync_phase = (sync_part.time() * rf_freq * 2 * math.pi) % (2 * math.pi) - math.pi
                    sync_energy = sync_part.kinEnergy()
                    x_avg, xp_avg, y_avg, yp_avg, z_avg, dE_avg = 0, 0, 0, 0, 0, 0
                    for n in range(part_num):
                        x, xp, y, yp, z, dE = bunch.x(n), bunch.xp(n), bunch.y(n), bunch.yp(n), bunch.z(n), bunch.dE(n)
                        x_avg += x
                        xp_avg += xp
                        y_avg += y
                        yp_avg += yp
                        z_avg += z
                        dE_avg += dE
                    x_avg /= part_num
                    xp_avg /= part_num
                    y_avg /= part_num
                    yp_avg /= part_num
                    z_avg /= part_num
                    phi_avg = phase_coeff * z_avg + sync_phase
                    dE_avg /= part_num
                    self.pv_dict[BPM_name + ":phaseAvg"] = phi_avg
                    self.pv_dict[BPM_name + ":xAvg"] = x_avg
                    self.pv_dict[BPM_name + ":yAvg"] = y_avg
                    self.pv_dict["SCL_Phys:" + BPM_name.split(':')[1] + ":energy"] = sync_energy
                    # print(BPM_name + " triggered")

        for node in bpm_nodes:
            node.addChildNode(BPMclass, node.ENTRANCE)

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

        # store initial settings
        self.initial_optics = self.pv_dict.copy()
        self.upstream_change = "None"

    def get_settings(self, setting_names: Optional[Union[str, List[str]]] = None):
        return_dict = {}
        if setting_names is None:
            for pv in self.pv_dict:
                if "Diag" not in pv and "Phys" not in pv:
                    return_dict[pv] = self.pv_dict[pv]
                    print(pv + " : " + str(self.pv_dict[pv]))
        elif isinstance(setting_names, list):
            for pv_name in setting_names:
                return_dict[pv_name] = self.pv_dict[pv_name]
                print(pv_name + " : " + str(self.pv_dict[pv_name]))
        else:
            return_dict = self.pv_dict[setting_names]
            print(setting_names + " : " + str(self.pv_dict[setting_names]))
        return return_dict
        # return {'SCL_LLRF:FCM01a:setCtlPhase': 23,
        #        }

    def get_measurements(self, measurement_names: Optional[Union[str, List[str]]] = None):
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        if measurement_names is None:
            for pv in self.pv_dict:
                if "Diag" in pv or "Phys" in pv:
                    print(pv + " : " + str(self.pv_dict[pv]))
        elif isinstance(measurement_names, list):
            for pv_name in measurement_names:
                print(self.pv_dict[pv_name])
        else:
            print(self.pv_dict[measurement_names])

        # return {'SCL_Diag:BPM00:phaseAvg': 23,
        #        'SCL_Phys:BPM00:energy': 188,
        #        }

    def track(self, number_of_particles=1000) -> dict[str, float]:
        if self.upstream_change != "None":
            # freeze optics (clone)
            frozen_lattice = self.accLattice
            start_node_name = self.upstream_change
            if "Cav" in start_node_name:
                start_node = self.accLattice.getRF_Cavity(start_node_name).getRF_GapNodes()[0]
            else:
                start_node = self.accLattice.getNodeForName(start_node_name)
            start_ind = frozen_lattice.getNodeIndex(start_node)

            # setup initial bunch
            tracked_bunch = Bunch()
            self.bunch_dict[start_node_name].copyBunchTo(tracked_bunch)
            for n in range(tracked_bunch.getSizeGlobal()):
                if n + 1 > number_of_particles:
                    tracked_bunch.deleteParticleFast(n)
            tracked_bunch.compress()

            # and track new setup
            # frozen_lattice.trackDesignBunch(tracked_bunch, index_start=start_ind)
            frozen_lattice.trackBunch(tracked_bunch, index_start=start_ind)
            self.upstream_change = "None"

        else:
            print("No changes to track through.")
            # if nothing changed do not track

    def update_optics(self, changed_optics: dict[str, float]):
        # update optics
        # figure out the most upstream element that changed
        # do not track here yet
        if self.upstream_change == "None":
            upstream_check = self.accLattice.getLength()
        else:
            upstream_check = self.position_dict[self.upstream_change]
            # if "Cav" in self.upstream_change:
            #    upstream_check = self.accLattice.getRF_Cavity(self.upstream_change).getPosition()
            # else:
            #    upstream_check = self.accLattice.getNodeForName(self.upstream_change).getPosition()
        change_flag = False
        for key, value in changed_optics.items():
            pv_position = -1
            k_split = key.split(':')

            if k_split[0] == "SCL_LLRF":
                node_name = "SCL:Cav" + k_split[1][-3:]
                rf_node = self.accLattice.getRF_Cavity(node_name)

                if k_split[2] == "CtlPhaseSet":
                    current_v = rf_node.getPhase()
                    if value != current_v:
                        rf_node.setPhase(value)
                        self.pv_dict[key] = value
                        pv_position = self.position_dict[key]
                        change_flag = True
                        print(f'New value of {key} is {value}')
                    # else:
                    #    print(f'Value of {k} did not change.')

            elif "Diag" not in k_split[0] and "Phys" not in k_split[0]:
                node_name = ':'.join(k_split[:2])
                node = self.accLattice.getNodeForName(node_name)
                if node.getType() == "linacQuad":
                    current_v = node.getField()
                    if value != current_v:
                        node.setField(value)
                        self.pv_dict[key] = value
                        pv_position = self.position_dict[key]
                        change_flag = True
                        print(f'New value of {key} is {value}')
                    # else:
                    #    print(f'Value of {k} did not change.')

            if change_flag is True and 0 < pv_position < upstream_check:
                self.upstream_change = node_name
            # { SCL_LLRF:FCM01a:setPhase: 23,
            #   SCL_Mag:Pkpkpgk: 10 }

    def reset_optics(self):
        self.update_optics(self.initial_optics)

    def save_optics(self, filename: Path = None):
        # timestamp being default name
        if filename is None:
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
            filename = Path(f"PVs_{timestamp}.json")
        with open(filename, "w") as json_file:
            json.dump(self.pv_dict, json_file, indent=4)

    def load_optics(self, filename: Path):
        with open(filename, "r") as json_file:
            input_optics = json.load(json_file)
            self.update_optics(input_optics)


class BrandonModel(OrbitModel):
    pass
