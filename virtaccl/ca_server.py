import signal
from threading import Event, Thread
from datetime import datetime
from typing import Dict, Any
from time import sleep

from math import floor

from pcaspy import Driver
from pcaspy.cas import epicsTimeStamp
from pcaspy import SimpleServer
from virtaccl.virtual_devices import Device


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


class Server:
    def __init__(self, prefix=''):
        self.prefix = prefix
        self.driver = None
        self.pv_db = dict()
        self.devices: Dict[str, Device] = {}

    def _CA_events(self, server):
        while True:
            server.process(0.1)

    def setParam(self, reason, value, timestamp=None):
        self.driver.setParam(reason, value, timestamp)

    def getParam(self, reason):
        return self.driver.getParam(reason)

    def update(self):
        self.driver.updatePVs()

    def add_device(self, device: Device):
        pvs = device.build_db()
        def_dict = {}
        for reason, param in pvs.items():
            param.server = self
            def_dict[reason] = param.get_definition()
        self.pv_db = self.pv_db | def_dict

        device.server = self
        self.devices[device.name] = device
        return device

    def start(self):
        server = SimpleServer()
        server.createPV(self.prefix, self.pv_db)
        self.driver = TDriver()
        tid = Thread(target=self._CA_events, args=(server,))

        # So it will die after main thread is gone
        tid.setDaemon(True)
        tid.start()

        for device_name, device in self.devices.items():
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
        for device_name, device in self.devices.items():
            result = result | device.get_settings()
        return result

    def update_measurements(self, new_measurements: Dict[str, Dict[str, Any]]):
        for device_name, device in self.devices.items():
            model_names = device.model_names
            device_measurements = {key: value for key, value in new_measurements.items() if key in model_names}
            device.update_measurements(device_measurements)

    def update_readbacks(self):
        for device_name, device in self.devices.items():
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
