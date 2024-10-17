# This script runs through how to build a lattice, build a bunch, and how to track it.
import math
from orbit.bunch_generators import TwissContainer, WaterBagDist3D

# Import Bunch to be able to build a bunch.
from orbit.core.bunch import Bunch

# Import LinacAccLattice to build a lattice and Sequence to build a sequence that we can then import into the lattice.
from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice, Sequence

# Import Quad and Drift components to build the lattice.
from orbit.py_linac.lattice.LinacAccNodes import Quad, Drift, DCorrectorH, DCorrectorV


from virtaccl.PyORBIT_Model.pyorbit_child_nodes import BPMclass, WSclass, ScreenClass
from virtaccl.PyORBIT_Model.bunch_generator import BunchGenerator


def get_IDMP_lattice_and_bunch(particle_number=1000, x_off=0, xp_off=0, y_off=0, yp_off=0, debug: bool = False):
    # Field strength and length of the quadrupoles
    quad_field = 0.5
    dch_field = 0.01
    dcv_field = -0.02
    mag_len = 0.673
    bpm_frequency = 402.5e6

    # List to contain the drift and quadrupole nodes.
    list_of_nodes = []

    BPM00 = BPMclass("BPM00", frequency=bpm_frequency)
    list_of_nodes.append(BPM00)

    D1 = Drift("Drift1")
    D1.setLength((10.029 - mag_len / 2) - 6.48)
    list_of_nodes.append(D1)

    Q1 = Quad("Quad1")
    Q1.setLength(mag_len)
    Q1.setField(-quad_field)

    DCH1 = DCorrectorH("HCorrector1")
    DCH1.setParam("effLength", mag_len)
    DCH1.setField(dch_field)
    Q1.addChildNode(DCH1, Q1.EXIT)

    DCV1 = DCorrectorV("VCorrector1")
    DCV1.setParam("effLength", mag_len)
    DCV1.setField(dcv_field)
    Q1.addChildNode(DCV1, Q1.EXIT)

    BPM01 = BPMclass("BPM01", frequency=bpm_frequency)
    Q1.addChildNode(BPM01, Q1.EXIT)

    list_of_nodes.append(Q1)

    D2 = Drift("Drift2")
    D2.setLength((13.599 - mag_len / 2) - (10.029 + mag_len / 2))
    list_of_nodes.append(D2)

    Q2 = Quad("Quad2")
    Q2.setLength(mag_len)
    Q2.setField(quad_field)

    DCH2 = DCorrectorH("HCorrector2")
    DCH2.setParam("effLength", mag_len)
    DCH2.setField(-dch_field)
    Q2.addChildNode(DCH2, Q2.EXIT)

    DCV2 = DCorrectorV("VCorrector2")
    DCV2.setParam("effLength", mag_len)
    DCV2.setField(-dcv_field)
    Q2.addChildNode(DCV2, Q2.EXIT)

    BPM02 = BPMclass("BPM02", frequency=bpm_frequency)
    Q2.addChildNode(BPM02, Q2.EXIT)

    list_of_nodes.append(Q2)

    D3 = Drift("Drift3")
    D3.setLength(16.612 - (13.59872 + mag_len / 2))
    list_of_nodes.append(D3)

    WS01 = WSclass("WS01")
    list_of_nodes.append(WS01)

    D4 = Drift("Drift4")
    D4.setLength(17.380 - 16.612)
    list_of_nodes.append(D4)

    BPM03 = BPMclass("BPM03", frequency=bpm_frequency)
    list_of_nodes.append(BPM03)

    D5 = Drift("Drift5")
    D5.setLength(12.998)
    list_of_nodes.append(D5)

    Screen = ScreenClass("Screen")
    list_of_nodes.append(Screen)

    # Dump

    # Define the sequence and add the list of nodes to the sequence.
    idmp = Sequence('IDmp')
    idmp.setNodes(list_of_nodes)

    # Define the lattice, add the list of nodes to the lattice, and initialize the lattice.
    my_lattice = LinacAccLattice('My Lattice')
    my_lattice.setNodes(list_of_nodes)
    my_lattice.initialize()
    if debug:
        print("Total length=", my_lattice.getLength())

    # -----TWISS Parameters at the entrance of MEBT ---------------
    # transverse emittances are unnormalized and in pi*mm*mrad
    # longitudinal emittance is in pi*eV*sec
    e_kin_ini = 1.349648024  # in [GeV]
    mass = 0.939294  # in [GeV]
    gamma = (mass + e_kin_ini) / mass
    beta = math.sqrt(gamma * gamma - 1.0) / gamma
    if debug:
        print("relat. gamma=", gamma)
        print("relat.  beta=", beta)
    frequency = 402.5e6
    v_light = 2.99792458e8  # in [m/sec]

    # ------ emittances are normalized - transverse by gamma*beta and long. by gamma**3*beta
    (alphaX, betaX, emittX) = (0.3777, 7.5421, 0.4249)
    (alphaY, betaY, emittY) = (-0.7225, 9.1459, 0.3691)
    (alphaZ, betaZ, emittZ) = (-17.0460, 179.6212, 1.1498)

    alphaZ = -alphaZ

    # ---make emittances un-normalized XAL units [m*rad]
    emittX = 1.0e-6 * emittX / (gamma * beta)
    emittY = 1.0e-6 * emittY / (gamma * beta)
    emittZ = 1.0e-6 * emittZ / (gamma ** 3 * beta)
    # print(" ========= XAL Twiss ===========")
    # print(" aplha beta emitt[mm*mrad] X= %6.4f %6.4f %6.4f " % (alphaX, betaX, emittX * 1.0e6))
    # print(" aplha beta emitt[mm*mrad] Y= %6.4f %6.4f %6.4f " % (alphaY, betaY, emittY * 1.0e6))
    # print(" aplha beta emitt[mm*mrad] Z= %6.4f %6.4f %6.4f " % (alphaZ, betaZ, emittZ * 1.0e6))

    # ---- long. size in mm
    sizeZ = math.sqrt(emittZ * betaZ) * 1.0e3

    # ---- transform to pyORBIT emittance[GeV*m]
    emittZ = emittZ * gamma ** 3 * beta ** 2 * mass
    betaZ = betaZ / (gamma ** 3 * beta ** 2 * mass)

    if debug:
        print(" ========= PyORBIT Twiss ===========")
        print(" aplha beta emitt[mm*mrad] X= %6.4f %6.4f %6.4f " % (alphaX, betaX, emittX * 1.0e6))
        print(" aplha beta emitt[mm*mrad] Y= %6.4f %6.4f %6.4f " % (alphaY, betaY, emittY * 1.0e6))
        print(" aplha beta emitt[mm*MeV] Z= %6.4f %6.4f %6.4f " % (alphaZ, betaZ, emittZ * 1.0e6))

    twissX = TwissContainer(alphaX, betaX, emittX)
    twissY = TwissContainer(alphaY, betaY, emittY)
    twissZ = TwissContainer(alphaZ, betaZ, emittZ)

    if debug:
        print("Start Bunch Generation.")
    bunch_gen = BunchGenerator(twissX, twissY, twissZ)

    # set the initial kinetic energy in GeV
    bunch_gen.setKinEnergy(e_kin_ini)

    # set the beam peak current in mA
    bunch_gen.setBeamCurrent(38.0)

    bunch_in = bunch_gen.getBunch(nParticles=particle_number, distributorClass=WaterBagDist3D)
    # bunch_in = bunch_gen.getBunch(nParticles = particle_number, distributorClass = GaussDist3D)
    # bunch_in = bunch_gen.getBunch(nParticles = particle_number, distributorClass = KVDist3D)

    bunch_in.charge(+1)
    for n in range(particle_number):
        x, xp, y, yp = bunch_in.x(n), bunch_in.xp(n), bunch_in.y(n), bunch_in.yp(n)
        bunch_in.x(n, x + x_off / 1000)
        bunch_in.xp(n, xp + xp_off / 1000)
        bunch_in.y(n, y + y_off / 1000)
        bunch_in.yp(n, yp + yp_off / 1000)

    return my_lattice, bunch_in
