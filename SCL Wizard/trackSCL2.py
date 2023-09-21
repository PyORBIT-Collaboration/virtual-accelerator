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

phase_num = 25

tank = "SCL:Cav01a"

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

print("Bunch Generation completed.")
print(bunch_in.getSyncParticle().time(), bunch_in.getSyncParticle().beta())


BPMs = accLattice_SCL.getNodesForSubstring("BPM", "drift")
current_waveform = np.full([phase_num, len(BPMs)], -1.0)
beta_waveform = np.full([phase_num, len(BPMs)], -1.0)

class BPM():
    def trackActions(actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            name = paramsDict["parentNode"].getName()
            phase = paramsDict["lattice"].getNodeForName("SCL_RF:Cav01a:Rg01").getRF_Cavity().getPhase()
            beta = bunch.getSyncParticle().beta()
            phase_ind = np.where(phases == phase)[0][0]
            BPM_ind = BPMsDict[name]
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
            current_waveform[phase_ind,BPM_ind] = part_num
            beta_waveform[phase_ind, BPM_ind] = beta

BPMsDict = {}
bpm_count = 0
for BPM_node in BPMs:
    BPM_node.addChildNode(BPM, BPM_node.ENTRANCE)
    BPMsDict[BPM_node.getName()] = bpm_count
    bpm_count += 1


cavities = accLattice_SCL.getNodesForSubstring("Cav", "drift")
cavDict = {}
for subcavity in cavities:
    cavity = subcavity.getRF_Cavity()
    if cavity.getName() not in cavDict:
        cavity.setAmp(0.0)
        if cavity.getName() == tank:
            cavDict[cavity.getName()] = cavity
            cavity.setAmp(1.0)

# track through the lattice
paramsDict = {"old_pos": -1.0, "count": 0, "pos_step": 0.1}

phases = np.zeros(phase_num)
for p in range(phase_num):
    phase = (p / (phase_num - 1) * 2 - 1) * np.pi
    phases[p] = phase

for cav_name in cavDict:
    cavity = cavDict[cav_name]
    for phase in phases:
        cavity.setPhase(phase)

        print("Tracking", cav_name, phase)

        bunch_in = Bunch()
        bunch_in.readBunch(bunch_file)
        bunch_in.getSyncParticle().time(0.0)

        accLattice_SCL.trackDesignBunch(bunch_in)
        accLattice_SCL.trackBunch(bunch_in)

np.save('current', current_waveform)
np.save('beta', beta_waveform)


print("Tracking completed.")
