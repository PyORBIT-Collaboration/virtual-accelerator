import math
from typing import Dict
from orbit.core.bunch import Bunch


class BPMclass:
    def __init__(self, child_name: str):
        self.parameters = {'x_avg': 0.0, 'y_avg': 0.0, 'phi_avg': 0.0, 'energy': 0.0, 'beta': 0.0}
        self.child_name = child_name
        self.node_type = 'BPM'

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            rf_freq = 402.5e6
            BPM_name = paramsDict["parentNode"].getName()
            sync_part = bunch.getSyncParticle()
            sync_beta = sync_part.beta()
            phase_coeff = 360.0 / (sync_beta * 2.99792458e8 / rf_freq)
            sync_phase = (sync_part.time() * rf_freq * 2 * math.pi) % (2 * math.pi) - math.pi
            sync_energy = sync_part.kinEnergy()
            x_avg, y_avg, z_avg = 0, 0, 0
            for n in range(part_num):
                x, y, z = bunch.x(n), bunch.y(n), bunch.z(n)
                x_avg += x
                y_avg += y
                z_avg += z
            x_avg /= part_num
            y_avg /= part_num
            z_avg /= part_num
            phi_avg = phase_coeff * z_avg + sync_phase
            self.parameters['x_avg'] = x_avg
            self.parameters['y_avg'] = y_avg
            self.parameters['phi_avg'] = phi_avg
            self.parameters['energy'] = sync_energy
            self.parameters['beta'] = sync_beta
            # print(BPM_name + " : " + str(x_avg))

    def getPhaseAvg(self):
        return self.parameters['phi_avg']

    def getXAvg(self):
        return self.parameters['x_avg']

    def getYAvg(self):
        return self.parameters['y_avg']

    def getEnergy(self):
        return self.parameters['energy']

    def getBeta(self):
        return self.parameters['beta']

    def getParam(self, param: str):
        return self.parameters[param]

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []


class BunchCopyClass:
    def __init__(self, pyorbit_name: str, bunch_dict: Dict[str, Bunch]):
        self.pyorbit_name = pyorbit_name
        self.bunch_dict = bunch_dict
        self.node_type = 'bunch_saver'

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            node = paramsDict["parentNode"]
            bunch.copyBunchTo(self.bunch_dict[self.pyorbit_name])
            # self.bunch_dict[node_name].getSyncParticle().time(0.0)
