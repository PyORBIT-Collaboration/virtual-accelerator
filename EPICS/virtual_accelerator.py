# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import time
import argparse
from pathlib import Path

from orbit.core.bunch import Bunch
from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from ca_server import Server, epics_now, not_ctrlc
from virtual_devices import Cavity, BPM, Quadrupole, Corrector, PBPM, WireScanner

from pyorbit_server_interface import OrbitModel

# update rate in Hz
REP_RATE = 0.5

if __name__ == '__main__':
    # Set a default prefix if unspecified at server initialization
    parser = argparse.ArgumentParser(description='Run CA server')
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of config json file.')
    parser.add_argument('--bunch', default='bunch_in.dat', type=str,
                        help='Pathname of input bunch file.')
    parser.add_argument('--debug', dest='debug', action='store_true', help="Some debug info will be printed.")
    parser.add_argument('--production', dest='debug', action='store_false',
                        help="DEFAULT: No additional info printed.")

    parser.add_argument("Sequences", nargs='*', help='Sequences', default=['SCLMed', 'SCLHigh', 'HEBT1'])

    args = parser.parse_args()
    debug = args.debug
    bunch_file = Path(args.bunch)
    config_file = Path(args.file)
    config_name = config_file.name.split('.')[0]
    offset_name = config_name[0:-7] + '_offsets.json' if config_name.endswith('_config') else config_name + '_offset.json'
    offset_file = config_file.parent / offset_name
    lattice_file = 'sns_linac.xml'
    subsections = args.Sequences

    sns_linac_factory = SNS_LinacLatticeFactory()
    sns_linac_factory.setMaxDriftLength(0.01)
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)
    Add_quad_apertures_to_lattice(model_lattice)
    Add_rfgap_apertures_to_lattice(model_lattice)

    bunch_in = Bunch()
    bunch_in.readBunch(str(bunch_file))
    for n in range(bunch_in.getSizeGlobal()):
        if n + 1 > 1000:
            bunch_in.deleteParticleFast(n)
    bunch_in.compress()

    model = OrbitModel(model_lattice, bunch_in)

    # server = Server(prefix)
    server = Server()

    with open(config_file, "r") as json_file:
        devices_dict = json.load(json_file)

    with open(offset_file, "r") as json_file:
        offset_dict = json.load(json_file)

    for device_type, devices in devices_dict.items():
        if device_type == "Cavities":
            for name, model_name in devices.items():
                initial_settings = model.get_settings(model_name)[model_name]
                phase_offset = offset_dict[name]
                rf_device = Cavity(name, model_name, initial_settings, phase_offset)
                server.add_device(rf_device)

        if device_type == "Quadrupoles":
            for name, model_name in devices.items():
                initial_settings = model.get_settings(model_name)[model_name]
                quad_device = Quadrupole(name, model_name, initial_settings)
                server.add_device(quad_device)

        if device_type == "Correctors":
            for name, model_name in devices.items():
                initial_settings = model.get_settings(model_name)[model_name]
                corrector_device = Corrector(name, model_name, initial_settings)
                server.add_device(corrector_device)

        if device_type == "Wire_Scanners":
            for name, model_name in devices.items():
                ws_device = WireScanner(name, model_name)
                server.add_device(ws_device)

        if device_type == "BPMs":
            for name, model_name in devices.items():
                phase_offset = offset_dict[name]
                bpm_device = BPM(name, model_name, phase_offset)
                server.add_device(bpm_device)

        if device_type == "PBPMs":
            for name, model_name in devices.items():
                pbpm_device = PBPM(name, model_name)
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
        sleep_time = max(0.0, REP_RATE - loop_time_taken)
        time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')
