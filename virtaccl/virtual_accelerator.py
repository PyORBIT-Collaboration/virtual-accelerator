# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import os
import sys
import time
import argparse
from datetime import datetime
from importlib.metadata import version

from virtaccl.server import Server, not_ctrlc
from virtaccl.beam_line import BeamLine
from virtaccl.model import Model


def va_parser():
    va_version = version('virtaccl')
    parser = argparse.ArgumentParser(
        description='Run the Virac virtual accelerator server. Version ' + va_version)
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates (default=1.0).')
    parser.add_argument('--sync_time', dest='sync_time', action='store_true',
                        help="Synchronize timestamps for PVs.")

    # Desired amount of output.
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help="Some debug info will be printed.")
    parser.add_argument('--production', dest='debug', action='store_false',
                        help="DEFAULT: No additional info printed.")
    parser.add_argument('--print_settings', dest='print_settings', action='store_true',
                        help="Will only print setting PVs. Will NOT run the virtual accelerator. (Default is off)")
    parser.add_argument('--print_pvs', dest='print_pvs', action='store_true',
                        help="Will print all PVs. Will NOT run the virtual accelerator. (Default is off)")

    # Number (in seconds) that determine some delay parameter in the server. Not exactly sure how it works, so use at
    # your own risk.
    parser.add_argument('--ca_proc', default=0.1, type=float,
                        help='Number (in seconds) that determine some delay parameter in the server. Not exactly sure '
                             'how it works, so use at your own risk. (Default=0.1)')

    return parser, va_version


def virtual_accelerator(model: Model, beam_line: BeamLine, server: Server, arguments: argparse.ArgumentParser):
    os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '10000000'

    args = arguments.parse_args()
    debug = args.debug
    sync_time = args.sync_time

    update_period = 1 / args.refresh_rate

    sever_parameters = beam_line.get_server_parameter_definitions()
    server.add_parameters(sever_parameters)

    if args.print_settings:
        for setting in beam_line.get_setting_keys():
            print(setting)
        sys.exit()
    elif args.print_pvs:
        for key in server.get_parameter_keys():
            print(key)
        sys.exit()

    delay = args.ca_proc
    server.process_delay = delay
    if debug:
        print(server)

    beam_line.reset_devices()
    server.start()
    print(f"Server started.")
    now = None

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()

        if sync_time:
            now = datetime.now()

        server_pvs = server.get_parameters()
        beam_line.update_settings_from_server(server_pvs)
        new_optics = beam_line.get_model_optics()
        model.update_optics(new_optics)

        model.track()

        new_measurements = model.get_measurements()
        beam_line.update_measurements_from_model(new_measurements)
        beam_line.update_readbacks()
        new_server_parameters = beam_line.get_parameters_for_server()
        server.set_parameters(new_server_parameters, timestamp=now)

        server.update()

        loop_time_taken = time.time() - loop_start_time
        sleep_time = update_period - loop_time_taken
        if sleep_time < 0.0:
            print('Warning: Update took longer than refresh rate.')
        else:
            time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')
