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

from sns_linac_bunch_generator import SNS_Linac_BunchGenerator

random.seed(100)

bunch_file = "in.dat"
bunch_out = "DTL1-MEBT_in.dat"

names_tot = ["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4", "SCLMed", "SCLHigh"]#, "HEBT1", "HEBT2"]
names_preSCL = ["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4"]
names_SCL = ["SCLMed", "SCLHigh"]
# ---- create the factory instance
sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)

# ---- the XML file name with the structure
xml_file_name = "sns_linac.xml"

# ---- make lattice from XML file
accLattice_tot = sns_linac_factory.getLinacAccLattice(names_tot, xml_file_name)
accLattice_preSCL = sns_linac_factory.getLinacAccLattice(names_preSCL, xml_file_name)
accLattice_SCL = sns_linac_factory.getLinacAccLattice(names_SCL, xml_file_name)

print("Linac lattice is ready.")

bunch_in_tot = Bunch()
bunch_in_tot.readBunch(bunch_file)
bunch_in_SCL = Bunch()
bunch_in_SCL.readBunch(bunch_file)

print("Bunch Generation completed.")
print(bunch_in_tot.getSyncParticle().time(), bunch_in_tot.getSyncParticle().beta())

# set up design
accLattice_tot.trackDesignBunch(bunch_in_tot)
accLattice_tot.trackBunch(bunch_in_tot)
print(bunch_in_tot.getSyncParticle().time(), bunch_in_tot.getSyncParticle().beta())
bunch_in_tot.dumpBunch("bunch_tot.dat")

print(bunch_in_SCL.getSyncParticle().time(), bunch_in_SCL.getSyncParticle().beta())

accLattice_preSCL.trackDesignBunch(bunch_in_SCL)
accLattice_preSCL.trackBunch(bunch_in_SCL)

bunch_in_SCL.dumpBunch("bunch_in_SCL.dat")

print(bunch_in_SCL.getSyncParticle().time(), bunch_in_SCL.getSyncParticle().beta())

bunch_test = Bunch()
bunch_test.readBunch("bunch_in_SCL.dat")
bunch_test.dumpBunch("bunch_test.dat")

bunch_test.getSyncParticle().time(0.0)
accLattice_SCL.trackDesignBunch(bunch_test)
accLattice_SCL.trackBunch(bunch_test)

print(bunch_test.getSyncParticle().time(), bunch_test.getSyncParticle().beta())
bunch_test.dumpBunch("bunch_test2.dat")



print("Design tracking completed.")