import json
import sys
from pathlib import Path
from pyorbit_server_interface import OrbitModel

config_file = Path("va_config.json")

lattice_str = "sns_linac.xml"
subsections = ['SCLMed', 'SCLHigh', 'HEBT1']

lattice_file = Path(lattice_str)
model = OrbitModel(lattice_file, subsections)

cavity_params = {"CtlPhaseSet": {"parameter_key": "phase", "pv_type": "setting"},
                 "CtlAmpSet": {"parameter_key": "amp", "pv_type": "setting"},
                 "BlnkBeam": {"parameter_key": "blanked", "pv_type": "setting"}}

quad_params = {"B_set": {"parameter_key": "field", "pv_type": "setting"},
               "B": {"parameter_key": "field", "pv_type": "readback"}}

corrector_params = {"B_set": {"parameter_key": "B", "pv_type": "setting"},
                    "B": {"parameter_key": "B", "pv_type": "readback"}}

bpm_params = {"xAvg": {"parameter_key": "x_avg", "pv_type": "diagnostic"},
              "yAvg": {"parameter_key": "y_avg", "pv_type": "diagnostic"},
              "phaseAvg": {"parameter_key": "phi_avg", "pv_type": "diagnostic"}}

pbpm_params = {"Energy": {"parameter_key": "energy", "pv_type": "physics"},
               "Beta": {"parameter_key": "beta", "pv_type": "physics"}}

devices = {'Cavities': {'parameters': cavity_params, 'devices': {}},
           'Quadrupoles': {'parameters': quad_params, 'devices': {}},
           'Correctors': {'parameters': corrector_params, 'devices': {}},
           'BPMs': {'parameters': bpm_params, 'devices': {}},
           'PBPMs': {'parameters': pbpm_params, 'devices': {}},}

for or_name, ele_ref in model.pyorbit_dict.get_element_dictionary().items():
    if 'Cav' in or_name:
        pv_name = "SCL_LLRF:FCM" + or_name[-3:]
        devices['Cavities']['devices'][pv_name] = or_name
    elif 'Q' in or_name:
        pv_name = or_name
        devices['Quadrupoles']['devices'][pv_name] = or_name
    elif 'DC' in or_name:
        pv_name = or_name
        devices['Correctors']['devices'][pv_name] = or_name
    elif 'BPM' in or_name:
        pv_name = or_name
        devices['BPMs']['devices'][pv_name] = or_name
        pv_name = pv_name.replace('Diag', 'Phys')
        devices['PBPMs']['devices'][pv_name] = or_name

lattice = {'file_name': lattice_str, 'subsections': subsections}

file_dict = {
    "Pyorbit_Lattice": lattice,
    "Devices": devices
}

with open(config_file, "w") as json_file:
    json.dump(file_dict, json_file, indent=4)
