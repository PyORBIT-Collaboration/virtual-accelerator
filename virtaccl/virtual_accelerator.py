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
        self._va_arguments_: Dict[str, Dict[str, Any]] = {}
        self.model_arguments: Dict[str, Dict[str, Any]] = {}
        self.server_arguments: Dict[str, Dict[str, Any]] = {}
        self.custom_arguments: Dict[str, Dict[str, Any]] = {}
        self.__all_arguments__ = {'va': self._va_arguments_, 'model': self.model_arguments,
                                  'server': self.server_arguments, 'custom': self.custom_arguments}
        self.__all_argument_keys__ = set()

        self.version = version('virtaccl')
        self.description = 'Run the Virac virtual accelerator server.'

        add_va_arguments(self)

    def __find_argument_dict__(self, name) -> Dict[str, Dict[str, Any]]:
        for argument_group, arguments in self.__all_arguments__.items():
            if name in arguments:
                return arguments

    def set_description(self, new_description: str):
        self.description = new_description

    def add_argument(self, *args, **kwargs):
        arg_key = args[0]
        if arg_key in self.__all_argument_keys__:
            print(f'Warning: Argument name "{arg_key}" already exists. Argument not added.')
        else:
            self.custom_arguments[arg_key] = {'positional': args, 'optional': kwargs}
            self.__all_argument_keys__.add(arg_key)

    def add_va_argument(self, *args, **kwargs):
        arg_key = args[0]
        if arg_key in self.__all_argument_keys__:
            print(f'Warning: Argument name "{arg_key}" already exists. Argument not added.')
        else:
            self._va_arguments_[arg_key] = {'positional': args, 'optional': kwargs}
            self.__all_argument_keys__.add(arg_key)

    def add_model_argument(self, *args, **kwargs):
        arg_key = args[0]
        if arg_key in self.__all_argument_keys__:
            print(f'Warning: Argument name "{arg_key}" already exists. Argument not added.')
        else:
            self.custom_arguments[arg_key] = {'positional': args, 'optional': kwargs}
            self.__all_argument_keys__.add(arg_key)

    def add_server_argument(self, *args, **kwargs):
        arg_key = args[0]
        if arg_key in self.__all_argument_keys__:
            print(f'Warning: Argument name "{arg_key}" already exists. Argument not added.')
        else:
            self.custom_arguments[arg_key] = {'positional': args, 'optional': kwargs}
            self.__all_argument_keys__.add(arg_key)

    def remove_argument(self, name: str):
        if name not in self.__all_argument_keys__:
            print(f'Warning: Argument name "{name}" was not found.')
        else:
            arguments = self.__find_argument_dict__(name)
            del arguments[name]
            self.__all_argument_keys__.remove(name)

    def edit_argument(self, name: str, new_options: Dict[str, Any]):
        if name not in self.__all_argument_keys__:
            print(f'Warning: Argument name "{name}" was not found.')
        else:
            arguments = self.__find_argument_dict__(name)
            for option_key, new_value in new_options.items():
                arguments[name]['optional'][option_key] = new_value

    def change_argument_default(self, name: str, new_value: Any):
        arguments = self.__find_argument_dict__(name)
        arguments[name]['optional']['default'] = new_value

    def change_argument_help(self, name: str, new_help: Any):
        arguments = self.__find_argument_dict__(name)
        arguments[name]['optional']['help'] = new_help

    def initialize_arguments(self) -> Dict[str, Any]:
        va_parser = argparse.ArgumentParser(
            description=self.description + ' Version ' + self.version,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        for group_key, argument_group in self.__all_arguments__.items():
            for argument_name, argument_dict in argument_group.items():
                va_parser.add_argument(*argument_dict['positional'], **argument_dict['optional'])
        return vars(va_parser.parse_args())


def add_va_arguments(va_parser: VA_Parser) -> VA_Parser:
    # Number (in Hz) determining the update rate for the virtual accelerator.
    va_parser.add_va_argument('--refresh_rate', default=1.0, type=float,
                              help='Rate (in Hz) at which the virtual accelerator updates.')
    va_parser.add_va_argument('--sync_time', dest='sync_time', action='store_true',
                              help="Synchronize timestamps for server parameters.")

    # Desired amount of output.
    va_parser.add_va_argument('--debug', dest='debug', action='store_true',
                              help="Some debug info will be printed.")
    va_parser.add_va_argument('--production', dest='debug', action='store_false',
                              help="DEFAULT: No additional info printed.")
    return va_parser


class VirtualAccelerator:
    def __init__(self, model: Model, beam_line: BeamLine, server: Server, **kwargs):
        if not kwargs:
            kwargs = VA_Parser().initialize_arguments()

        self.debug = kwargs['debug']
        self.sync_time = kwargs['sync_time']
        self.update_period = 1 / kwargs['refresh_rate']

        new_measurements = model.get_measurements()
        beam_line.update_measurements_from_model(new_measurements)
        beam_line.update_readbacks()
        sever_parameters = beam_line.get_server_parameter_definitions()
        server.add_parameters(sever_parameters)
        beam_line.reset_devices()

        self.model = model
        self.beam_line = beam_line
        if self.debug:
            print(server)
        self.server = server

    def set_value(self, server_key: str, new_value):
        self.server.set_parameter(server_key, new_value)
        self.track()

    def set_values(self, new_settings: Dict[str, Any]):
        self.server.set_parameters(new_settings)
        self.track()

    def get_value(self, server_key: str):
        return self.server.get_parameter(server_key)

    def get_values(self) -> Dict[str, Any]:
        return self.server.get_parameters()

    def track(self, timestamp: datetime = None):
        server_parameters = self.server.get_parameters()
        self.beam_line.update_settings_from_server(server_parameters)
        new_optics = self.beam_line.get_model_optics()

        self.model.update_optics(new_optics)
        self.model.track()
        new_measurements = self.model.get_measurements()

        self.beam_line.update_measurements_from_model(new_measurements)
        self.beam_line.update_readbacks()
        new_server_values = self.beam_line.get_parameters_for_server()
        self.server.set_parameters(new_server_values, timestamp=timestamp)

    def start_server(self):
        self.server.start()
        print(f"Server started.")
        now = None

        # Our new data acquisition routine
        while not_ctrlc():
            loop_start_time = time.time()

            if self.sync_time:
                now = datetime.now()
            self.track(timestamp=now)
            self.server.update()

            loop_time_taken = time.time() - loop_start_time
            sleep_time = self.update_period - loop_time_taken
            if sleep_time < 0.0:
                print('Warning: Update took longer than refresh rate.')
            else:
                time.sleep(sleep_time)

        print('Exiting. Thank you for using our virtual accelerator!')
