# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
import time
import argparse
from pathlib import Path

from orbit.core.bunch import Bunch
from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from ca_server import Server, epics_now, not_ctrlc
from virtual_devices import Cavity, BPM, Quadrupole, Corrector, P_BPM, WireScanner

from pyorbit_server_interface import OrbitModel


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run CA server')
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')

    # Json file that contains a dictionary connecting EPICS name of devices with their associated element model names.
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of config json file.')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates.')

    # Lattice xml input file and the sequences desired from that file.
    parser.add_argument('--lattice', default='sns_linac.xml', type=str,
                        help='Pathname of lattice file')
    parser.add_argument("--sequences", nargs='*',
                        help='Desired sections from lattice listed in order without commas',
                        default=["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4",
                                 "SCLMed", "SCLHigh", "HEBT1"])

    # Desired initial bunch file and the desired number of particles from that file.
    parser.add_argument('--bunch', default='MEBT_in.dat', type=str,
                        help='Pathname of input bunch file.')
    parser.add_argument('--particle_number', default=1000, type=int,
                        help='Number of particles to use.')

    # Json file that contains a dictionary connecting EPICS name of devices with their phase offset.
    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of phase offset file.')

    # Desired amount of output.
    parser.add_argument('--debug', dest='debug', action='store_true', help="Some debug info will be printed.")
    parser.add_argument('--production', dest='debug', action='store_false',
                        help="DEFAULT: No additional info printed.")

    args = parser.parse_args()
    debug = args.debug

    config_file = Path(args.file)
    with open(config_file, "r") as json_file:
        devices_dict = json.load(json_file)

    REP_RATE = args.refresh_rate

    lattice_file = args.lattice
    subsections = args.sequences

    sns_linac_factory = SNS_LinacLatticeFactory()
    sns_linac_factory.setMaxDriftLength(0.01)
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)
    Add_quad_apertures_to_lattice(model_lattice)
    Add_rfgap_apertures_to_lattice(model_lattice)

    bunch_file = Path(args.bunch)
    part_num = args.particle_number

    bunch_in = Bunch()
    bunch_in.readBunch(str(bunch_file))
    bunch_orig_num = bunch_in.getSizeGlobal()
    if bunch_orig_num < part_num:
        print('Bunch file contains less particles than the desired number of particles.')
    else:
        bunch_macrosize = bunch_in.macroSize()
        bunch_macrosize *= bunch_orig_num / part_num
        bunch_in.macroSize(bunch_macrosize)
        for n in range(bunch_orig_num):
            if n + 1 > part_num:
                bunch_in.deleteParticleFast(n)
        bunch_in.compress()

    model = OrbitModel(model_lattice, bunch_in)
    element_list = model.get_element_list()

    server = Server()

    offset_file = args.phase_offset
    if offset_file is not None:
        with open(offset_file, "r") as json_file:
            offset_dict = json.load(json_file)

    for device_type, devices in devices_dict.items():
        for name, model_name in devices.items():
            if model_name in element_list:
                if device_type == "RF_Cavity":
                    initial_settings = model.get_settings(model_name)[model_name]
                    phase_offset = 0
                    if offset_file is not None:
                        phase_offset = offset_dict[name]
                    rf_device = Cavity(name, model_name, initial_dict=initial_settings, phase_offset=phase_offset)
                    server.add_device(rf_device)

                if device_type == "Quadrupole":
                    initial_settings = model.get_settings(model_name)[model_name]
                    quad_device = Quadrupole(name, model_name, initial_dict=initial_settings)
                    server.add_device(quad_device)

                if device_type == "Corrector":
                    initial_settings = model.get_settings(model_name)[model_name]
                    corrector_device = Corrector(name, model_name, initial_dict=initial_settings)
                    server.add_device(corrector_device)

                if device_type == "Wire_Scanner":
                    ws_device = WireScanner(name, model_name)
                    server.add_device(ws_device)

                if device_type == "BPMs":
                    phase_offset = 0
                    if offset_file is not None:
                        phase_offset = offset_dict[name]
                    bpm_device = BPM(name, model_name, phase_offset=phase_offset)
                    server.add_device(bpm_device)

                if device_type == "Physics_BPM":
                    pbpm_device = P_BPM(name, model_name)
                    server.add_device(pbpm_device)

    if debug:
        print(server)
    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()

        now = epics_now()

        new_params = server.get_settings()
        server.update_readbacks()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.update_measurements(new_measurements)

        server.update()

        loop_time_taken = time.time() - loop_start_time
        sleep_time = REP_RATE - loop_time_taken
        if sleep_time < 0.0:
            print('Warning: Update took longer than refresh rate.')
        else:
            time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')
