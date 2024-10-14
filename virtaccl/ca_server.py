import signal
import sys
from threading import Event, Thread
from datetime import datetime
from typing import Dict, Any, List
from time import sleep

from math import floor

from pcaspy import Driver
from pcaspy.cas import epicsTimeStamp
from pcaspy import SimpleServer


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
    def __init__(self, prefix='', process_delay=0.1):
        self.prefix = prefix
        self.driver = None
        self.pv_db = {}
        self.process_delay = process_delay

    def _CA_events(self, server):
        while True:
            server.process(self.process_delay)

    def setParam(self, reason, value, timestamp=None):
        self.driver.setParam(reason, value, timestamp)

    def getParam(self, reason):
        return self.driver.getParam(reason)

    def update(self):
        self.driver.updatePVs()

    def add_pvs(self, pvs: Dict[str, Dict[str, Any]]):
        self.pv_db |= pvs

    def start(self):
        server = SimpleServer()
        server.createPV(self.prefix, self.pv_db)
        self.driver = TDriver()
        tid = Thread(target=self._CA_events, args=(server,))

        # So it will die after main thread is gone
        tid.setDaemon(True)
        tid.start()
        self.run()

    def stop(self):
        # it's unclear how to gracefully stop the server
        sleep(1)

    def __str__(self):
        return 'Following PVs are registered:\n' + '\n'.join([f'{self.prefix}{k}' for k in self.pv_db])

    def get_pvs(self) -> Dict[str, Any]:
        return {k: self.getParam(k) for k in self.pv_db.keys()}

    def set_pvs(self, values: Dict[str, Any], timestamp=None):
        for k, v in values.items():
            self.setParam(k, v, timestamp)

    def get_pv_names(self) -> List[str]:
        pvs = list(self.pv_db.keys())
        return pvs

    def run(self):
        pass


def not_ctrlc():
    return not CtrlC.event.is_set()


class CtrlC:
    event = Event()
    signal.signal(signal.SIGINT, lambda _1, _2: CtrlC.event.set())
