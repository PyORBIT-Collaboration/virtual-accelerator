import signal
from threading import Event
from typing import Dict, Any
from datetime import datetime


class Server:
    def __init__(self):
        self.parameter_db = {}

    def add_parameters(self, new_parameters: Dict[str, Dict[str, Any]]):
        for parameter_key, parameter_definitions in new_parameters.items():
            self.add_parameter(parameter_key, parameter_definitions)

    def add_parameter(self, parameter_key: str, parameter_definitions: Dict[str, Any]):
        self.parameter_db |= {parameter_key: parameter_definitions}

    def get_parameters(self) -> Dict[str, Any]:
        return {key: self.get_parameter(key) for key in self.parameter_db.keys()}

    def set_parameters(self, new_values: Dict[str, Any], timestamp: datetime = None):
        for parameter_key, new_value in new_values.items():
            self.set_parameter(parameter_key, new_value, timestamp)

    def get_parameter_keys(self):
        keys = list(self.parameter_db.keys())
        return keys

    def __str__(self):
        return 'Following parameters are registered:\n' + '\n'.join([f'{key}' for key in self.parameter_db.keys()])

    def get_parameter(self, parameter_key: str):
        return self.parameter_db[parameter_key]['value']

    def set_parameter(self, parameter_key: str, new_value, timestamp: datetime = None):
        self.parameter_db[parameter_key]['value'] = new_value

    def update(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def run(self):
        pass


def not_ctrlc():
    return not CtrlC.event.is_set()


class CtrlC:
    event = Event()
    signal.signal(signal.SIGINT, lambda _1, _2: CtrlC.event.set())
