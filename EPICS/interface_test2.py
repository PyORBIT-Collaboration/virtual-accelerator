import sys
import time
from pathlib import Path
from pyorbit_server_interface import OrbitModel

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
    #all_devices.append(server.add_device(Cavity(device_name, *init_values)))

for device_name, pyorbit_name in quads.items():
    init_values = []
    for pv_param_name, pv_info in quad_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
        init_values.append(model.get_measurements(pv_name)[pv_name])
    #all_devices.append(server.add_device(Cavity(device_name, *init_values)))

for device_name, pyorbit_name in corrs.items():
    init_values = []
    for pv_param_name, pv_info in corr_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
        init_values.append(model.get_measurements(pv_name)[pv_name])
    #all_devices.append(server.add_device(Cavity(device_name, *init_values)))

for device_name, pyorbit_name in bpms.items():
    init_values = []
    for pv_param_name, pv_info in bpm_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_types'], pyorbit_name, pv_info['parameter_key'])
        init_values.append(model.get_measurements(pv_name)[pv_name])
    #all_devices.append(server.add_device(Cavity(device_name, *init_values)))

model.order_pvs()




"""
print(model.get_settings("SCL_Mag:DCH00:B"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))

dict1 = {"SCL_Mag:DCH00:B": 0.000001}
model.update_optics(dict1)

print(model.get_settings("SCL_Mag:DCH00:B"))

model.track()

print(model.get_measurements("SCL_Diag:BPM32:xAvg"))

dict1 = {"SCL_Mag:DCH00:B": 0.0}
model.update_optics(dict1)

print(model.get_settings("SCL_Mag:DCH00:B"))

model.track()

print(model.get_measurements("SCL_Diag:BPM32:xAvg"))




print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

dict1 = {"SCL_LLRF:FCM23d:BlnkBeam": False}
model.update_optics(dict1)

print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

print("Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

dict1 = {"SCL_Mag:QV19:B": 0}
model.update_optics(dict1)

dict2 = {"SCL_LLRF:FCM23d:CtlPhaseSet": 0}
model.update_optics(dict2)

model.track()
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

model.save_optics(Path("test.json"))

print("\n reset check")
model.reset_optics()
model.track()

print("\n Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

model.load_optics(Path("test.json"))
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))


"""
avg_time = 0
for i in range(100):
    #init_phase = model.get_settings("SCL_LLRF:FCM01a:CtlPhaseSet")["SCL_LLRF:FCM01a:CtlPhaseSet"]
    #up_dict = {"SCL_LLRF:FCM01a:CtlPhaseSet": init_phase + 0.000000000000001}
    init_field = model.get_settings("SCL_Mag:QH00:B")["SCL_Mag:QH00:B"]
    up_dict = {"SCL_Mag:QH00:B": init_field + 0.00000000001}
    model.update_optics(up_dict)

    start_time = time.time()
    model.track()
    end_time = time.time()
    time_taken = end_time - start_time
    print(time_taken)
    avg_time += time_taken

avg_time /= 100
print(avg_time)

