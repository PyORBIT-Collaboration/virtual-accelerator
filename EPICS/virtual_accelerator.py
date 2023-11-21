# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import math
import sys
import time
from pathlib import Path
import argparse

from orbit.core.bunch import Bunch
from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from ca_server import Server, epics_now, not_ctrlc, Device, AbsNoise, PhaseT, LinearT, PhaseTInv
from virtual_devices import Cavity, BPM, Quadrupole, Corrector, pBPM

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

    with open(args.file, "r") as json_file:
        input_dicts = json.load(json_file)

    lattice = input_dicts['Pyorbit_Lattice']
    devices_dict = input_dicts['Devices']

    lattice_file = Path(lattice['file_name'])
    subsections = lattice['subsections']
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

    for device_type, device_dict in devices_dict.items():
        params_dict = device_dict['parameters']
        devices = device_dict['devices']
        if device_type == "Cavities":
            for pv_name, device_info in devices.items():
                pyorbit_name = device_info['pyorbit_name']
                initial_settings = model.get_settings(pyorbit_name)[pyorbit_name]
                rf_device = Cavity(pv_name, pyorbit_name, initial_settings)
                server.add_device(rf_device)

        if device_type == "Quadrupoles":
            for pv_name, device_info in devices.items():
                pyorbit_name = device_info['pyorbit_name']
                initial_settings = model.get_settings(pyorbit_name)[pyorbit_name]
                quad_device = Quadrupole(pv_name, pyorbit_name, initial_settings)
                server.add_device(quad_device)

        if device_type == "Correctors":
            for pv_name, device_info in devices.items():
                pyorbit_name = device_info['pyorbit_name']
                initial_settings = model.get_settings(pyorbit_name)[pyorbit_name]
                corrector_device = Corrector(pv_name, pyorbit_name, initial_settings)
                server.add_device(corrector_device)

        if device_type == "BPMs":
            for pv_name, device_info in devices.items():
                pyorbit_name = device_info['pyorbit_name']
                bpm_device = BPM(pv_name, pyorbit_name)
                server.add_device(bpm_device)

        if device_type == "PBPMs":
            for pv_name, device_info in devices.items():
                pyorbit_name = device_info['pyorbit_name']
                pbpm_device = pBPM(pv_name, pyorbit_name)
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
