# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import time
import argparse

from orbit.core.bunch import Bunch
from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from ca_server import Server, epics_now, not_ctrlc
from virtual_devices import Cavity, BPM, Quadrupole, Corrector, PBPM, WireScanner

from pyorbit_server_interface import OrbitModel

# update rate in Hz
REP_RATE = 1.0

if __name__ == '__main__':
    # Set a default prefix if unspecified at server initialization
    parser = argparse.ArgumentParser(description='Run CA server')
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of pv file. Relative to Server/')

    args = parser.parse_args()
    # prefix = args.prefix + ':'
    # print(f'Using prefix: {args.prefix}.')

    lattice_file = 'sns_linac.xml'
    subsections = ['SCLMed', 'SCLHigh', 'HEBT1']
    sns_linac_factory = SNS_LinacLatticeFactory()
    sns_linac_factory.setMaxDriftLength(0.01)
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)
    Add_quad_apertures_to_lattice(model_lattice)
    Add_rfgap_apertures_to_lattice(model_lattice)

    bunch_in = Bunch()
    bunch_in.readBunch('SCL_in.dat')
    for n in range(bunch_in.getSizeGlobal()):
        if n + 1 > 1000:
            bunch_in.deleteParticleFast(n)
    bunch_in.compress()

    model = OrbitModel(model_lattice, bunch_in)

    # server = Server(prefix)
    server = Server()

    with open(args.file, "r") as json_file:
        devices_dict = json.load(json_file)

    with open('va_offsets.json', "r") as json_file:
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

    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()
        server.update()

        now = epics_now()

        new_params = server.get_settings()
        server.update_readbacks()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.update_measurements(new_measurements)

        loop_time_taken = time.time() - loop_start_time
        sleep_time = max(0.0, REP_RATE - loop_time_taken)
        time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')
