import json
import sys
from pathlib import Path
from pyorbit_server_interface import OrbitModel

config_file = Path("va_config.json")

lattice_str = "sns_linac.xml"
subsections = ['SCLMed', 'SCLHigh', 'HEBT1']

lattice_file = Path(lattice_str)
model = OrbitModel(lattice_file, subsections)

cavities = {}
quads = {}
correctors = {}
bpms = {}
pbpms = {}

cavity_params = {"CtlPhaseSet": {"parameter_key": "phase", "pv_types": ["setting"]},
              "CtlAmpSet": {"parameter_key": "amp", "pv_types": ["setting"]},
              "BlnkBeam": {"parameter_key": "blanked", "pv_types": ["setting"]}}

quad_params = {"B_set": {"parameter_key": "field", "pv_types": ["setting"]},
               "B": {"parameter_key": "field", "pv_types": ["readback"]}}

corrector_params = {"B_set": {"parameter_key": "B", "pv_types": ["setting"]},
                    "B": {"parameter_key": "B", "pv_types": ["readback"]}}

bpm_params = {"xAvg": {"parameter_key": "x_avg", "pv_types": ["diagnostic"]},
              "yAvg": {"parameter_key": "y_avg", "pv_types": ["diagnostic"]},
              "phaseAvg": {"parameter_key": "phi_avg", "pv_types": ["diagnostic"]}}

pbpm_params = {"Energy": {"parameter_key": "energy", "pv_types": ["physics"]}}

for or_name, ele_ref in model.pyorbit_dict.get_element_dictionary().items():
    if 'Cav' in or_name:
        pv_name = "SCL_LLRF:FCM" + or_name[-3:]
        cavities[pv_name] = or_name
    elif 'Q' in or_name:
        pv_name = or_name
        quads[pv_name] = or_name
    elif 'DC' in or_name:
        pv_name = or_name
        correctors[pv_name] = or_name
    elif 'BPM' in or_name:
        pv_name = or_name
        bpms[pv_name] = or_name
        pv_name = pv_name.replace('Diag', 'Phys')
        pbpms[pv_name] = or_name

lattice = {'file_name': lattice_str, 'subsections': subsections}

file_dict = {
    "pyorbit_lattice": lattice,
    "cavity_parameters": cavity_params,
    "cavities": cavities,
    "quadrupole_parameters": quad_params,
    "quadrupoles": quads,
    "corrector_parameters": corrector_params,
    "correctors": correctors,
    "bpm_parameters": bpm_params,
    "bpms": bpms,
    "pbpm_parameters": pbpm_params,
    "pbpms": pbpms
}

with open(config_file, "w") as json_file:
    json.dump(file_dict, json_file, indent=4)
