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

file_out = open("node_tree", "w")

names_SCL = ["SCLMed", "SCLHigh"]

# ---- create the factory instance
sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)

# ---- the XML file name with the structure
xml_file_name = "sns_linac.xml"

# ---- make lattice from XML file
accLattice_SCL = sns_linac_factory.getLinacAccLattice(names_SCL, xml_file_name)

print("Linac lattice is ready.")


def printNodeTree(list_of_nodes, level=0):
    for node in list_of_nodes:
        indent = " " * level * 4
        file_out.write(indent + str(node.getName()) + "\n")
        children = node.getAllChildren()
        if len(children) > 0:
            printNodeTree(children, level+1)

file_out = open("node_tree", "w")

nodes = accLattice_SCL.getNodes()
printNodeTree(nodes)

file_out.close()

sys.exit()


#Cavities = accLattice_SCL.getNodesForSubstring("Cav", "SCLMed")
#print(Cavities[0].getRF_Cavity().getPhase(), Cavities[0].getGapPhase(), Cavities[1].getGapPhase(), Cavities[2].getGapPhase())
#accLattice_SCL.trackDesignBunch(bunch_in)
#print(Cavities[0].getRF_Cavity().getPhase(), Cavities[0].getGapPhase(), Cavities[1].getGapPhase(), Cavities[2].getGapPhase())
#Cavities[0].getRF_Cavity().setPhase(1.9)
#accLattice_SCL.trackDesignBunch(bunch_in)
#print(Cavities[0].getRF_Cavity().getPhase(), Cavities[0].getGapPhase(), Cavities[1].getGapPhase(), Cavities[2].getGapPhase())

#print(Cavities[0].getRF_Cavity().getAmp(), Cavities[0].getParam('E0TL'), Cavities[1].getParam('E0TL'), Cavities[2].getParam('E0TL'))
#accLattice_SCL.trackDesignBunch(bunch_in)
#print(Cavities[0].getRF_Cavity().getAmp(), Cavities[0].getParam('E0TL'), Cavities[1].getParam('E0TL'), Cavities[2].getParam('E0TL'))
#Cavities[0].getRF_Cavity().setAmp(0.5)
#accLattice_SCL.trackDesignBunch(bunch_in)
#print(Cavities[0].getRF_Cavity().getAmp(), Cavities[0].getParam('E0TL'), Cavities[1].getParam('E0TL'), Cavities[2].getParam('E0TL'))
#sys.exit()


# track through the lattice
paramsDict = {"old_pos": -1.0, "count": 0, "pos_step": 0.1}
actionContainer = AccActionsContainer("Test Design Bunch Tracking")

print(" N                node   position  eKin Nparts ")

twiss_analysis = BunchTwissAnalysis()
pos_start = 0.0
current_cav = 0

def action_entrance(paramsDict):
    node = paramsDict["node"]
    bunch = paramsDict["bunch"]
    pos = paramsDict["path_length"]
    if paramsDict["old_pos"] == pos:
        return
    if paramsDict["old_pos"] + paramsDict["pos_step"] > pos:
        return
    paramsDict["old_pos"] = pos
    paramsDict["count"] += 1
    twiss_analysis.analyzeBunch(bunch)
    nParts = bunch.getSizeGlobal()
    eKin = bunch.getSyncParticle().kinEnergy() * 1.0e3
    s_prt = " %5d  %35s  %4.5f " % (paramsDict["count"], node.getName(), pos + pos_start)
    s_prt += "  %10.6f   %8d " % (eKin, nParts)
    #print(s_prt)

def action_exit(paramsDict):
    action_entrance(paramsDict)


#actionContainer.addAction(action_entrance, AccActionsContainer.ENTRANCE)
#actionContainer.addAction(action_exit, AccActionsContainer.EXIT)
#actionContainer.addAction(action_BPM, BPMs[1].ENTRANCE)

# set up design
accLattice_SCL.trackDesignBunch(bunch_in)
accLattice_SCL.trackBunch(bunch_in, paramsDict=paramsDict, actionContainer=actionContainer)
bunch_in.dumpBunch("bunch_out.dat")

print(bunch_in.getSyncParticle().time(), bunch_in.getSyncParticle().beta())

print("Design tracking completed.")
