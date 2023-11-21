import json
from pathlib import Path
from random import random

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from pyorbit_server_interface import OrbitModel

config_file = Path("va_config.json")
offset_file = Path("va_offsets.json")

lattice_str = "sns_linac.xml"
subsections = ['SCLMed', 'SCLHigh', 'HEBT1']

sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)
model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_str)

model = OrbitModel(model_lattice)

devices = {'Cavities': {},
           'Quadrupoles': {},
           'Correctors': {},
           'BPMs': {},
           'PBPMs': {}, }

offsets = {}

for or_name, ele_ref in model.pyorbit_dict.get_element_dictionary().items():
    if 'Cav' in or_name:
        pv_name = "SCL_LLRF:FCM" + or_name[-3:]
        devices['Cavities'][pv_name] = or_name
        offsets[pv_name] = (2 * random() - 1) * 180
    elif 'Q' in or_name:
        split_name = or_name.split(':')
        pv_name = f"{split_name[0]}:PS_{split_name[1]}"
        devices['Quadrupoles'][pv_name] = or_name
    elif 'DC' in or_name:
        split_name = or_name.split(':')
        pv_name = f"{split_name[0]}:PS_{split_name[1]}"
        devices['Correctors'][pv_name] = or_name
    elif 'BPM' in or_name:
        pv_name = or_name
        devices['BPMs'][pv_name] = or_name
        offsets[pv_name] = (2 * random() - 1) * 180

        pv_name = pv_name.replace('Diag', 'Phys')
        devices['PBPMs'][pv_name] = or_name

with open(config_file, "w") as json_file:
    json.dump(devices, json_file, indent=4)

with open(offset_file, "w") as json_file:
    json.dump(offsets, json_file, indent=4)
