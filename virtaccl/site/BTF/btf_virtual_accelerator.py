# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import math
import os
import sys
import time
import argparse
from pathlib import Path
from importlib.metadata import version

from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice

from virtaccl.PyORBIT_Model.pyorbit_child_nodes import BPMclass, FCclass, BCMclass
from virtaccl.site.BTF.orbit_model.btf_lattice_factory import PyORBIT_Lattice_Factory

from orbit.core.bunch import Bunch
from orbit.core.linac import BaseRfGap

from virtaccl.ca_server import Server
from virtaccl.beam_line import BeamLine
from virtaccl.site.SNS_Linac.virtual_devices import BPM, Quadrupole, P_BPM, Quadrupole_Power_Supply, Bend_Power_Supply, Bend
from virtaccl.site.BTF.orbit_model.virtual_devices_BTF import BTF_FC, BTF_Quadrupole, BTF_Quadrupole_Power_Supply, BTF_BCM, BTF_Actuator, BTF_Corrector, BTF_Corrector_Power_Supply
from virtaccl.site.BTF.orbit_model.btf_child_nodes import BTF_Screenclass, BTF_Slitclass

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel
from virtaccl.virtual_accelerator import va_parser, virtual_accelerator

def load_config(filename: Path):
    with open(filename, "r") as json_file:
        devices_dict = json.load(json_file)


def main():
    loc = Path(__file__).parent
    parser, va_version = va_parser()
    parser.description = 'Run the SNS Linac PyORBIT virtual accelerator server. Version ' + va_version

    # Json file that contains a dictionary connecting EPICS name of devices with their associated element model names.
    parser.add_argument('--file', '-f', default=loc / 'btf_config.json', type=str,
                        help='Pathname of config json file.')

    # Lattice xml input file and the sequences desired from that file.
    parser.add_argument('--lattice', default=loc / 'orbit_model/btf_lattice_straight.xml', type=str,
                        help='Pathname of lattice file')
    parser.add_argument("--start", default="MEBT1", type=str,
                        help='Desired sequence of the lattice to start the model with (default=MEBT1).')
    parser.add_argument("end", nargs='?', default="MEBT2", type=str,
                        help='Desired sequence of the lattice to end the model with (default=MEBT2).')

    # Desired initial bunch file and the desired number of particles from that file.
    parser.add_argument('--bunch', default=loc / 'orbit_model/parmteq_bunch_RFQ_output_1.00e+05.dat', type=str,
                        help='Pathname of input bunch file.')
    parser.add_argument('--particle_number', default=1000, type=int,
                        help='Number of particles to use (default=1000).')
    parser.add_argument('--beam_current', default=30.0, type=float,
                        help='Initial beam current in mA. (default=30.0).')
    parser.add_argument('--save_bunch', const='end_bunch.dat', nargs='?', type=str,
                        help="Saves the bunch at the end of the lattice after each track in the given location. "
                             "If no location is given, the bunch is saved as 'end_bunch.dat' in the working directory. "
                             "(Default is that the bunch is not saved.)")

    # Json file that contains a dictionary connecting EPICS name of devices with their phase offset.
    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of phase offset file.')

    args = parser.parse_args()
    debug = args.debug
    save_bunch = args.save_bunch

    config_file = Path(args.file)
    with open(config_file, "r") as json_file:
        devices_dict = json.load(json_file)

    lattice_file = args.lattice
    linac_sequence = ["MEBT1"]
    bend_1_sequence = ["STUB"]
    bend_2_sequence = ["MEBT2"]
    start_sequence = args.start
    end_sequence = args.end
    model_sequences = []

    if start_sequence in linac_sequence:
        start_ind = linac_sequence.index(start_sequence)
        if end_sequence in linac_sequence:
            model_sequences += linac_sequence
        else:
            model_sequences += linac_sequence
            if end_sequence in bend_1_sequence:
                model_sequences += bend_1_sequence
            elif end_sequence in bend_2_sequence:
                model_sequences += bend_2_sequence
            else:
                print("End sequence not found in BTF lattice.")
                sys.exit()
    elif start_sequence in bend_1_sequence:
        model_sequences += bend_1_sequence
    elif start_sequence in bend_2_sequence:
        model_sequences += bend_2_sequence
    else:
        print("Start sequence no found in SNS lattice.")
    if not model_sequences:
        print("Bad sequence designations.")
        sys.exit()
    print(model_sequences)

    lattice_factory = PyORBIT_Lattice_Factory()
    lattice_factory.setMaxDriftLength(0.01)
    model_lattice = lattice_factory.getLinacAccLattice(model_sequences, lattice_file)
    cppGapModel = BaseRfGap
    rf_gaps = model_lattice.getRF_Gaps()
    for rf_gap in rf_gaps:
        rf_gap.setCppGapModel(cppGapModel())
    Add_quad_apertures_to_lattice(model_lattice)
    Add_rfgap_apertures_to_lattice(model_lattice)


    bunch_file = Path(args.bunch)
    part_num = args.particle_number

    bunch_in = Bunch()
    bunch_in.readBunch(str(bunch_file))
    bunch_orig_num = bunch_in.getSizeGlobal()
    if bunch_orig_num < part_num:
        print('Bunch file contains less particles than the desired number of particles.')
    elif part_num <= 0:
        bunch_in.deleteAllParticles()
    else:
        bunch_macrosize = bunch_in.macroSize()
        bunch_macrosize *= bunch_orig_num / part_num
        bunch_in.macroSize(bunch_macrosize)
        for n in range(bunch_orig_num):
            if n + 1 > part_num:
                bunch_in.deleteParticleFast(n)
        bunch_in.compress()

    # get sync particle momentum for use in corrector current conversion
    syncPart = bunch_in.getSyncParticle()
    momentum = syncPart.momentum()
    beam_current = args.beam_current / 1000 # Set the initial beam current in Amps

    model = OrbitModel(debug=debug, save_bunch=save_bunch)
    model.define_custom_node(BPMclass.node_type, BPMclass.parameter_list, diagnostic=True)
    model.define_custom_node(FCclass.node_type, FCclass.parameter_list, optic=True, diagnostic=True)
    model.define_custom_node(BTF_Screenclass.node_type, BTF_Screenclass.parameter_list, optic=True)
    model.define_custom_node(BTF_Slitclass.node_type, BTF_Slitclass.parameter_list, optic=True)
    model.define_custom_node(BCMclass.node_type, BCMclass.parameter_list, diagnostic=True)
    model.define_custom_node("markerLinacNode")
    model.initialize_lattice(model_lattice)
    model.set_initial_bunch(bunch_in, beam_current)
    element_list = model.get_element_list()

    server = Server()
    beam_line = BeamLine(server)

    offset_file = args.phase_offset
    if offset_file is not None:
        with open(offset_file, "r") as json_file:
            offset_dict = json.load(json_file)

    quad_ps = devices_dict["Quadrupole_Power_Supply"]
    quads = devices_dict["Quadrupole"]
    for name, device_dict in quads.items():
        ele_name = device_dict["PyORBIT_Name"]
        initial_current = device_dict["Current"]
        coeff_a = device_dict["coeff_a"]
        coeff_b = device_dict["coeff_b"]
        if ele_name in element_list:
            length = model.get_element_dictionary()[ele_name].get_element().getLength()
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in quad_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = BTF_Quadrupole_Power_Supply(ps_name, initial_current)
                beam_line.add_device(ps_device)
                quadrupole_device = BTF_Quadrupole(name, ele_name, power_supply=ps_device, coeff_a = coeff_a, coeff_b = coeff_b, length=length)
                beam_line.add_device(quadrupole_device)

    fq_quad_ps = devices_dict["FQ_Quadrupole_Power_Supply"]
    fq_quads = devices_dict["FQ_Quadrupole"]
    for name, device_dict in fq_quads.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = abs(model.get_element_parameters(ele_name)['dB/dr'])
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in fq_quad_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Quadrupole_Power_Supply(ps_name, initial_field)
                beam_line.add_device(ps_device)
                quadrupole_device = Quadrupole(name, ele_name, power_supply=ps_device, polarity=polarity)
                beam_line.add_device(quadrupole_device)

    corr_ps = devices_dict["Corrector_Power_Supply"]
    corrs = devices_dict["Corrector"]
    for name, device_dict in corrs.items():
        ele_name = device_dict["PyORBIT_Name"]
        quad_name = device_dict["Quad_Name"]
        corr_current = device_dict["Current"]
        coeff = device_dict["coeff"]
        if ele_name in element_list:
            length = model.get_element_dictionary()[quad_name].get_element().getLength()
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in corr_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = BTF_Corrector_Power_Supply(ps_name, corr_current)
                beam_line.add_device(ps_device)
                corrector_device = BTF_Corrector(name, ele_name, power_supply = ps_device, coeff = coeff, length=length, momentum = momentum)
                beam_line.add_device(corrector_device)

    bends = devices_dict["Bend"]
    for name, device_dict in bends.items():
        ele_name = device_dict["PyORBIT_Name"]
        if ele_name in element_list:
            initial_field = 0
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in devices_dict["Bend_Power_Supply"]:
                ps_name = device_dict["Power_Supply"]
                ps_device = Bend_Power_Supply(ps_name, initial_field)
                beam_line.add_device(ps_device)
                bend_device = Bend(name, ele_name, power_supply=ps_device)
                beam_line.add_device(bend_device)

    fc = devices_dict["FC"]
    for name, device_dict in fc.items():
        ele_name = device_dict["PyORBIT_Name"]
        initial_state = device_dict["State"]
        if ele_name in element_list:
            fc_child = FCclass(ele_name)
            model.add_child_node(ele_name, fc_child)
            fc_device = BTF_FC(name, ele_name, initial_state)
            beam_line.add_device(fc_device)

    bs = devices_dict["BS"]
    for name, device_dict in bs.items():
        ele_name = device_dict["PyORBIT_Name"]
        initial_state = device_dict["State"]
        if ele_name in element_list:
            bs_child = FCclass(ele_name)
            model.add_child_node(ele_name, bs_child)
            bs_device = BTF_FC(name, ele_name, initial_state)
            beam_line.add_device(bs_device)

    bcm = devices_dict["BCM"]
    for name, device_dict in bcm.items():
        ele_name = device_dict["PyORBIT_Name"]
        if ele_name in element_list:
            bcm_child = BCMclass(ele_name)
            model.add_child_node(ele_name, bcm_child)
            bcm_device = BTF_BCM(name, ele_name)
            beam_line.add_device(bcm_device)

    bpms = devices_dict["BPM"]
    for name, device_dict in bpms.items():
        ele_name = device_dict["PyORBIT_Name"]
        if ele_name in element_list:
            freq = device_dict["Frequency"]
            bpm_child = BPMclass(ele_name, freq)
            model.add_child_node(ele_name, bpm_child)
            phase_offset = 0
            if offset_file is not None:
                phase_offset = offset_dict[name]
            bpm_device = BPM(name, ele_name, phase_offset=phase_offset)
            beam_line.add_device(bpm_device)

    screens = devices_dict["Screen"]
    for name, device_dict in screens.items():
        ele_name = device_dict["PyORBIT_Name"]
        axis = device_dict["Axis"]
        axis_polarity = device_dict["Axis_Polarity"]
        if ele_name in element_list:
            screen_child = BTF_Screenclass(ele_name, screen_axis = axis, screen_polarity = axis_polarity)
            model.add_child_node(ele_name, screen_child)
            screen_device = BTF_Actuator(name, ele_name)
            beam_line.add_device(screen_device)

    slits = devices_dict["Slit"]
    for name, device_dict in slits.items():
        ele_name = device_dict["PyORBIT_Name"]
        axis = device_dict["Axis"]
        axis_polarity = device_dict["Axis_Polarity"]
        speed = device_dict["Standard_Speed"]
        limit= device_dict["Actuator_Limit"]
        if ele_name in element_list:
            slit_child = BTF_Slitclass(ele_name, slit_axis = axis, slit_polarity = axis_polarity)
            model.add_child_node(ele_name, slit_child)
            slit_device = BTF_Actuator(name, ele_name, speed = speed, limit = limit)
            beam_line.add_device(slit_device)

    virtual_accelerator(model, beam_line, parser)

if __name__ == '__main__':
    main()



