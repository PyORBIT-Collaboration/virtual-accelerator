# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
from pathlib import Path
from time import sleep
from castst import Server, epics_now, not_ctrlc
import argparse
from devices import BLM, BCM, BPM, Magnet, Cavity, genPV

from pyorbit_server_interface import OrbitModel

# update rate in Hz
REP_RATE = 5.0

# A function to parse BLMs and attributes from file
# Returns a list of lines (split into sublists)

# def read_file(file):
#    with open(file, "r") as f:
#        file = f.read().splitlines()
#        # filter out comments while reading the file
#        parameters = [i.split() for i in file if not i.strip().startswith('#')]
#        return parameters


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

    lattice_file = Path(lattice['file_name'])
    subsections = lattice['subsections']
    model = OrbitModel(lattice_file, subsections)

    server = Server(prefix)
    all_devices = []
    device_types = {'Cavity', 'Magnet', 'BLM', 'BCM', 'BPM', 'genPV'}

    for device_name, pyorbit_name in cavs.items():
        init_values = []
        for pv_param_name, pv_info in cav_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        print(init_values)
        all_devices.append(server.add_device(Cavity(device_name, *init_values)))

    for device_name, pyorbit_name in quads.items():
        init_values = []
        for pv_param_name, pv_info in quad_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(Cavity(device_name, *init_values)))

    for device_name, pyorbit_name in corrs.items():
        init_values = []
        for pv_param_name, pv_info in corr_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(Cavity(device_name, *init_values)))

    for device_name, pyorbit_name in bpms.items():
        init_values = []
        for pv_param_name, pv_info in bpm_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
            init_values.append(model.get_measurements(pv_name)[pv_name])
        all_devices.append(server.add_device(Cavity(device_name, *init_values)))

    model.order_pvs()

    print(model.pv_dict.get_pvs())

    sys.exit()

    server = Server(prefix)
    all_devices = []

    # Dynamically create device objects and add them to the server. Append to list for iterability
    device_types = {'Cavity', 'Magnet', 'BLM', 'BCM', 'BPM', 'genPV'}
    print("Devices in use:")
    for parameters in mixed_devices:
        all_devices.append(server.add_device(globals()[parameters[0]](*parameters[1:])))

    server.start()
    print(f"Server started. \n"
          f"{server}")
    # Now that our server is started, we can initialize our problem space with given i.c.
    # Is there a way to abstract this into the Device class somehow? Or automatic upon creation?

    sys.exit()

    for d in all_devices:
        d.initialize()

    blms = [item for item in all_devices if type(item).__name__ == 'BLM']
    cavs = [item for item in all_devices if type(item).__name__ == 'Cavity']
    all_devices = list(set(all_devices) - set(blms) - set(cavs))

    # Our new data acquisition routine
    while not_ctrlc():
        now = epics_now()
        phases_buffer = []
        for c in cavs:
            phases_buffer.append(c.update_value())
        for d in all_devices:
            d.update_value()
        for b in blms:
            # BLM data is synchronized by forcing a timestamp
            # Loss signal is only impacted by first two CCL phases, but pass them all to be generic
            # Can modify formula to have other dependencies
            b.calc_loss(*phases_buffer, ts=now)

        server.update()
        sleep(1.0 / REP_RATE)

    print('Exiting. Thank you for using our epics server!')
