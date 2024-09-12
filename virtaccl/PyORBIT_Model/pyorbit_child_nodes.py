import math
import sys
from typing import Dict

import numpy as np

from orbit.core.bunch import Bunch
from orbit.py_linac.lattice import BaseLinacNode


# A collection of classes that are attached to the lattice as child nodes for the virtual accelerator.


# A class that adds BPMs to the lattice. This class calculates both typical diagnostics (average position) and values
# that can't be directly measured (like energy).
class BPMclass(BaseLinacNode):
    node_type = "BPM"
    parameter_list = ['frequency', 'x_avg', 'y_avg', 'phi_avg', 'amp_avg', 'energy', 'beta', 'part_num']

    def __init__(self, child_name: str, frequency: float = 402.5e6):
        parameters = {'frequency': frequency, 'x_avg': 0.0, 'y_avg': 0.0, 'phi_avg': 0.0, 'amp_avg': 0.0,
                      'current': 0.0, 'energy': 0.0, 'beta': 0.0, 'part_num': 0}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(BPMclass.node_type)
        self.si_e_charge = 1.6021773e-19

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        sync_part = bunch.getSyncParticle()
        sync_beta = sync_part.beta()
        sync_energy = sync_part.kinEnergy()
        if part_num > 0:
            rf_freq = self.getParam('frequency')
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
            phi_avg = (phase_coeff * z_avg + sync_phase) % (2 * math.pi) - math.pi
            phi_rms = phase_coeff * math.sqrt((z_rms / part_num) - z_avg * z_avg)
            amp = abs(current * math.exp(-phi_rms * phi_rms / 2))

            self.setParam('x_avg', x_avg)
            self.setParam('y_avg', y_avg)
            self.setParam('phi_avg', phi_avg)
            self.setParam('amp_avg', amp)
            self.setParam('current', current)
            self.setParam('energy', sync_energy)
            self.setParam('beta', sync_beta)
            self.setParam('part_num', part_num)
        else:
            self.setParam('x_avg', 0.0)
            self.setParam('y_avg', 0.0)
            self.setParam('phi_avg', 0.0)
            self.setParam('amp_avg', 0.0)
            self.setParam('current', 0.0)
            self.setParam('energy', sync_energy)
            self.setParam('beta', sync_beta)
            self.setParam('part_num', part_num)

    def getFrequency(self):
        return self.getParam('frequency')

    def setFrequency(self, new_frequency: float) -> None:
        self.setParam('frequency', new_frequency)

    def getPhaseAvg(self):
        return self.getParam('phi_avg')

    def getXAvg(self):
        return self.getParam('x_avg')

    def getYAvg(self):
        return self.getParam('y_avg')

    def getCurrent(self):
        return self.getParam('current')

    def getEnergy(self):
        return self.getParam('energy')

    def getBeta(self):
        return self.getParam('beta')


# Class for wire scanners. This class simply returns histograms of the vertical and horizontal positions.
class WSclass(BaseLinacNode):
    node_type = "WireScanner"
    parameter_list = ['x_histogram', 'y_histogram', 'x_avg', 'y_avg']

    def __init__(self, child_name: str, bin_number: int = 50):
        parameters = {'x_histogram': np.array([[-10, 0], [10, 0]]), 'y_histogram': np.array([[-10, 0], [10, 0]]),
                      'x_avg': 0.0, 'y_avg': 0.0}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(WSclass.node_type)
        self.bin_number = bin_number

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        x_array = np.zeros(part_num)
        y_array = np.zeros(part_num)
        if part_num > 0:
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

            self.setParam('x_histogram', x_out)
            self.setParam('y_histogram', y_out)
            self.setParam('x_avg', x_avg)
            self.setParam('y_avg', y_avg)

        else:
            self.setParam('x_histogram', np.array([[-10, 0], [10, 0]]))
            self.setParam('y_histogram', np.array([[-10, 0], [10, 0]]))
            self.setParam('x_avg', 0)
            self.setParam('y_avg', 0)

    def getXHistogram(self):
        return self.getParam('x_histogram')

    def getYHistogram(self):
        return self.getParam('y_histogram')

    def getXAvg(self):
        return self.getParam('x_avg')

    def getYAvg(self):
        return self.getParam('y_avg')


# Class for wire scanners. This class simply returns histograms of the vertical and horizontal positions.
class ScreenClass(BaseLinacNode):
    node_type = "Screen"
    parameter_list = ['xy_histogram', 'x_axis', 'y_axis', 'x_avg', 'y_avg']

    def __init__(self, child_name: str, x_bin_number: int = 10, y_bin_number: int = 10):
        parameters = {'xy_histogram': np.zeros((2, 2)), 'x_axis': np.array([-10, 10]), 'y_axis': np.array([-10, 10]),
                      'x_avg': 0.0, 'y_avg': 0.0}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(ScreenClass.node_type)
        self.x_number = x_bin_number
        self.y_number = y_bin_number

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        x_array = np.zeros(part_num)
        y_array = np.zeros(part_num)
        if part_num > 0:
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

            xy_hist, y_edges, x_edges = np.histogram2d(y_array, x_array, bins=[self.x_number, self.y_number])

            x_avg /= part_num
            y_avg /= part_num

            self.setParam('xy_histogram', xy_hist)
            self.setParam('x_axis', x_edges)
            self.setParam('y_axis', y_edges)
            self.setParam('x_avg', x_avg)
            self.setParam('y_avg', y_avg)

        else:
            self.setParam('xy_histogram', np.zeros((2, 2)))
            self.setParam('x_axis', np.array([-10, 10]))
            self.setParam('y_axis', np.array([-10, 10]))
            self.setParam('x_avg', 0)
            self.setParam('y_avg', 0)

    def getXYHistogram(self):
        return self.getParam('xy_histogram')

    def getXAvg(self):
        return se<M-C-Undo>lf.getParam('x_avg')

    def getYAvg(self):
        return self.getParam('y_avg')


class DumpBunchClass(BaseLinacNode):
    node_type = "bunch_dumper"
    parameter_list = ['out_file']

    def __init__(self, child_name: str, out_file: str = 'bunch.dat'):
        BaseLinacNode.__init__(self, child_name)
        self.addParam('out_file', out_file)
        self.child_name = child_name
        self.setType(DumpBunchClass.node_type)

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        file_name = self.getParam('out_file')
        bunch.dumpBunch(file_name)
        print('Bunch dumped into ' + file_name)

    def setFileName(self, new_name: str):
        self.setParam('out_file', new_name)


# This class copies the bunch to a the bunch dictionary used to save the bunch at each optic.
class BunchCopyClass(BaseLinacNode):
    def __init__(self, child_name: str, bunch_key: str, bunch_dict: Dict[str, Bunch]):
        BaseLinacNode.__init__(self, child_name)
        self.child_name = child_name
        self.setType("bunch_saver")
        self.bunch_key = bunch_key
        self.bunch_dict = bunch_dict

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        bunch.copyBunchTo(self.bunch_dict[self.bunch_key])


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

class FCclass(BaseLinacNode):
    node_type = "FaradayCup"
    parameter_list = ['current', 'state']

    def __init__(self, child_name: str):
        parameters = {'current': 0.0, 'state': 1}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(FCclass.node_type)
        self.si_e_charge = 1.6021773e-19

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()

        if part_num > 0:
            initial_beam_current = paramsDict["beam_current"]
            initial_number = paramsDict['initial_particle_number']
            current = part_num / initial_number * initial_beam_current
            self.setParam('current', current)
        else:
            self.setParam('current', 0.0)

        live_state = self.getParam('state')
        if live_state == 1:
            if part_num > 0:
                bunch.deleteAllParticles()

    def getCurrent(self):
        return self.getParam('current')

    def getState(self):
        return self.getParam('state')

class BCMclass(BaseLinacNode):
    node_type = "BCM"
    parameter_list = ['current']

    def __init__(self, child_name: str):
        parameters = {'current': 0.0}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(BCMclass.node_type)
        self.si_e_charge = 1.6021773e-19

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]

        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            initial_beam_current = paramsDict["beam_current"]
            initial_number = paramsDict['initial_particle_number']
            current = part_num / initial_number * initial_beam_current
            self.setParam('current', current)
        else:
            self.setParam('current', 0.0)

    def getCurrent(self):
        return self.getParam('current')
