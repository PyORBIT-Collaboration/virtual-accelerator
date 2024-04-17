# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
import time
import argparse
from pathlib import Path
from importlib.metadata import version

from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory

from orbit.core.bunch import Bunch
from orbit.core.linac import BaseRfGap, RfGapTTF

from virtaccl.ca_server import Server, epics_now, not_ctrlc
from virtaccl.PyORBIT_Model.virtual_devices import Cavity, BPM, Quadrupole, Corrector, P_BPM, \
    WireScanner, Magnet_Power_Supply, Bend
from virtaccl.PyORBIT_Model.SNS.virtual_devices_SNS import SNS_Dummy_BCM, SNS_Cavity, SNS_Dummy_ICS

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel


def load_config(filename: Path):
    with open(filename, "r") as json_file:
        devices_dict = json.load(json_file)


def main():
    loc = Path(__file__).parent
    va_version = version('virtaccl')
    parser = argparse.ArgumentParser(
        description='Run the SNS PyORBIT virtual accelerator server. Version ' + va_version)
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')

    # Json file that contains a dictionary connecting EPICS name of devices with their associated element model names.
    parser.add_argument('--file', '-f', default=loc / 'va_config.json', type=str,
                        help='Pathname of config json file.')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates (default=1.0).')

    # Lattice xml input file and the sequences desired from that file.
    parser.add_argument('--lattice', default=loc / 'PyORBIT_Model/SNS/sns_sts_linac.xml', type=str,
                        help='Pathname of lattice file')
    parser.add_argument("--start", default="MEBT", type=str,
                        help='Desired subsection of the lattice to start the model with (default=MEBT).')
    parser.add_argument("end", nargs='?', default="HEBT2", type=str,
                        help='Desired subsection of the lattice to end the model with (default=HEBT2).')

    # Desired initial bunch file and the desired number of particles from that file.
    parser.add_argument('--bunch', default=loc / 'PyORBIT_Model/SNS/MEBT_in.dat', type=str,
                        help='Pathname of input bunch file.')
    parser.add_argument('--particle_number', default=1000, type=int,
                        help='Number of particles to use (default=1000).')

    # Json file that contains a dictionary connecting EPICS name of devices with their phase offset.
    parser.add_argument('--phase_offset', default=None, type=str,
                        help='Pathname of phase offset file.')

    # Desired amount of output.
    parser.add_argument('--debug', dest='debug', action='store_true', help="Some debug info will be printed.")
    parser.add_argument('--production', dest='debug', action='store_false',
                        help="DEFAULT: No additional info printed.")

    args = parser.parse_args()
    debug = args.debug

    config_file = Path(args.file)
    with open(config_file, "r") as json_file:
        devices_dict = json.load(json_file)

    update_period = 1 / args.refresh_rate

    lattice_file = args.lattice
    all_sections = ["MEBT", "DTL1", "DTL2", "DTL3", "DTL4", "DTL5", "DTL6", "CCL1", "CCL2", "CCL3", "CCL4",
                    "SCLMed", "SCLHigh", "HEBT1", "HEBT2"]
    sec_start = all_sections.index(args.start)
    sec_end = all_sections.index(args.end)
    subsections = all_sections[sec_start:sec_end + 1]
    if not subsections:
        print("Error: No subsections of the lattice selectable using current arguments.")
        sys.exit()

    sns_linac_factory = SNS_LinacLatticeFactory()
    sns_linac_factory.setMaxDriftLength(0.01)
    model_lattice = sns_linac_factory.getLinacAccLattice(subsections, lattice_file)
    cppGapModel = BaseRfGap
    # cppGapModel = RfGapTTF
    rf_gaps = model_lattice.getRF_Gaps()
    for rf_gap in rf_gaps:
        rf_gap.setCppGapModel(cppGapModel())
    # cavities = model_lattice.getRF_Cavities()
    # for cavity in cavities:
    #     if 'SCL' in cavity.getName():
    #         cavity.setAmp(0.0)
    # Add_quad_apertures_to_lattice(model_lattice)
    # Add_rfgap_apertures_to_lattice(model_lattice)

    bunch_file = Path(args.bunch)
    part_num = args.particle_number

    bunch_in = Bunch()
    bunch_in.readBunch(str(bunch_file))
    bunch_orig_num = bunch_in.getSizeGlobal()
    if bunch_orig_num < part_num:
        print('Bunch file contains less particles than the desired number of particles.')
    elif part_num <= 0:
        bunch_in.deleteAllParticles()
    else:
        bunch_macrosize = bunch_in.macroSize()
        bunch_macrosize *= bunch_orig_num / part_num
        bunch_in.macroSize(bunch_macrosize)
        for n in range(bunch_orig_num):
            if n + 1 > part_num:
                bunch_in.deleteParticleFast(n)
        bunch_in.compress()

    model = OrbitModel(model_lattice, bunch_in, debug=debug)
    model.set_beam_current(38.0e-3)  # Set the initial beam current in Amps.
    element_list = model.get_element_list()

    # Give BPMs their proper frequencies
    bpm_frequencies = {'MEBT': 805e6, 'DTL': 805e6, 'CCL': 402.5e6, 'SCL': 402.5e6, 'HEBT': 402.5e6}
    for element in element_list:
        if 'BPM' in element:
            for seq, freq in bpm_frequencies.items():
                if seq in element:
                    model.get_element_dictionary()[element].set_parameter('frequency', freq)

    # Retrack the bunch to update BPMs with their new frequencies.
    model.force_track()

    server = Server()

    offset_file = args.phase_offset
    if offset_file is not None:
        with open(offset_file, "r") as json_file:
            offset_dict = json.load(json_file)

    cavities = devices_dict["RF_Cavity"]
    for name, model_name in cavities.items():
        if model_name in element_list:
            initial_settings = model.get_element_parameters(model_name)
            initial_settings['amp'] = 1
            phase_offset = 0
            if offset_file is not None:
                phase_offset = offset_dict[name]
            rf_device = SNS_Cavity(name, model_name, initial_dict=initial_settings, phase_offset=phase_offset)
            server.add_device(rf_device)

    mag_ps = devices_dict["Power_Supply"]
    ps_quads = {}
    for name in mag_ps:
        ps_quads[name] = {"quads": {}, "avg_field": 0}

    quads = devices_dict["Quadrupole"]
    for name, device_dict in quads.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_settings = model.get_element_parameters(ele_name)
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in mag_ps:
                ps_name = device_dict["Power_Supply"]
                if "Power_Shunt" in device_dict and device_dict["Power_Shunt"] in mag_ps:
                    shunt_name = device_dict["Power_Shunt"]
                    ps_quads[ps_name]["quads"] |= \
                        {name: {'or_name': ele_name, 'shunt': shunt_name, 'dB/dr': abs(initial_settings['dB/dr']),
                                'polarity': polarity}}
                    ps_quads[ps_name]["avg_field"] += abs(initial_settings['dB/dr'])
                else:
                    ps_quads[ps_name]["quads"] |= \
                        {name: {'or_name': ele_name, 'shunt': 'none', 'dB/dr': abs(initial_settings['dB/dr']),
                                'polarity': polarity}}
                    ps_quads[ps_name]["avg_field"] += abs(initial_settings['dB/dr'])

    for ps_name, ps_dict in ps_quads.items():
        if ps_dict["quads"]:
            ps_dict["avg_field"] /= len(ps_dict["quads"])
            ps_field = ps_dict["avg_field"]
            ps_device = Magnet_Power_Supply(ps_name, ps_field)
            server.add_device(ps_device)
            for quad_name, quad_model in ps_dict["quads"].items():
                if quad_model['shunt'] == 'none':
                    quad_device = Quadrupole(quad_name, quad_model['or_name'], power_supply=ps_device,
                                             polarity=quad_model['polarity'])
                else:
                    shunt_name = quad_model['shunt']
                    field = quad_model['dB/dr']
                    shunt_field = field - ps_field
                    shunt_device = Magnet_Power_Supply(shunt_name, shunt_field)
                    server.add_device(shunt_device)
                    quad_device = Quadrupole(quad_name, quad_model['or_name'], power_supply=ps_device,
                                             power_shunt=shunt_device, polarity=quad_model['polarity'])
                server.add_device(quad_device)

    correctors = devices_dict["Corrector"]
    for name, device_dict in correctors.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = model.get_element_parameters(ele_name)['B']
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in mag_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Magnet_Power_Supply(ps_name, initial_field)
                server.add_device(ps_device)
                corrector_device = Corrector(name, ele_name, power_supply=ps_device, polarity=polarity)
                server.add_device(corrector_device)

    bends = devices_dict["Bend"]
    for name, device_dict in bends.items():
        ele_name = device_dict["PyORBIT_Name"]
        if ele_name in element_list:
            initial_field = 0
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in mag_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Magnet_Power_Supply(ps_name, initial_field)
                server.add_device(ps_device)
                bend_device = Bend(name, ele_name, power_supply=ps_device)
                server.add_device(bend_device)

    wire_scanners = devices_dict["Wire_Scanner"]
    for name, model_name in wire_scanners.items():
        if model_name in element_list:
            ws_device = WireScanner(name, model_name)
            server.add_device(ws_device)

    bpms = devices_dict["BPM"]
    for name, model_name in bpms.items():
        if model_name in element_list:
            phase_offset = 0
            if offset_file is not None:
                phase_offset = offset_dict[name]
            bpm_device = BPM(name, model_name, phase_offset=phase_offset)
            server.add_device(bpm_device)

    pbpms = devices_dict["Physics_BPM"]
    for name, model_name in pbpms.items():
        if model_name in element_list:
            pbpm_device = P_BPM(name, model_name)
            server.add_device(pbpm_device)

    dummy_device = SNS_Dummy_BCM("Ring_Diag:BCM_D09", 'HEBT_Diag:BPM11')
    server.add_device(dummy_device)
    dummy_device = SNS_Dummy_ICS("ICS_Tim")
    server.add_device(dummy_device)

    if debug:
        print(server)
    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()

        now = epics_now()

        new_params = server.get_settings()
        server.update_readbacks()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.update_measurements(new_measurements)

        server.update()

        loop_time_taken = time.time() - loop_start_time
        sleep_time = update_period - loop_time_taken
        if sleep_time < 0.0:
            print('Warning: Update took longer than refresh rate.')
        else:
            time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')


if __name__ == '__main__':
    main()
