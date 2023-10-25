# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
from pathlib import Path
from time import sleep
import argparse

sys.path.append('../../../SNS_CA_Server/caserver')
from castst import Server, epics_now, not_ctrlc, Device
from devices import BLM, BCM, BPM, Magnet, Cavity, PBPM, genPV

from pyorbit_server_interface import OrbitModel

# update rate in Hz
REP_RATE = 5.0

if __name__ == '__main__':
    # Set a default prefix if unspecified at server initialization
    parser = argparse.ArgumentParser(description='Run CA server')
    parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of pv file. Relative to Server/')

    args = parser.parse_args()
    prefix = args.prefix + ':'
    print(f'Using prefix: {args.prefix}.')

    with open(args.file, "r") as json_file:
        input_dicts = json.load(json_file)

    lattice = input_dicts['Pyorbit_Lattice']
    devices_dict = input_dicts['Devices']

    lattice_file = Path(lattice['file_name'])
    subsections = lattice['subsections']
    model = OrbitModel(lattice_file, subsections)

    server = Server(prefix)

    for device_type, device_dict in devices_dict.items():
        params_dict = device_dict['parameters']
        devices = device_dict['devices']
        for device_name, pyorbit_name in devices.items():
            server_device = Device(device_name)
            for pv_param_name, pv_info in params_dict.items():
                pv_name = device_name + ':' + pv_param_name
                pv_type = pv_info['pv_type']
                model.add_pv(pv_name, pv_type, pyorbit_name, pv_info['parameter_key'])
                if pv_type == 'setting':
                    initial_value = model.get_settings(pv_name)[pv_name]
                    server_device.register_setting(pv_param_name, {'prec': 4}, initial_value)
                else:
                    server_device.register_measurement(pv_param_name, {'prec': 4})
            server.add_device(server_device)

    model.order_pvs()

    bunch_file = Path('../SCL_Wizard/SCL_in.dat')
    model.load_initial_bunch(bunch_file, number_of_particls=1000)

    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        now = epics_now()

        new_params = server.get_params()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.set_params(new_measurements)

        server.update()
        sleep(1.0 / REP_RATE)

    print('Exiting. Thank you for using our epics server!')
