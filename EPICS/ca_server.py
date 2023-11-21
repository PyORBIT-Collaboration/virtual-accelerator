import math
import signal
from threading import Event, Thread
from datetime import datetime
from time import sleep

from math import floor
from pcaspy import Driver
from pcaspy.cas import epicsTimeStamp
from pcaspy import SimpleServer

from numpy.random import random_sample


def to_epics_timestamp(t: datetime):
    if t is None:
        return None

    epics_tst = t.timestamp() - 631152000.0
    tst = epicsTimeStamp()
    tst.secPastEpoch = int(floor(epics_tst))
    tst.nsec = int((epics_tst % 1) * 1_000_000_000)

    return tst


def epics_now():
    return to_epics_timestamp(datetime.now())


class TDriver(Driver):
    def __init__(self):
        Driver.__init__(self)

    def setParam(self, reason, value, timestamp=None):
        super().setParam(reason, value)
        if timestamp is not None:
            self.pvDB[reason].time = timestamp


class Transform:

    def real(self, x):
        return x

    def raw(self, x):
        return x


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
    def __init__(self, noise=0.0, **kw):
        super().__init__(**kw)
        self.noise = noise

    def add_noise(self, x):
        return x + self.noise * (random_sample() - 0.5)


class Device:

    def __init__(self, pv_name, model_name=None):
        self.name = pv_name
        if model_name is None:
            self.model_name = pv_name
        else:
            self.model_name = model_name

        self.server = None
        self.__db_dictionary__ = {}

        # dictionary stores (definition, default, reason_rb, transform, noise)
        self.settings = {}

        # dictionary stores (definition, transform, noise)
        self.measurements = {}

    @classmethod
    def _default(cls, transform, noise):
        # default transformation is identity
        transform = transform if transform else Transform()
        # default noise is zero
        noise = noise if noise else Noise()
        return transform, noise

    def register_measurement(self, reason, definition=None, transform=None, noise=None):
        t, n = self._default(transform, noise)
        self.measurements[reason] = (definition if definition else {}), t, n

    def register_setting(self, reason, definition=None, default=0, transform=None, noise=None, reason_rb=None):
        t, n = self._default(transform, noise)
        self.settings[reason] = (definition if definition else {}), default, reason_rb, t, n

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        return transform.real(self.getParam(reason))

    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_input_dict = self.get_setting(setting)
            params_dict = params_dict | param_input_dict
        return params_dict

    def update_measurement(self, reason, value):
        *_, transform, noise = self.measurements[reason]
        self.setParam(reason, noise.add_noise(transform.raw(value)))

    def update_readback(self, reason):
        value = self.get_setting(reason)
        *_, reason_rb, transform, noise = self.settings[reason]
        self.setParam(reason_rb, transform.raw(noise.add_noise(value)))

    def update_readbacks(self):
        # s[2] is reason_rb
        [self.update_readback(k) for k, s in self.settings.items() if s[2]]

    def reset(self):
        for k, v in self.settings.items():
            self.setParam(k, v[1])

    def setParam(self, reason, value, timestamp=None):
        if self.server:
            self.server.setParam(f'{self.name}:{reason}', value, timestamp)

    def getParam(self, reason):
        if self.server:
            return self.server.getParam(f'{self.name}:{reason}')
        return None

    def build_db(self):
        setting_pvs = {k: v[0] for k, v in self.settings.items()}
        readback_pvs = {v[2]: v[0] for k, v in self.settings.items() if v[2]}
        measurement_pvs = {k: v[0] for k, v in self.measurements.items()}
        all_pvs = setting_pvs | readback_pvs | measurement_pvs
        full_db = {f'{self.name}:{k}': v for k, v in all_pvs.items()}

        measurement_map = {f'{self.name}:{k}': (self, k) for k in measurement_pvs}
        return full_db, measurement_map


class Server:
    def __init__(self, prefix=''):
        self.prefix = prefix
        self.driver = None
        self.pv_db = dict()
        self.measurement_map = {}
        self.devices = []

        self.model_map = {}

    def _CA_events(self, server):
        while True:
            server.process(0.1)

    def setParam(self, reason, value, timestamp=None):
        self.driver.setParam(reason, value, timestamp)

    def getParam(self, reason):
        return self.driver.getParam(reason)

    def update(self):
        self.driver.updatePVs()

    def add_device(self, device):
        pvs, mmap = device.build_db()
        self.pv_db = self.pv_db | pvs
        self.measurement_map = self.measurement_map | mmap

        device_name = device.name
        model_name = device.model_name
        self.model_map = self.model_map | {device_name: model_name}

        device.server = self
        self.devices.append(device)
        return device

    def start(self):
        server = SimpleServer()
        server.createPV(self.prefix, self.pv_db)
        self.driver = TDriver()
        tid = Thread(target=self._CA_events, args=(server,))

        # So it will die after main thread is gone
        tid.setDaemon(True)
        tid.start()

        for device in self.devices:
            device.reset()

        self.run()

    def stop(self):
        # it's unclear how to gracefully stop the server
        sleep(1)

    def __str__(self):
        return 'Following PVs are registered:\n' + '\n'.join([f'{self.prefix}{k}' for k in self.pv_db])

    def get_params(self):
        return {k: self.getParam(k) for k in self.pv_db.keys()}

    def get_settings(self):
        result = {}
        for device in self.devices:
            result = result | {device.model_name: device.get_settings()}
        return result

    def update_measurements(self, measurements):
        for device in self.devices:
            device_name = device.name
            model_name = self.model_map[device_name]
            if model_name in measurements:
                model_params = measurements[model_name]
                for model_key, value in model_params.items():
                    device.update_measurement(model_key, value)

    def update_readbacks(self):
        for device in self.devices:
            device.update_readbacks()

    def set_params(self, values: dict, timestamp=None):
        for k, v in values.items():
            self.setParam(k, v, timestamp)

    def run(self):
        pass


def not_ctrlc():
    return not CtrlC.event.is_set()


class CtrlC:
    event = Event()
    signal.signal(signal.SIGINT, lambda _1, _2: CtrlC.event.set())
