#! /usr/bin/env python

"""
This script will track the bunch through the SNS Linac.

At the beginning the lattice can be modified by replacing
the BaseRF_Gap nodes with AxisFieldRF_Gap nodes for
the selected sequences. These nodes will use the
RF fields at the axis of the RF gap to track the bunch.
The usual BaseRF_Gap nodes have a zero length.

The apertures are added to the lattice.
"""

import sys
import math
import random
import time

import numpy as np

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

# from linac import the C++ RF gap classes
# ---- for these RF gap models parameters are defined by the synchronous particle
from orbit.core.linac import BaseRfGap, MatrixRfGap, RfGapTTF

# ---- variants of slow RF gap models which updates all RF gap parameters
# ---- individually for each particle in the bunch
from orbit.core.linac import BaseRfGap_slow, RfGapTTF_slow, RfGapThreePointTTF_slow


from orbit.bunch_generators import TwissContainer
from orbit.bunch_generators import WaterBagDist3D, GaussDist3D, KVDist3D

from orbit.core.bunch import Bunch, BunchTwissAnalysis

from orbit.lattice import AccLattice, AccNode, AccActionsContainer

from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice
from orbit.py_linac.lattice_modifications import Add_rfgap_apertures_to_lattice
from orbit.py_linac.lattice_modifications import AddMEBTChopperPlatesAperturesToSNS_Lattice
from orbit.py_linac.lattice_modifications import AddScrapersAperturesToLattice

# ---- BaseRF_Gap to  AxisFieldRF_Gap replacement  ---- It is a possibility ----------
from orbit.py_linac.lattice_modifications import Replace_BaseRF_Gap_to_AxisField_Nodes
from orbit.py_linac.lattice_modifications import Replace_BaseRF_Gap_and_Quads_to_Overlapping_Nodes
from orbit.py_linac.lattice_modifications import Replace_Quads_to_OverlappingQuads_Nodes

from orbit.py_linac.overlapping_fields import SNS_EngeFunctionFactory

random.seed(100)

phase_num = 51

#tank = "SCL:Cav01a"

BPMs = ["SCL_Diag:BPM31", "SCL_Diag:BPM32"]

bunch_file = "SCL_in.dat"

names_SCL = ["SCLMed", "SCLHigh"]


# ---- create the factory instance
sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)

# ---- the XML file name with the structure
xml_file_name = "sns_linac.xml"

# ---- make lattice from XML file
accLattice_SCL = sns_linac_factory.getLinacAccLattice(names_SCL, xml_file_name)

print("Linac lattice is ready.")

bunch_in = Bunch()
bunch_in.readBunch(bunch_file)
bunch_in.getSyncParticle().time(0.0)

print(bunch_in.getSizeGlobal())
for n in range(bunch_in.getSizeGlobal()):
    if n+1 > 10000:
        bunch_in.deleteParticleFast(n)
bunch_in.compress()
print(bunch_in.getSizeGlobal())

print("Bunch Generation completed.")
#print(bunch_in.getSyncParticle().time(), bunch_in.getSyncParticle().beta())


cavities = accLattice_SCL.getNodesForSubstring("Cav", "drift")
cavDict = {}
cav_count = 0
for subcavity in cavities:
    cavity = subcavity.getRF_Cavity()
    if cavity.getName() not in cavDict:
        cavity.setAmp(0.0)
        cavDict[cavity.getName()] = cav_count
        cav_count += 1
        #if cavity.getName() == tank:
        #    cavDict[cavity.getName()] = cavity
        #    cavity.setAmp(1.0)

#current_waveform = np.full([phase_num, len(BPMs)], -1.0)
phase_waveform = np.full([len(cavDict), phase_num, len(BPMs)], -1.0)
waveformDict = {}

class BPM_class():
    def trackActions(actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            BPM_name = paramsDict["parentNode"].getName()
            Synch_phase = (bunch.getSyncParticle().time() * 402.5e6 * 2 * np.pi) % (2 * np.pi) - np.pi
            #cavphase = paramsDict["lattice"].getNodeForName("SCL_RF:Cav01a:Rg01").getRF_Cavity().getPhase()
            #phase_ind = np.where(phases == phase)[0][0]
            #BPM_ind = BPMsDict[BPM_name]
            """
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
            dE_avg /= part_num
            #str = f"{name} {part_num} {beta} {x_avg} {xp_avg} {y_avg} {yp_avg} {z_avg} {dE_avg}\n"
            """
            #current_waveform[phase_ind,BPM_ind] = part_num
            #phase_waveform[phase_ind, BPM_ind] = measured_phase
            waveformDict[BPM_name] = Synch_phase

BPMsDict = {}
BPM_count = 0
for BPM in BPMs:
    BPM_node = accLattice_SCL.getNodeForName(BPM)
    BPM_node.addChildNode(BPM_class, BPM_node.ENTRANCE)
    BPMsDict[BPM] = BPM_count
    BPM_count += 1

# track through the lattice
paramsDict = {"old_pos": -1.0, "count": 0, "pos_step": 0.1}

phases = np.zeros(phase_num)
for p in range(phase_num):
    phase = (p / (phase_num - 1) * 2 - 1) * np.pi
    phases[p] = phase

#T_array = np.full([len(cavDict), phase_num], -1.0)
DT = np.full([len(cavDict), phase_num], -1.0)
limits = np.full([len(cavDict), 2], -1.0)
energies = np.load("energies.npy")
for cav in range(energies.shape[0]):
    Pmax = np.max(energies[cav,:])
    Pmin = np.min(energies[cav, :])
    limits[cav,:] = Pmin, Pmax

dist = accLattice_SCL.getNodeForName(BPMs[1]).getPosition() - accLattice_SCL.getNodeForName(BPMs[0]).getPosition()
Terror = 1e-6

for cav_name in cavDict:
    cavity = accLattice_SCL.getRF_Cavity(cav_name)
    cavity.setAmp(1.0)
    for phase in phases:
        cavity.setPhase(phase)

        print("Tracking", cav_name, phase)

        bunch_in = Bunch()
        bunch_in.readBunch(bunch_file)
        bunch_in.getSyncParticle().time(0.0)

        for n in range(bunch_in.getSizeGlobal()):
            if n + 1 > 100:
                bunch_in.deleteParticleFast(n)
        bunch_in.compress()

        accLattice_SCL.trackDesignBunch(bunch_in)
        accLattice_SCL.trackBunch(bunch_in)

        phase1, phase0 = waveformDict[BPMs[1]], waveformDict[BPMs[0]]

        realT = bunch_in.getSyncParticle().kinEnergy()
        #T_array[cavDict[cav_name], np.where(phases == phase)[0][0]] = T

        T = 100000000
        n = 0
        count = 0
        while np.abs(realT - T) > Terror:
            t = ((phase1 + n * 2 * np.pi) - phase0) / (402.5e6 * 2 * np.pi)
            beta = dist / t / 299792458
            if beta < 1 and beta > 0:
                gamma = 1 / math.sqrt(1 - beta * beta)
                T = (gamma - 1) * 0.939294
                #print(n, beta, gamma, T)
            n += 1

        DT[cavDict[cav_name], np.where(phases == phase)[0][0]] = realT - T

#np.save('energies', T_array)
np.save('delta_energies', DT)
#np.save('energies_count', T_count)

sys.exit()

#np.save('current', current_waveform)
np.save('phases', phase_waveform)

d = accLattice_SCL.getNodeForName(BPMs[1]).getPosition() - accLattice_SCL.getNodeForName(BPMs[0]).getPosition()
beta = 1
n = 0
while beta >= 0.3:
    t = ((phase_waveform[0,1] + n * 2 * np.pi) - phase_waveform[0,0]) / (402.5e6 * 2 * np.pi)
    beta = d / t / 299792458
    if beta < 1:
        gamma = 1 / math.sqrt(1 - beta * beta)
        T = (gamma - 1) * 0.939294
        print(n, beta, gamma, T)
    n += 1
print(n-1, beta, gamma, T)

print("Tracking completed.")
