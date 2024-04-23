import json
import sys
from pathlib import Path
from random import random
import argparse

from virtaccl.PyORBIT_Model.pyorbit_lattice_factory import PyORBIT_Lattice_Factory

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel


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

    parser.add_argument('--lattice', default='PyORBIT_Model/SNS/sns_linac.xml', type=str,
                        help='Pathname of lattice file')

    parser.add_argument("Sequences", nargs='*', help='Sequences',
                        default=["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4",
                                 "SCLMed", "SCLHigh", "HEBT1", "HEBT2", "LDmp"])

    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of resulting randomized phase offset file for cavities and BPMs.')

    args = parser.parse_args()

    config_file = Path(args.file)
    lattice_file = args.lattice
    subsections = args.Sequences
    offset_file = args.phase_offset

    sns_linac_factory = PyORBIT_Lattice_Factory()
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)

    model = OrbitModel(model_lattice)

    quad_doublets = {'SCL': ['01', '02', '03', '04', '05', '06', '07', '08', '09', '12', '13', '14', '15', '16',
                             '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29']}

    mag_sets = {'CCL_Mag:PS_Q104t111': {'hor': ['104', '106', '108', '110'], 'ver': ['105', '107', '109', '111']},
                'CCL_Mag:PS_Q112t207': {'hor': ['112', '202', '204', '206'], 'ver': ['201', '203', '205', '207']},
                'CCL_Mag:PS_Q208t303': {'hor': ['208', '210', '212', '302'], 'ver': ['209', '211', '301', '303']},
                'CCL_Mag:PS_Q304t311': {'hor': ['304', '306', '308', '310'], 'ver': ['305', '307', '309', '311']},
                'CCL_Mag:PS_Q312t407': {'hor': ['312', '402', '404', '406'], 'ver': ['401', '403', '405', '407']},
                'SCL_Mag:PS_QH32a33': ['32', '33'], 'HEBT_Mag:PS_QH04a06': ['04', '06'],
                'HEBT_Mag:PS_QH12t18e': ['12', '14', '16', '18'], 'HEBT_Mag:PS_QV13t19o': ['13', '15', '17', '19'],
                'HEBT_Mag:PS_DH12t18': ['12', '13', '14', '15', '16', '17', '18'],
                'HEBT_Mag:PS_QV25t31o': ['25', '27', '29', '31'], 'HEBT_Mag:PS_QH26a28a32': ['26', '28', '32']}

    bpm_frequencies = {'MEBT': 805e6, 'DTL': 805e6, 'CCL': 402.5e6, 'SCL': 402.5e6, 'HEBT': 402.5e6, 'LDmp': 402.5e6}

    cavity_amps = {'MEBT1': 0.450, 'MEBT2': 0.314, 'MEBT3': 0.445, 'MEBT4': 0.600,
                   'DTL1': 0.192, 'DTL2': 0.495, 'DTL3': 0.457, 'DTL4': 0.615, 'DTL5': 0.570, 'DTL6': 0.525,
                   'CCL1': 0.811, 'CCL2': 0.793, 'CCL3': 0.689, 'CCL4': 0.788,
                   'SCLMed': 14.9339, 'SCL:Cav12a': 21.875, 'SCLHigh': 22.807}

    cavity_key = 'RF_Cavity'
    quad_key = 'Quadrupole'
    corrector_key = 'Corrector'
    bend_key = 'Bend'
    BPM_key = 'BPM'
    pBPM_key = 'Physics_BPM'
    WS_key = 'Wire_Scanner'
    QPS_key = 'Quadrupole_Power_Supply'
    CPS_key = 'Corrector_Power_Supply'
    BPS_key = 'Bend_Power_Supply'
    QPShunt_key = 'Quadrupole_Power_Shunt'
    shunt_key = 'Power_Shunt'
    pyorbit_key = 'PyORBIT_Name'
    polarity_key = 'Polarity'
    PS_key = 'Power_Supply'
    freq_key = 'Frequency'
    marker_key = 'Marker'
    amp_key = 'Design_Amplitude'

    devices = {cavity_key: {},
               quad_key: {},
               corrector_key: {},
               bend_key: {},
               WS_key: {},
               BPM_key: {},
               QPS_key: [],
               QPShunt_key: [],
               CPS_key: [],
               BPS_key: [],
               pBPM_key: {}, }

    offsets = {}

    for or_name, ele_ref in model.pyorbit_dictionary.items():
        # All cavities are named after sequence name and one digit: MEBT1, CCL2
        # except SCL cavities: SCL:Cav03a
        ele_type = ele_ref.get_type()
        if ele_type == cavity_key:
            amplitude = None
            if 'SCL:Cav' in or_name:
                pv_name = "SCL_LLRF:FCM" + or_name[-3:]
                if or_name == 'SCL:Cav12a':
                    amplitude = cavity_amps['SCL:Cav12a']
                elif ele_ref.get_first_node().getSequence().getName() == 'SCLMed':
                    amplitude = cavity_amps['SCLMed']
                elif ele_ref.get_first_node().getSequence().getName() == 'SCLHigh':
                    amplitude = cavity_amps['SCLHigh']
            else:
                pv_name = or_name[:-1] + "_LLRF:FCM" + or_name[-1:]
                for cav, amp in cavity_amps.items():
                    if cav in or_name:
                        amplitude = amp
            if amplitude:
                devices[cavity_key][pv_name] = {pyorbit_key: or_name, amp_key: amplitude}
            else:
                devices[cavity_key][pv_name] = or_name
            if offset_file is not None:
                offsets[pv_name] = (2 * random() - 1) * 180

        elif ele_type == quad_key:
            split_name = or_name.split(':')
            q_num = split_name[1][-2:]
            if 'CCL_Mag:QT' in or_name:
                q_num = split_name[1][-3:]
            if 'PMQ' in or_name:
                pass
            elif 'SCL' in or_name and q_num in quad_doublets['SCL']:
                pv_name = or_name
                ps_name = f"{split_name[0]}:PS_QD{q_num}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                if 'QH' in or_name:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}
                elif 'QV' in or_name:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: 1}

            elif 'CCL_Mag:' in or_name and (q_num in mag_sets['CCL_Mag:PS_Q104t111']['hor'] or
                                            q_num in mag_sets['CCL_Mag:PS_Q104t111']['ver']):
                ps_name = 'CCL_Mag:PS_Q104t111'
                pv_name = or_name
                shunt_name = f"{split_name[0]}:ShntC_{split_name[1]}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[QPShunt_key].append(shunt_name)
                if q_num in mag_sets['CCL_Mag:PS_Q104t111']['hor']:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: 1}

            elif 'CCL_Mag:' in or_name and (q_num in mag_sets['CCL_Mag:PS_Q112t207']['hor'] or
                                            q_num in mag_sets['CCL_Mag:PS_Q112t207']['ver']):
                ps_name = 'CCL_Mag:PS_Q112t207'
                pv_name = or_name
                shunt_name = f"{split_name[0]}:ShntC_{split_name[1]}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[QPShunt_key].append(shunt_name)
                if q_num in mag_sets['CCL_Mag:PS_Q112t207']['hor']:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: 1}

            elif 'CCL_Mag:' in or_name and (q_num in mag_sets['CCL_Mag:PS_Q208t303']['hor'] or
                                            q_num in mag_sets['CCL_Mag:PS_Q208t303']['ver']):
                ps_name = 'CCL_Mag:PS_Q208t303'
                pv_name = or_name
                shunt_name = f"{split_name[0]}:ShntC_{split_name[1]}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[QPShunt_key].append(shunt_name)
                if q_num in mag_sets['CCL_Mag:PS_Q208t303']['hor']:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: 1}

            elif 'CCL_Mag:' in or_name and (q_num in mag_sets['CCL_Mag:PS_Q304t311']['hor'] or
                                            q_num in mag_sets['CCL_Mag:PS_Q304t311']['ver']):
                ps_name = 'CCL_Mag:PS_Q304t311'
                pv_name = or_name
                shunt_name = f"{split_name[0]}:ShntC_{split_name[1]}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[QPShunt_key].append(shunt_name)
                if q_num in mag_sets['CCL_Mag:PS_Q304t311']['hor']:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: 1}

            elif 'CCL_Mag:' in or_name and (q_num in mag_sets['CCL_Mag:PS_Q312t407']['hor'] or
                                            q_num in mag_sets['CCL_Mag:PS_Q312t407']['ver']):
                ps_name = 'CCL_Mag:PS_Q312t407'
                pv_name = or_name
                shunt_name = f"{split_name[0]}:ShntC_{split_name[1]}"
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[QPShunt_key].append(shunt_name)
                if q_num in mag_sets['CCL_Mag:PS_Q312t407']['hor']:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, shunt_key: shunt_name,
                                                  polarity_key: 1}

            elif 'SCL_Mag:QH' in or_name and q_num in mag_sets['SCL_Mag:PS_QH32a33']:
                pv_name = or_name
                ps_name = 'SCL_Mag:PS_QH32a33'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}

            elif 'HEBT_Mag:QH' in or_name and q_num in mag_sets['HEBT_Mag:PS_QH04a06']:
                pv_name = or_name
                ps_name = 'HEBT_Mag:PS_QH04a06'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}

            elif 'HEBT_Mag:QH' in or_name and q_num in mag_sets['HEBT_Mag:PS_QH12t18e']:
                pv_name = or_name
                ps_name = 'HEBT_Mag:PS_QH12t18e'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}

            elif 'HEBT_Mag:QV' in or_name and q_num in mag_sets['HEBT_Mag:PS_QV13t19o']:
                pv_name = or_name
                ps_name = 'HEBT_Mag:PS_QV13t19o'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: 1}

            elif 'HEBT_Mag:QV' in or_name and q_num in mag_sets['HEBT_Mag:PS_QV25t31o']:
                pv_name = or_name
                ps_name = 'HEBT_Mag:PS_QV25t31o'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: 1}

            elif 'HEBT_Mag:QH' in or_name and q_num in mag_sets['HEBT_Mag:PS_QH26a28a32']:
                pv_name = or_name
                ps_name = 'HEBT_Mag:PS_QH26a28a32'
                if ps_name not in devices[QPS_key]:
                    devices[QPS_key].append(ps_name)
                devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}

            else:
                pv_name = or_name
                ps_name = f"{split_name[0]}:PS_{split_name[1]}"
                devices[QPS_key].append(ps_name)
                if 'QH' in or_name:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}
                else:
                    devices[quad_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: 1}

        elif ele_type == corrector_key:
            pv_name = or_name
            split_name = or_name.split(':')
            ps_name = f"{split_name[0]}:PS_{split_name[1]}"
            devices[corrector_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name, polarity_key: -1}
            devices[CPS_key].append(ps_name)

        elif ele_type == bend_key:
            pv_name = or_name
            split_name = or_name.split(':')
            b_num = split_name[1][-2:]
            if b_num in mag_sets['HEBT_Mag:PS_DH12t18']:
                ps_name = 'HEBT_Mag:PS_DH12t18'
                if ps_name not in devices[BPS_key]:
                    devices[BPS_key].append(ps_name)
                devices[bend_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name}
            else:
                ps_name = f"{split_name[0]}:PS_{split_name[1]}"
                devices[bend_key][pv_name] = {pyorbit_key: or_name, PS_key: ps_name}
                devices[BPS_key].append(ps_name)

        elif ele_type == marker_key:
            if 'WS' in or_name:
                pv_name = or_name
                devices[WS_key][pv_name] = or_name
            elif 'BPM' in or_name:
                pv_name = or_name
                frequency = 402.5e6
                for seq, freq in bpm_frequencies.items():
                    if seq in pv_name:
                        frequency = freq
                devices[BPM_key][pv_name] = {pyorbit_key: or_name, freq_key: frequency}
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
