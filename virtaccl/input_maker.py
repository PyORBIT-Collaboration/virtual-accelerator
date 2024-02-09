import json
import sys
from pathlib import Path
from random import random
import argparse

from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from virtaccl.pyorbit_server_interface import OrbitModel


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
                                 "SCLMed", "SCLHigh", "HEBT1"])

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

    cavity_key = 'RF_Cavity'
    quad_key = 'Quadrupole'
    doublet_key = 'Quadrupole_Doublet'
    corrector_key = 'Corrector'
    BPM_key = 'BPM'
    pBPM_key = 'Physics_BPM'
    WS_key = 'Wire_Scanner'

    devices = {cavity_key: {},
               quad_key: {},
               doublet_key: {},
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
            if 'PMQ' in or_name:
                pass
            elif 'SCL_Mag:QH01' in or_name or 'SCL_Mag:QV01' in or_name:
                split_name = or_name.split(':')
                pv_name = f"{split_name[0]}:PS_QD01"
                if pv_name not in devices[doublet_key]:
                    devices[doublet_key][pv_name] = [or_name]
                else:
                    devices[doublet_key][pv_name].append(or_name)
            else:
                split_name = or_name.split(':')
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
