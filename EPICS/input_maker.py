import json
from pathlib import Path
from random import random
import argparse

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from pyorbit_server_interface import OrbitModel



def main():
    mebt_map = {
        "MEBT_RF:Bnch01": "MEBT_LLRF:FCM1",
        "MEBT_RF:Bnch02": "MEBT_LLRF:FCM2",
        "MEBT_RF:Bnch03": "MEBT_LLRF:FCM3",
        "MEBT_RF:Bnch04": "MEBT_LLRF:FCM4",

    }

    description = f"""
            Generates config files for accelerator sequences
            """
    epilog = """
            Example: input_maker SCLMed SCLHigh
            """
    parser = argparse.ArgumentParser( description=description, epilog=epilog,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of resulting config json file.')
    parser.add_argument("Sequences", nargs='*', help='Sequences', default=['SCLMed', 'SCLHigh', 'HEBT1'])
    args = parser.parse_args()

    config_file = Path(args.file)
    config_name = config_file.name.split('.')[0]
    offset_name = config_name[0:-7] + '_offsets.json' if config_name.endswith('_config') else config_name + '_offset.json'
    offset_file = config_file.parent / offset_name

    lattice_str = "sns_linac.xml"
    subsections = args.Sequences


    sns_linac_factory = SNS_LinacLatticeFactory()
    sns_linac_factory.setMaxDriftLength(0.01)
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_str)

    model = OrbitModel(model_lattice)

    devices = {'Cavities': {},
               'Quadrupoles': {},
               'Correctors': {},
               'Wire_Scanners': {},
               'BPMs': {},
               'PBPMs': {}, }

    offsets = {}

    for or_name, ele_ref in model.pyorbit_dict.get_element_dictionary().items():
        if or_name in mebt_map:
            pv_name = mebt_map[or_name]
            devices['Cavities'][pv_name] = or_name
            offsets[pv_name] = (2 * random() - 1) * 180
        elif 'Cav' in or_name:
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
        elif 'WS' in or_name:
            pv_name = or_name
            devices['Wire_Scanners'][pv_name] = or_name
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

if __name__ == "__main__":
    main()

