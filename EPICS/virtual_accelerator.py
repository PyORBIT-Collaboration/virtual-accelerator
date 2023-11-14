# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import math
import sys
import time
from pathlib import Path
import argparse

from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from ca_server import Server, epics_now, not_ctrlc, Device, AbsNoise, PhaseT, LinearT, PhaseTInv

from pyorbit_server_interface import OrbitModel

# update rate in Hz
REP_RATE = 1.0

if __name__ == '__main__':
    # Set a default prefix if unspecified at server initialization
    parser = argparse.ArgumentParser(description='Run CA server')
    #parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')
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

    model = OrbitModel(model_lattice)

    # server = Server(prefix)
    server = Server()

    for device_type, device_dict in devices_dict.items():
        params_dict = device_dict['parameters']
        devices = device_dict['devices']
        for device_name, device_info in devices.items():
            pyorbit_name = device_info['pyorbit_name']
            server_device = Device(device_name)
            for pv_param_name, pv_info in params_dict.items():
                pv_name = device_name + ':' + pv_param_name
                pv_type = pv_info['pv_type']
                model.add_pv(pv_name, pv_type, pyorbit_name, pv_info['parameter_key'])

                if 'noise' in pv_info:
                    noise = AbsNoise(noise=pv_info['noise'])
                else:
                    noise = None

                if 'phase_off_set' in pv_info:
                    off_set = PhaseTInv(offset=pv_info['phase_offset'], scaler=180/math.pi)
                elif 'linear_offset' in pv_info:
                    off_set = LinearT(scaler=pv_info['linear_offset'])
                else:
                    off_set = None

                if 'override' in device_info and pv_param_name in device_info['override']:
                    for or_param, or_value in device_info['override'][pv_param_name].items():
                        if or_param == 'phase_offset':
                            off_set = PhaseTInv(offset=or_value, scaler=180/math.pi)
                        elif or_param == 'linear_offset':
                            off_set = LinearT(scaler=or_value)

                if pv_type == 'setting':
                    initial_value = model.get_settings(pv_name)[pv_name]
                    if off_set is not None:
                        initial_value = off_set.raw(initial_value)
                    server_device.register_setting(pv_param_name, {'prec': 4}, initial_value,
                                                   transform=off_set)

                elif pv_type == 'diagnostic' or pv_type == 'readback' or pv_type == 'physics':
                    server_device.register_measurement(pv_param_name, {'prec': 4},
                                                       noise=noise, transform=off_set)

                server.add_device(server_device)

    model.order_pvs()

    bunch_file = Path('../SCL_Wizard/SCL_in.dat')
    model.load_initial_bunch(bunch_file, number_of_particles=1000)

    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()
        server.update()

        now = epics_now()

        new_params = server.get_settings()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.update_measurements(new_measurements)

        loop_time_taken = time.time() - loop_start_time
        sleep_time = max(0.0, REP_RATE - loop_time_taken)
        time.sleep(sleep_time)

    print('Exiting. Thank you for using our epics server!')
