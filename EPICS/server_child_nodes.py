import math
from typing import Dict

import numpy as np
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
            phase_coeff = 2 * math.pi / (sync_beta * 2.99792458e8 / rf_freq)
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
        else:
            self.parameters['x_avg'] = 0.0
            self.parameters['y_avg'] = 0.0
            self.parameters['phi_avg'] = 0.0
            self.parameters['energy'] = 0.0
            self.parameters['beta'] = 0.0

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


class WSclass:
    def __init__(self, child_name: str):
        self.parameters = {'x_histogram': np.zeros((0, 0)), 'y_histogram': np.zeros((0, 0))}
        self.child_name = child_name
        self.node_type = 'WireScanner'

        self.high_res_bins = 30
        self.low_res_bins = 20

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        x_array = np.zeros(part_num)
        y_array = np.zeros(part_num)
        if part_num > 0:
            WS_name = paramsDict["parentNode"].getName()
            sync_part = bunch.getSyncParticle()
            sync_beta = sync_part.beta()
            sync_energy = sync_part.kinEnergy()
            for n in range(part_num):
                x, y, z = bunch.x(n), bunch.y(n), bunch.z(n)
                x_array[n] = x
                y_array[n] = y

            high_res_bins = self.high_res_bins
            low_res_bins = self.low_res_bins

            x_mean = np.mean(x_array)
            x_sigma = np.std(x_array)
            x_high_res_bins = np.linspace(x_mean - 2 * x_sigma, x_mean + 2 * x_sigma, high_res_bins + 1)
            x_low_res_bin = np.linspace(x_mean - 5 * x_sigma, x_mean - 2 * x_sigma, low_res_bins // 2)
            x_low_res_bin = np.concatenate(
                (x_low_res_bin, np.linspace(x_mean + 2 * x_sigma, x_mean + 5 * x_sigma, low_res_bins // 2)))
            all_x_bins = np.sort(np.concatenate((x_low_res_bin, x_high_res_bins[1:-1])))
            x_hist, x_bins = np.histogram(x_array, bins=all_x_bins)
            x_positions = (all_x_bins[:-1] + all_x_bins[1:]) / 2
            x_out = np.column_stack((x_positions, x_hist))

            y_mean = np.mean(y_array)
            y_sigma = np.std(y_array)
            y_high_res_bins = np.linspace(y_mean - 2 * y_sigma, y_mean + 2 * y_sigma, high_res_bins + 1)
            y_low_res_bin = np.linspace(y_mean - 5 * y_sigma, y_mean - 2 * y_sigma, low_res_bins // 2)
            y_low_res_bin = np.concatenate(
                (y_low_res_bin, np.linspace(y_mean + 2 * y_sigma, y_mean + 5 * y_sigma, low_res_bins // 2)))
            all_y_bins = np.sort(np.concatenate((y_low_res_bin, y_high_res_bins)))
            y_hist, y_bins = np.histogram(y_array, bins=all_y_bins)
            y_positions = (all_y_bins[:-1] + all_y_bins[1:]) / 2
            y_out = np.column_stack((y_positions, y_hist))

            self.parameters['x_histogram'] = x_out
            self.parameters['y_histogram'] = y_out

    def getXHistogram(self):
        return self.parameters['x_histogram']

    def getYHistogram(self):
        return self.parameters['y_histogram']

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
