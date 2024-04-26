# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
import time
import argparse
from pathlib import Path

from virtaccl.ca_server import Server, epics_now, not_ctrlc
from virtaccl.PyORBIT_Model.virtual_devices import (Quadrupole, Corrector, Quadrupole_Power_Supply, WireScanner, BPM,
                                                    P_BPM)
from virtaccl.PyORBIT_Model.SNS.virtual_devices_SNS import SNS_Dummy_BCM, SNS_Dummy_ICS

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel

from virtaccl.site.IDmp.IDmp_maker import get_IDMP_lattice_and_bunch


def main():
    loc = Path(__file__).parent
    parser = argparse.ArgumentParser(description='Run CA server')
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')

    # Json file that contains a dictionary connecting EPICS name of devices with their associated element model names.
    parser.add_argument('--file', '-f', default=loc / 'va_config.json', type=str,
                        help='Pathname of config json file.')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates.')

    parser.add_argument('--particle_number', default=1000, type=int,
                        help='Number of particles to use.')

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
    part_num = args.particle_number

    lattice, bunch = get_IDMP_lattice_and_bunch(part_num, x_off=2, xp_off=0.3)
    model = OrbitModel(lattice, bunch, debug=debug)
    model.set_beam_current(38.0e-3)  # Set the initial beam current in Amps.
    element_list = model.get_element_list()

    server = Server()

    offset_file = args.phase_offset
    if offset_file is not None:
        with open(offset_file, "r") as json_file:
            offset_dict = json.load(json_file)

    mag_ps = devices_dict["Power_Supply"]

    quads = devices_dict["Quadrupole"]
    for name, device_dict in quads.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = abs(model.get_element_parameters(ele_name)['dB/dr'])
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in mag_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Quadrupole_Power_Supply(ps_name, initial_field)
                server.add_device(ps_device)
                corrector_device = Quadrupole(name, ele_name, power_supply=ps_device, polarity=polarity)
                server.add_device(corrector_device)

    correctors = devices_dict["Corrector"]
    for name, device_dict in correctors.items():
        ele_name = device_dict["PyORBIT_Name"]
        polarity = device_dict["Polarity"]
        if ele_name in element_list:
            initial_field = abs(model.get_element_parameters(ele_name)['B'])
            if "Power_Supply" in device_dict and device_dict["Power_Supply"] in mag_ps:
                ps_name = device_dict["Power_Supply"]
                ps_device = Quadrupole_Power_Supply(ps_name, initial_field)
                server.add_device(ps_device)
                corrector_device = Corrector(name, ele_name, power_supply=ps_device, polarity=polarity)
                server.add_device(corrector_device)

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
