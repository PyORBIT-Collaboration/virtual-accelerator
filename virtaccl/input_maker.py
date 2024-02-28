import json
import sys
from pathlib import Path
from random import random
import argparse

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from virtaccl.pyorbit_controller import OrbitModel


def main():
    description = f"""
            Generates config files for accelerator sequences
            """
    epilog = """
            Example: input_maker SCLMed SCLHigh
            """
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--file', '-f', default='va_config.json', type=str,
                        help='Pathname of resulting config json file.')

    parser.add_argument('--lattice', default='sns_linac.xml', type=str,
                        help='Pathname of lattice file')

    parser.add_argument("Sequences", nargs='*', help='Sequences',
                        default=["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4",
                                 "SCLMed", "SCLHigh", "HEBT1", "HEBT2"])

    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of resulting randomized phase offset file for cavities and BPMs.')

    args = parser.parse_args()

    config_file = Path(args.file)
    lattice_file = args.lattice
    subsections = args.Sequences
    offset_file = args.phase_offset

    sns_linac_factory = SNS_LinacLatticeFactory()
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)

    model = OrbitModel(model_lattice)

    quad_doublets = {'SCL': ['01', '02', '03', '04', '05', '06', '07', '08', '09', '12', '13', '14', '15', '16',
                     '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29']}

    quad_sets = {'SCL_Mag:PS_QH32a33': ['32', '33'], 'HEBT_Mag:PS_QH04a06': ['04', '06'],
                 'HEBT_Mag:PS_QH12t18e': ['12', '14', '16', '18'], 'HEBT_Mag:PS_QV13t19o': ['13', '15', '17', '19']}

    cavity_key = 'RF_Cavity'
    quad_key = 'Quadrupole'
    doublet_key = 'Quadrupole_Doublet'
    q_sets_key = 'Quadrupole_Set'
    corrector_key = 'Corrector'
    BPM_key = 'BPM'
    pBPM_key = 'Physics_BPM'
    WS_key = 'Wire_Scanner'

    devices = {cavity_key: {},
               quad_key: {},
               doublet_key: {},
               q_sets_key: {},
               corrector_key: {},
               WS_key: {},
               BPM_key: {},
               pBPM_key: {}, }

    offsets = {}

    for or_name, ele_ref in model.pyorbit_dictionary.items():
        # All cavities are named after sequence name and one digit: MEBT1, CCL2
        # except SCL cavities: SCL:Cav03a
        ele_type = ele_ref.get_type()
        if ele_type == cavity_key:
            if 'SCL:Cav' in or_name:
                pv_name = "SCL_LLRF:FCM" + or_name[-3:]
            else:
                pv_name = or_name[:-1] + "_LLRF:FCM" + or_name[-1:]

            devices[cavity_key][pv_name] = or_name
            if offset_file is not None:
                offsets[pv_name] = (2 * random() - 1) * 180

        elif ele_type == quad_key:
            split_name = or_name.split(':')
            q_num = split_name[1][-2:]
            if 'PMQ' in or_name:
                pass
            elif 'SCL' in or_name and q_num in quad_doublets['SCL']:
                pv_name = f"{split_name[0]}:PS_QD{q_num}"
                if pv_name not in devices[doublet_key]:
                    devices[doublet_key][pv_name] = [or_name]
                else:
                    devices[doublet_key][pv_name].append(or_name)
            elif 'SCL_Mag:QH' in or_name and q_num in quad_sets['SCL_Mag:PS_QH32a33']:
                pv_name = 'SCL_Mag:PS_QH32a33'
                if pv_name not in devices[q_sets_key]:
                    devices[q_sets_key][pv_name] = [or_name]
                else:
                    devices[q_sets_key][pv_name].append(or_name)
            elif 'HEBT_Mag:QH' in or_name and q_num in quad_sets['HEBT_Mag:PS_QH04a06']:
                pv_name = 'HEBT_Mag:PS_QH04a06'
                if pv_name not in devices[q_sets_key]:
                    devices[q_sets_key][pv_name] = [or_name]
                else:
                    devices[q_sets_key][pv_name].append(or_name)
            elif 'HEBT_Mag:QH' in or_name and q_num in quad_sets['HEBT_Mag:PS_QH12t18e']:
                pv_name = 'HEBT_Mag:PS_QH12t18e'
                if pv_name not in devices[q_sets_key]:
                    devices[q_sets_key][pv_name] = [or_name]
                else:
                    devices[q_sets_key][pv_name].append(or_name)
            elif 'HEBT_Mag:QV' in or_name and q_num in quad_sets['HEBT_Mag:PS_QV13t19o']:
                pv_name = 'HEBT_Mag:PS_QV13t19o'
                if pv_name not in devices[q_sets_key]:
                    devices[q_sets_key][pv_name] = [or_name]
                else:
                    devices[q_sets_key][pv_name].append(or_name)
            else:
                pv_name = f"{split_name[0]}:PS_{split_name[1]}"
                devices[quad_key][pv_name] = or_name

        elif ele_type == corrector_key:
            split_name = or_name.split(':')
            pv_name = f"{split_name[0]}:PS_{split_name[1]}"
            devices[corrector_key][pv_name] = or_name

        elif ele_type == WS_key:
            pv_name = or_name
            devices[WS_key][pv_name] = or_name

        elif ele_type == BPM_key:
            pv_name = or_name
            devices[BPM_key][pv_name] = or_name
            if offset_file is not None:
                offsets[pv_name] = (2 * random() - 1) * 180

            pv_name = pv_name.replace('Diag', 'Phys')
            devices[pBPM_key][pv_name] = or_name

    with open(config_file, "w") as json_file:
        json.dump(devices, json_file, indent=4)

    if offset_file is not None:
        with open(offset_file, "w") as json_file:
            json.dump(offsets, json_file, indent=4)


if __name__ == "__main__":
    main()
