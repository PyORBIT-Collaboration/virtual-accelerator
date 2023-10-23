# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
from pathlib import Path
from time import sleep
import argparse

sys.path.append('../../../SNS_CA_Server/caserver')
from castst import Server, epics_now, not_ctrlc
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

    lattice = input_dicts['pyorbit_lattice']
    cav_params = input_dicts["cavity_parameters"]
    cavs = input_dicts["cavities"]
    quad_params = input_dicts["quadrupole_parameters"]
    quads = input_dicts["quadrupoles"]
    corr_params = input_dicts["corrector_parameters"]
    corrs = input_dicts["correctors"]
    bpm_params = input_dicts["bpm_parameters"]
    bpms = input_dicts["bpms"]
    pbpm_params = input_dicts["pbpm_parameters"]
    pbpms = input_dicts["pbpms"]

    lattice_file = Path(lattice['file_name'])
    subsections = lattice['subsections']
    model = OrbitModel(lattice_file, subsections)

    server = Server(prefix)
    all_devices = []

    for device_name, pyorbit_name in cavs.items():
        init_values = []
        for pv_param_name, pv_info in cav_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        init_values = [init_values[0], 1.0]
        all_devices.append(server.add_device(Cavity(device_name, *init_values)))

    for device_name, pyorbit_name in quads.items():
        init_values = []
        for pv_param_name, pv_info in quad_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(Magnet(device_name, *init_values)))

    for device_name, pyorbit_name in corrs.items():
        init_values = []
        for pv_param_name, pv_info in corr_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(Magnet(device_name, *init_values)))

    for device_name, pyorbit_name in bpms.items():
        init_values = []
        for pv_param_name, pv_info in bpm_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(BPM(device_name)))

        for device_name, pyorbit_name in pbpms.items():
            init_values = []
            for pv_param_name, pv_info in pbpm_params.items():
                pv_name = device_name + ':' + pv_param_name
                model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
                init_values.append(model.get_measurements(pv_name)[pv_name])
            all_devices.append(server.add_device(PBPM(device_name)))

    model.order_pvs()

    bunch_file = Path('../SCL_Wizard/SCL_in.dat')
    model.load_initial_bunch(bunch_file, number_of_particls=1000)

    server.start()
    print(f"Server started.")
    #print(f"Devices in use: {[p.name for p in all_devices]}")

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
