import math
from typing import Dict

import numpy as np
from orbit.core.bunch import Bunch


# A collection of classes that are attached to the lattice as child nodes for the virtual accelerator.


# A class that adds BPMs to the lattice. This class calculates both typical diagnostics (average position) and values
# that can't be directly measured (like energy).
class BPMclass:
    def __init__(self, child_name: str, frequency: float = 402.5e6):
        self.parameters = {'frequency': frequency, 'x_avg': 0.0, 'y_avg': 0.0, 'phi_avg': 0.0, 'amp_avg': 0.0,
                           'current': 0.0, 'energy': 0.0, 'beta': 0.0, 'part_num': 0}
        self.child_name = child_name
        self.node_type = 'BPM'
        self.si_e_charge = 1.6021773e-19

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        sync_part = bunch.getSyncParticle()
        sync_beta = sync_part.beta()
        sync_energy = sync_part.kinEnergy()
        if part_num > 0:
            rf_freq = self.parameters['frequency']
            BPM_name = paramsDict["parentNode"].getName()
            initial_beam_current = paramsDict["beam_current"]
            initial_number = paramsDict['initial_particle_number']
            current = part_num / initial_number * initial_beam_current
            phase_coeff = 2 * math.pi / (sync_beta * 2.99792458e8 / rf_freq)
            sync_phase = sync_part.time() * rf_freq * 2 * math.pi
            x_avg, y_avg, z_avg, z_rms = 0, 0, 0, 0
            for n in range(part_num):
                x, y, z = bunch.x(n), bunch.y(n), bunch.z(n)
                x_avg += x
                y_avg += y
                z_avg += z
                z_rms += z * z
            x_avg /= part_num
            y_avg /= part_num
            z_avg /= part_num
            phi_rms = phase_coeff * math.sqrt(z_rms / part_num)
            phi_avg = (phase_coeff * z_avg + sync_phase) % (2 * math.pi) - math.pi
            amp = abs(current * math.exp(-phi_rms * phi_rms / 2))
            self.parameters['x_avg'] = x_avg
            self.parameters['y_avg'] = y_avg
            self.parameters['phi_avg'] = phi_avg
            self.parameters['amp_avg'] = amp
            self.parameters['current'] = current
            self.parameters['energy'] = sync_energy
            self.parameters['beta'] = sync_beta
            self.parameters['part_num'] = part_num
            # print(BPM_name + " : " + str(part_num))
        else:
            self.parameters['x_avg'] = 0.0
            self.parameters['y_avg'] = 0.0
            self.parameters['phi_avg'] = 0.0
            self.parameters['amp_avg'] = 0.0
            self.parameters['current'] = 0.0
            self.parameters['energy'] = sync_energy
            self.parameters['beta'] = sync_beta
            self.parameters['part_num'] = part_num

    def getFrequency(self):
        return self.parameters['frequency']

    def setFrequency(self, new_frequency: float) -> None:
        self.parameters['frequency'] = new_frequency

    def getPhaseAvg(self):
        return self.parameters['phi_avg']

    def getXAvg(self):
        return self.parameters['x_avg']

    def getYAvg(self):
        return self.parameters['y_avg']

    def getCurrent(self):
        return self.parameters['current']

    def getEnergy(self):
        return self.parameters['energy']

    def getBeta(self):
        return self.parameters['beta']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []


# Class for wire scanners. This class simply returns histograms of the vertical and horizontal positions.
class WSclass:
    def __init__(self, child_name: str, bin_number: int = 50):
        self.parameters = {'x_histogram': np.array([[-10, 0], [10, 0]]), 'y_histogram': np.array([[-10, 0], [10, 0]]),
                           'x_avg': 0.0, 'y_avg': 0.0}
        self.child_name = child_name
        self.bin_number = bin_number
        self.node_type = 'WireScanner'

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
            x_avg = 0
            y_avg = 0
            for n in range(part_num):
                x, y, z = bunch.x(n), bunch.y(n), bunch.z(n)
                x_array[n] = x
                y_array[n] = y
                x_avg += x
                y_avg += y

            x_limits = np.array([np.min(x_array), np.max(x_array)]) * 1.1
            x_bin_edges = np.linspace(x_limits[0], x_limits[1], self.bin_number + 1)
            x_hist, x_bins = np.histogram(x_array, bins=x_bin_edges)
            x_positions = (x_bins[:-1] + x_bins[1:]) / 2
            x_out = np.column_stack((x_positions, x_hist))

            y_limits = np.array([np.min(y_array), np.max(y_array)]) * 1.1
            y_bin_edges = np.linspace(y_limits[0], y_limits[1], self.bin_number + 1)
            y_hist, y_bins = np.histogram(y_array, bins=y_bin_edges)
            y_positions = (y_bins[:-1] + y_bins[1:]) / 2
            y_out = np.column_stack((y_positions, y_hist))

            x_avg /= part_num
            y_avg /= part_num

            self.parameters['x_histogram'] = x_out
            self.parameters['y_histogram'] = y_out
            self.parameters['x_avg'] = x_avg
            self.parameters['y_avg'] = y_avg

        else:
            self.parameters['x_histogram'] = np.array([[-10, 0], [10, 0]])
            self.parameters['y_histogram'] = np.array([[-10, 0], [10, 0]])
            self.parameters['x_avg'] = 0
            self.parameters['y_avg'] = 0


    def getXHistogram(self):
        return self.parameters['x_histogram']

    def getYHistogram(self):
        return self.parameters['y_histogram']

    def getXAvg(self):
        return self.parameters['x_avg']

    def getYAvg(self):
        return self.parameters['y_avg']

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


# This class copies the bunch to a the bunch dictionary used to save the bunch at each optic.
class BunchCopyClass:
    def __init__(self, pyorbit_name: str, bunch_dict: Dict[str, Bunch]):
        self.pyorbit_name = pyorbit_name
        self.bunch_dict = bunch_dict
        self.node_type = 'bunch_saver'

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            bunch.copyBunchTo(self.bunch_dict[self.pyorbit_name])


# This class removes all bunch particles if the bunch is outside of the beta limits of the cavity.
class RF_Gap_Aperture:
    def __init__(self, gap_name: str, beta_min: float, beta_max: float):
        self.gap_name = gap_name
        self.beta_min = beta_min
        self.beta_max = beta_max

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        sync_part = bunch.getSyncParticle()
        sync_beta = sync_part.beta()
        if not self.beta_min < sync_beta < self.beta_max:
            bunch.deleteAllParticles()
