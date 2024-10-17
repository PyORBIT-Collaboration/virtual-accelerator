import os
import sys
import time
import argparse
from datetime import datetime
from importlib.metadata import version
from typing import Dict, Any

from virtaccl.server import Server, not_ctrlc
from virtaccl.beam_line import BeamLine
from virtaccl.model import Model


class VA_Parser:
    def __init__(self):
        self.arguments: Dict[str, Dict[str, Any]] = {}
        self.version = version('virtaccl')
        self.description = 'Run the Virac virtual accelerator server.'

        add_va_arguments(self)

    def set_description(self, new_description: str):
        self.description = new_description

    def add_argument(self, *args, **kwargs):
        self.arguments[args[0]] = {'positional': args, 'optional': kwargs}

    def remove_argument(self, name: str):
        del self.arguments[name]

    def edit_argument(self, name: str, argument_keyword: str, new_value: Any):
        self.arguments[name]['optional'][argument_keyword] = new_value

    def change_argument_default(self, name: str, new_value: Any):
        self.arguments[name]['optional']['default'] = new_value

    def change_argument_help(self, name: str, new_help: Any):
        self.arguments[name]['optional']['help'] = new_help

    def initialize_arguments(self) -> argparse.ArgumentParser:
        va_parser = argparse.ArgumentParser(
            description=self.description + ' Version ' + self.version,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        for argument_name, argument_dict in self.arguments.items():
            va_parser.add_argument(*argument_dict['positional'], **argument_dict['optional'])

        return va_parser


def add_va_arguments(va_parser: VA_Parser) -> VA_Parser:
    # Number (in Hz) determining the update rate for the virtual accelerator.
    va_parser.add_argument('--refresh_rate', default=1.0, type=float,
                           help='Rate (in Hz) at which the virtual accelerator updates.')
    va_parser.add_argument('--sync_time', dest='sync_time', action='store_true',
                           help="Synchronize timestamps for server parameters.")

    # Desired amount of output.
    va_parser.add_argument('--debug', dest='debug', action='store_true',
                           help="Some debug info will be printed.")
    va_parser.add_argument('--production', dest='debug', action='store_false',
                           help="DEFAULT: No additional info printed.")

    va_parser.add_argument('--print_settings', dest='print_settings', action='store_true',
                           help="Will only print setting parameters. Will NOT run the virtual accelerator.")
    va_parser.add_argument('--print_server_keys', dest='print_keys', action='store_true',
                           help="Will print all server keys. Will NOT run the virtual accelerator.")

    return va_parser


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
    elif args.print_keys:
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

        server_parameters = server.get_parameters()
        beam_line.update_settings_from_server(server_parameters)
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
