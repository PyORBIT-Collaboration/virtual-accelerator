# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import os
import time
import argparse
from pathlib import Path

from virtaccl.PyORBIT_Model.pyorbit_child_nodes import BPMclass, WSclass, ScreenClass
from virtaccl.ca_server import Server, epics_now, not_ctrlc
from virtaccl.site.SNS_Linac.virtual_devices import (Quadrupole, Corrector, Quadrupole_Power_Supply,
                                                     Corrector_Power_Supply, WireScanner, BPM, P_BPM, Screen)
from virtaccl.site.SNS_Linac.virtual_devices_SNS import SNS_Dummy_BCM, SNS_Dummy_ICS

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel
from virtaccl.virtual_accelerator import va_parser, virtual_accelerator
from virtaccl.beam_line import BeamLine

from virtaccl.site.SNS_IDmp.IDmp_maker import get_IDMP_lattice_and_bunch


def main():
    loc = Path(__file__).parent
    parser, va_version = va_parser()
    parser.description = 'Run the SNS Injection Dump PyORBIT virtual accelerator server. Version ' + va_version

    # Json file that contains a dictionary connecting EPICS name of devices with their associated element model names.
    parser.add_argument('--file', '-f', default=loc / 'va_config.json', type=str,
                        help='Pathname of config json file.')

    # Lattice xml input file and the sequences desired from that file.
    parser.add_argument('--lattice', default=loc / 'orbit_model/sns_linac.xml', type=str,
                        help='Pathname of lattice file')
    parser.add_argument("--start", default="MEBT", type=str,
                        help='Desired sequence of the lattice to start the model with (default=MEBT).')
    parser.add_argument("end", nargs='?', default="HEBT1", type=str,
                        help='Desired sequence of the lattice to end the model with (default=HEBT1).')

    # Desired initial bunch file and the desired number of particles from that file.
    parser.add_argument('--bunch', default=loc / 'orbit_model/MEBT_in.dat', type=str,
                        help='Pathname of input bunch file.')
    parser.add_argument('--particle_number', default=1000, type=int,
                        help='Number of particles to use (default=1000).')
    parser.add_argument('--beam_current', default=38.0, type=float,
                        help='Initial beam current in mA. (default=38.0).')
    parser.add_argument('--save_bunch', const='end_bunch.dat', nargs='?', type=str,
                        help="Saves the bunch at the end of the lattice after each track in the given location. "
                             "If no location is given, the bunch is saved as 'end_bunch.dat' in the working directory. "
                             "(Default is that the bunch is not saved.)")

    # Json file that contains a dictionary connecting EPICS name of devices with their phase offset.
    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of phase offset file.')

    args = parser.parse_args()
    debug = args.debug

    config_file = Path(args.file)
    with open(config_file, "r") as json_file:
        devices_dict = json.load(json_file)

    part_num = args.particle_number
    lattice, bunch = get_IDMP_lattice_and_bunch(part_num, x_off=2, xp_off=0.3)
    model = OrbitModel(input_bunch=bunch, debug=debug)
    model.define_custom_node(BPMclass.node_type, BPMclass.parameter_list, diagnostic=True)
    model.define_custom_node(WSclass.node_type, WSclass.parameter_list, diagnostic=True)
    model.define_custom_node(ScreenClass.node_type, ScreenClass.parameter_list, diagnostic=True)
    model.set_beam_current(38.0e-3)  # Set the initial beam current in Amps.
    model.initialize_lattice(lattice)
    element_list = model.get_element_list()

    beam_line = BeamLine()

    offset_file = args.phase_offset
    if offset_file is not None:
        with open(offset_file, "r") as json_file:
            offset_dict = json.load(json_file)

    quad_ps = devices_dict["Quadrupole_Power_Supply"]
    quads = devices_dict["Quadrupole"]
    for name, device_dict in quads.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = abs(model.get_element_parameters(ele_name)['dB/dr'])
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in quad_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Quadrupole_Power_Supply(ps_name, initial_field)
                beam_line.add_device(ps_device)
                corrector_device = Quadrupole(name, ele_name, power_supply=ps_device, polarity=polarity)
                beam_line.add_device(corrector_device)

    corr_ps = devices_dict["Corrector_Power_Supply"]
    correctors = devices_dict["Corrector"]
    for name, device_dict in correctors.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = model.get_element_parameters(ele_name)['B']
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in corr_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Corrector_Power_Supply(ps_name, initial_field)
                beam_line.add_device(ps_device)
                corrector_device = Corrector(name, ele_name, power_supply=ps_device, polarity=polarity)
                beam_line.add_device(corrector_device)

    wire_scanners = devices_dict["Wire_Scanner"]
    for name, model_name in wire_scanners.items():
        if model_name in element_list:
            ws_device = WireScanner(name, model_name)
            beam_line.add_device(ws_device)

    bpms = devices_dict["BPM"]
    for name, model_name in bpms.items():
        if model_name in element_list:
            phase_offset = 0
            if offset_file is not None:
                phase_offset = offset_dict[name]
            bpm_device = BPM(name, model_name, phase_offset=phase_offset)
            beam_line.add_device(bpm_device)

    screen = devices_dict["Screen"]
    for name, model_name in screen.items():
        if model_name in element_list:
            screen_device = Screen(name, model_name)
            beam_line.add_device(screen_device)

    pbpms = devices_dict["Physics_BPM"]
    for name, model_name in pbpms.items():
        if model_name in element_list:
            pbpm_device = P_BPM(name, model_name)
            beam_line.add_device(pbpm_device)

    dummy_device = SNS_Dummy_BCM("Ring_Diag:BCM_D09", 'HEBT_Diag:BPM11')
    beam_line.add_device(dummy_device)
    dummy_device = SNS_Dummy_ICS("ICS_Tim")
    beam_line.add_device(dummy_device)

    server = Server()

    virtual_accelerator(model, beam_line, server, parser)

    print('Exiting. Thank you for using our virtual accelerator!')


if __name__ == '__main__':
    main()
