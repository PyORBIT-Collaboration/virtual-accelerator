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

names_SCL = ["SCLMed", "SCLHigh"]

# ---- create the factory instance
sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)

# ---- the XML file name with the structure
xml_file_name = "sns_linac.xml"

# ---- make lattice from XML file
accLattice_SCL = sns_linac_factory.getLinacAccLattice(names_SCL, xml_file_name)

print("Linac lattice is ready.")

unique_devices = set()
ignore_nodes = {'drift', 'tilt', 'fringe'}


def printNodeTree(list_of_nodes, cavities="", quads="", correctors="", bpms=""):
    for node in list_of_nodes:
        node_type = node.getType()
        if not any(substring in node_type for substring in ignore_nodes):
            if node_type == 'baserfgap':
                node_name = node.getRF_Cavity().getName()
                node_number = node_name[-3:]
                device_name = "SCL_LLRF:FCM" + node_number
                line = "Cavity " + " " + device_name + " " + node_name
                if device_name not in unique_devices:
                    cavities += line + "\n"
                    unique_devices.add(device_name)

            elif node_type == 'markerLinacNode':
                node_name = node.getName()
                if "BPM" in node_name:
                    device_name = node_name
                    line = "BPM " + " " + device_name + " " + node_name
                    if device_name not in unique_devices:
                        bpms += line + "\n"
                        unique_devices.add(device_name)

            elif node_type == 'linacQuad':
                node_name = node.getName()
                device_name = node_name
                line = "Quad " + " " + device_name + " " + node_name
                if device_name not in unique_devices:
                    quads += line + "\n"
                    unique_devices.add(device_name)

            elif node_type == 'dch' or 'dcv':
                node_name = node.getName()
                device_name = node_name
                line = "Corrector" + " " + device_name + " " + node_name
                if device_name not in unique_devices:
                    correctors += line + "\n"
                    unique_devices.add(device_name)
            children = node.getAllChildren()
            if len(children) > 0:
                cavities, quads, correctors, bpms = printNodeTree(children, cavities, quads, correctors, bpms)
    return cavities, quads, correctors, bpms


nodes = accLattice_SCL.getNodes()
Cavities, Quads, Correctors, BPMs = printNodeTree(nodes)

file_out = open("pvs_in", "w")
file_out.write("Cavities\n" + Cavities)
file_out.write("Quadrupoles\n" + Quads)
file_out.write("Correctors\n" + Correctors)
file_out.write("BPMs\n" + BPMs)
file_out.close()
