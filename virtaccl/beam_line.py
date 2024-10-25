import math

import numpy as np
from numpy.random import random_sample
from typing import Optional, Union, List, Dict, Any, Set


class Transform:

    def real(self, x):
        return x

    def raw(self, x):
        return x


class NormalizePeak(Transform):
    def __init__(self, max_value=1, reason_rb=None):
        self._max = max_value
        self._reason_rb = reason_rb

    def raw(self, x):
        sig_max = np.amax(x)
        if sig_max > 0:
            coeff = self._max / np.amax(x)
        else:
            coeff = 0
        return x * coeff

    def calculate_rb(self, x):
        return self.raw(x)


class LinearT(Transform):
    def __init__(self, offset=0.0, scaler=1.0, reason_rb=None):
        self._offset = offset
        self._scaler = scaler
        self._reason_rb = reason_rb

    def real(self, x):
        return x / self._scaler - self._offset

    def raw(self, x):
        return (x + self._offset) * self._scaler

    def calculate_rb(self, x):
        return self.raw(x)


class PhaseT(LinearT):
    def __init__(self, noise=0.0, **kw):
        super().__init__(**kw)
        self.noise = noise

    @staticmethod
    def wrap_phase(deg):
        x = deg % 360
        return x - 360 if x > 180 else x

    def raw(self, x):
        return self.wrap_phase(LinearT.raw(self, x))

    def real(self, x):
        return self.wrap_phase(LinearT.real(self, x))


class LinearTInv(Transform):
    def __init__(self, offset=0.0, scaler=1.0, reason_rb=None):
        self._offset = offset
        self._scaler = scaler
        self._reason_rb = reason_rb

    def real(self, x):
        return (x - self._offset) / self._scaler

    def raw(self, x):
        return (x * self._scaler) + self._offset

    def calculate_rb(self, x):
        return self.raw(x)


class PhaseTInv(LinearTInv):
    def __init__(self, noise=0.0, **kw):
        super().__init__(**kw)
        self.noise = noise

    @staticmethod
    def wrap_phase_deg(deg):
        x = deg % 360
        return x - 360 if x > 180 else x

    @staticmethod
    def wrap_phase_rad(rad):
        x = rad % (2 * math.pi)
        return x - 2 * math.pi if x > math.pi else x

    def raw(self, x):
        return self.wrap_phase_deg(LinearTInv.raw(self, x))

    def real(self, x):
        return self.wrap_phase_rad(LinearTInv.real(self, x))


class Noise:
    def add_noise(self, x):
        return x


class AbsNoise(Noise):
    def __init__(self, noise=0.0, shape=1, **kw):
        super().__init__(**kw)
        self.noise = noise
        self.shape = shape

    def add_noise(self, x):
        if self.shape == 1:
            noise = self.noise * (random_sample() * 2 - 1)
        else:
            noise = self.noise * (random_sample(self.shape) * 2 - 1)
        return x + noise


class PosNoise(Noise):
    def __init__(self, noise=0.0, count=1, **kw):
        super().__init__(**kw)
        self.noise = noise
        self.count = count

    def add_noise(self, x):
        if self.count == 1:
            noise = self.noise * random_sample()
        else:
            noise = self.noise * random_sample(self.count)
        return x + noise


class Parameter:
    def __init__(self, reason: str, definition=None, default=0, setting_reason=None, transform=None, noise=None,
                 server_key_override: str = None):
        self.reason = reason
        self.definition = definition
        self.default_value = default
        self.setting_reason = setting_reason
        self.transform, self.noise = self._default(transform, noise)
        self.server_key = server_key_override

        self.current_value = default

    @classmethod
    def _default(cls, transform, noise):
        # default transformation is identity
        transform = transform if transform else Transform()
        # default noise is zero
        noise = noise if noise else Noise()
        return transform, noise

    def get_server_key(self) -> str:
        return self.server_key

    def set_server_key(self, server_key: str):
        self.server_key = server_key

    def get_definition(self):
        return self.definition

    def get_default(self):
        return self.default_value

    def set_default_value(self, new_default):
        self.default_value = new_default

    def set_value(self, new_value):
        self.current_value = new_value

    def get_value(self):
        return self.current_value

    def get_value_for_server(self):
        virtual_value = self.noise.add_noise(self.transform.raw(self.current_value))
        return virtual_value

    def set_value_from_server(self, new_value):
        self.current_value = self.transform.real(new_value)


class Device:

    def __init__(self, server_name: str, model_name: Optional[Union[str, List[str]]] = None,
                 connected_device: Optional[Union['Device', List['Device']]] = None):
        self.name = server_name

        if model_name is None:
            self.model_names = [server_name]
        elif not isinstance(model_name, list):
            self.model_names = [model_name]
        else:
            self.model_names = model_name

        if connected_device is None:
            connected_device = []
        elif not isinstance(connected_device, list):
            connected_device = [connected_device]
        else:
            connected_device = connected_device

        self.connected_devices = {}
        for device in connected_device:
            self.connected_devices[device] = device

        # dictionary stores (definition, default, transform, noise)
        self.parameters: Dict[str, Parameter] = {}

        self.sever_changes: Set[str] = set()

        self.settings: Set[str] = set()
        self.measurements: Set[str] = set()
        self.readbacks: Set[str] = set()

    def register_parameter(self, reason: str, definition=None, default=0, setting_reason: str = None, transform=None,
                           noise=None, server_key_override: str = None) -> Parameter:
        if definition is None:
            definition = {}
        param = Parameter(reason, definition, default, setting_reason, transform, noise, server_key_override)
        self.parameters[reason] = param
        return param

    def register_measurement(self, reason: str, definition=None, transform=None, noise=None,
                             server_key_override: str = None) -> Parameter:
        param = self.register_parameter(reason, definition, transform=transform, noise=noise,
                                        server_key_override=server_key_override)
        self.measurements.add(reason)
        return param

    def register_setting(self, reason: str, definition=None, default=0, transform=None, noise=None,
                         server_key_override: str = None) -> Parameter:
        param = self.register_parameter(reason, definition, default=default, transform=transform, noise=noise,
                                        server_key_override=server_key_override)
        self.settings.add(reason)
        return param

    def register_readback(self, reason: str, setting: str = None, definition=None, transform=None, noise=None,
                          server_key_override: str = None) -> Parameter:
        rb_def = {}
        if definition is not None:
            rb_def = definition
        elif setting is not None and setting in self.settings:
            rb_def = self.get_parameter(setting).get_definition()
        param = self.register_parameter(reason, definition=rb_def, setting_reason=setting, transform=transform,
                                        noise=noise, server_key_override=server_key_override)
        self.readbacks.add(reason)
        return param

    def get_parameter_value(self, reason):
        return self.parameters[reason].get_value()

    def set_parameter_value(self, reason, new_value):
        self.parameters[reason].set_value(new_value)

    def get_parameter(self, reason) -> Parameter:
        return self.parameters[reason]

    def get_parameters(self) -> Dict[str, Parameter]:
        return self.parameters

    def update_setting(self, reason: str, new_value=None):
        param = self.get_parameter(reason)
        param.set_value_from_server(new_value)

    def update_settings(self, new_settings: Dict[str, Any]):
        for reason in self.settings:
            if reason in new_settings:
                self.update_setting(reason, new_settings[reason])

    def server_setting_override(self, reason: str, new_value=None):
        self.set_parameter_value(reason, new_value)
        self.sever_changes.add(reason)

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        return {}

    def update_measurement(self, reason: str, value=None):
        self.set_parameter_value(reason, value)
        self.sever_changes.add(reason)

    def update_measurements(self, new_measurements: Dict[str, Dict[str, Any]] = None):
        for model_name, measurement in new_measurements.items():
            if model_name in self.model_names:
                for reason, value in measurement.items():
                    self.update_measurement(reason, value)

    def update_readback(self, reason, value=None):
        if value is None:
            setting_reason = self.parameters[reason].setting_reason
            if setting_reason is not None:
                setting_reason = self.parameters[reason].setting_reason
                value = self.parameters[setting_reason].get_value()
        self.set_parameter_value(reason, value)
        self.sever_changes.add(reason)

    def update_readbacks(self):
        for reason in self.readbacks:
            self.update_readback(reason)

    def clear_changes(self):
        self.sever_changes.clear()

    def get_changed_parameters(self) -> Dict[str, Any]:
        changes_dict = {}
        for reason in self.sever_changes:
            param = self.get_parameter(reason)
            changes_dict[param.get_server_key()] = param.get_value_for_server()
        return changes_dict

    def reset(self):
        for reason in self.settings:
            param = self.parameters[reason]
            param.set_value(param.get_default())

    def build_db(self) -> Dict[str, Parameter]:
        parameter_db = {v.get_server_key(): v for k, v in self.parameters.items()}
        return parameter_db


class BeamLine:

    def __init__(self, server_key_joiner: str = ':'):
        self.devices: Dict[str, Device] = {}
        self.server_key_joiner = server_key_joiner

        self.setting_keys = set()
        self.measurement_keys = set()
        self.readback_keys = set()

    def add_device(self, device: Device) -> Device:
        self.devices[device.name] = device
        for reason, parameter in device.get_parameters().items():
            server_key = parameter.get_server_key()
            if server_key is None:
                server_key = device.name + self.server_key_joiner + reason
                parameter.set_server_key(server_key)

            if reason in device.settings:
                self.setting_keys.add(server_key)
            elif reason in device.measurements:
                self.measurement_keys.add(server_key)
            elif reason in device.readbacks:
                self.readback_keys.add(server_key)
        return device

    def get_devices(self) -> Dict[str, Device]:
        return self.devices

    def get_device(self, device_name: str) -> Device:
        return self.devices[device_name]

    def get_server_parameter_definitions(self) -> Dict[str, Dict[str, Any]]:
        def_dict = {}
        for device_name, device in self.get_devices().items():
            parameters = device.build_db()
            for reason, param in parameters.items():
                def_dict[reason] = param.get_definition() | {'value': param.get_value_for_server()}
        return def_dict

    def reset_devices(self):
        for device_name, device in self.devices.items():
            device.reset()

    def update_settings_from_server(self, server_parameters: Dict[str, Any]):
        for device_name, device in self.devices.items():
            device_settings = {}
            for reason in device.settings:
                parameter = device.get_parameter(reason)
                param_key = parameter.get_server_key()
                if param_key in server_parameters:
                    device_settings |= {reason: server_parameters[param_key]}
            device.update_settings(device_settings)

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        optics_dict = {}
        for device_name, device in self.devices.items():
            optics_dict |= device.get_model_optics()
        return optics_dict

    def update_measurements_from_model(self, new_measurements: Dict[str, Dict[str, Any]]):
        for device_name, device in self.devices.items():
            model_names = device.model_names
            device_measurements = {key: value for key, value in new_measurements.items() if key in model_names}
            device.update_measurements(device_measurements)

    def update_readbacks(self):
        for device_name, device in self.devices.items():
            device.update_readbacks()

    def get_parameters_for_server(self) -> Dict[str, Any]:
        sever_dict = {}
        for device_name, device in self.devices.items():
            sever_dict |= device.get_changed_parameters()
            device.clear_changes()
        return sever_dict

    def get_setting_keys(self) -> List[str]:
        setting_keys = []
        for device_name, device in self.devices.items():
            for reason in device.settings:
                setting_keys.append(device.get_parameter(reason).get_server_key())
        return setting_keys

    def get_measurement_keys(self) -> List[str]:
        measurement_keys = []
        for device_name, device in self.devices.items():
            for reason in device.measurements:
                measurement_keys.append(device.get_parameter(reason).get_server_key())
        return measurement_keys

    def get_readback_keys(self) -> List[str]:
        readback_keys = []
        for device_name, device in self.devices.items():
            for reason in device.readbacks:
                readback_keys.append(device.get_parameter(reason).get_server_key())
        return readback_keys
