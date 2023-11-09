import json
from pathlib import Path
from random import random

from pyorbit_server_interface import OrbitModel

config_file = Path("va_config.json")

lattice_str = "sns_linac.xml"
subsections = ['SCLMed', 'SCLHigh', 'HEBT1']

lattice_file = Path(lattice_str)
model = OrbitModel(lattice_file, subsections)

cavity_params = {"CtlPhaseSet": {"parameter_key": "phase", "pv_type": "setting"},
                 "CtlAmpSet": {"parameter_key": "amp", "pv_type": "setting"},
                 "BlnkBeam": {"parameter_key": "blanked", "pv_type": "setting"}}

quad_params = {"B_set": {"parameter_key": "dB/dr", "pv_type": "setting"},
               "B": {"parameter_key": "dB/dr", "pv_type": "readback", "noise": 0.0001}}

corrector_params = {"B_set": {"parameter_key": "B", "pv_type": "setting"},
                    "B": {"parameter_key": "B", "pv_type": "readback", "noise": 0.0001}}

bpm_params = {"xAvg": {"parameter_key": "x_avg", "pv_type": "diagnostic", "noise": 1e-7},
              "yAvg": {"parameter_key": "y_avg", "pv_type": "diagnostic", "noise": 1e-7},
              "phaseAvg": {"parameter_key": "phi_avg", "pv_type": "diagnostic", "noise": 0.001}}

pbpm_params = {"Energy": {"parameter_key": "energy", "pv_type": "physics"},
               "Beta": {"parameter_key": "beta", "pv_type": "physics"}}

devices = {'Cavities': {'parameters': cavity_params, 'devices': {}},
           'Quadrupoles': {'parameters': quad_params, 'devices': {}},
           'Correctors': {'parameters': corrector_params, 'devices': {}},
           'BPMs': {'parameters': bpm_params, 'devices': {}},
           'PBPMs': {'parameters': pbpm_params, 'devices': {}}, }

for or_name, ele_ref in model.pyorbit_dict.get_element_dictionary().items():
    if 'Cav' in or_name:
        pv_name = "SCL_LLRF:FCM" + or_name[-3:]
        devices['Cavities']['devices'][pv_name] = {'pyorbit_name': or_name, 'override':
            {"CtlAmpSet": {"linear_offset": 14.9339}, "CtlPhaseSet": {"phase_offset": (2 * random() - 1) * 180}}}
    elif 'Q' in or_name:
        pv_name = or_name
        devices['Quadrupoles']['devices'][pv_name] = {'pyorbit_name': or_name}
    elif 'DC' in or_name:
        pv_name = or_name
        devices['Correctors']['devices'][pv_name] = {'pyorbit_name': or_name}
    elif 'BPM' in or_name:
        pv_name = or_name
        devices['BPMs']['devices'][pv_name] = {'pyorbit_name': or_name, 'override':
            {"phaseAvg": {"phase_offset": (2 * random() - 1) * 180}}}
        pv_name = pv_name.replace('Diag', 'Phys')
        devices['PBPMs']['devices'][pv_name] = {'pyorbit_name': or_name}

lattice = {'file_name': lattice_str, 'subsections': subsections}

file_dict = {
    "Pyorbit_Lattice": lattice,
    "Devices": devices
}

with open(config_file, "w") as json_file:
    json.dump(file_dict, json_file, indent=4)
