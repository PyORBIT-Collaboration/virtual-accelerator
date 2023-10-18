import json
from pathlib import Path
from pyorbit_server_interface import OrbitModel

config_file = Path("va_config.json")

lattice_file = Path("sns_linac.xml")
pv_file = Path("server_devices.txt")
model = OrbitModel(lattice_file, ['SCLMed', 'SCLHigh'])

cavities = {}
cavity_params = {}
quads = {}
quad_params = {}
correctors = {}
corrector_params = {}
bpms = {}
bpm_params = {}
for name, pvref in model.pv_dict.get_pvref_dict().items():
    device_name = ':'.join(name.split(':')[:2])
    pyorbit_name = pvref.get_node_name()
    if 'BPM' in pyorbit_name:
        bpms[device_name] = pyorbit_name
        bpm_params[name.split(':')[2]] = {'parameter_key': pvref.get_param_key(), 'pv_types': ['diagnostic']}
    elif 'Q' in pyorbit_name:
        quads[device_name] = pyorbit_name
        quad_params[name.split(':')[2]] = {'parameter_key': pvref.get_param_key(),
                                           'pv_types': ['setting', 'readback']}
    elif 'DC' in pyorbit_name:
        correctors[device_name] = pyorbit_name
        corrector_params[name.split(':')[2]] = {'parameter_key': pvref.get_param_key(),
                                                'pv_types': ['setting', 'readback']}
    elif 'Cav' in pyorbit_name:
        cavities[device_name] = pyorbit_name
        cavity_params[name.split(':')[2]] = {'parameter_key': pvref.get_param_key(), 'pv_types': ['setting']}
    else:
        'Uh oh'

lattice = {'file_name': 'sns_linac.xml', 'subsections': ['SCLMed', 'SCLHigh']}

file_dict = {
    "pyorbit_lattice": lattice,
    "cavity_parameters": cavity_params,
    "cavities": cavities,
    "quadrupole_parameters": quad_params,
    "quadrupoles": quads,
    "corrector_parameters": corrector_params,
    "correctors": correctors,
    "bpm_parameters": bpm_params,
    "bpms": bpms
}

with open(config_file, "w") as json_file:
    json.dump(file_dict, json_file, indent=4)
