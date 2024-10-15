from threading import Thread
from datetime import datetime
from time import sleep

from math import floor
from typing import Any

from pcaspy import Driver
from pcaspy.cas import epicsTimeStamp
from pcaspy import SimpleServer

from virtaccl.server import Server


def to_epics_timestamp(t: datetime):
    if t is None:
        return None

    epics_tst = t.timestamp() - 631152000.0
    tst = epicsTimeStamp()
    tst.secPastEpoch = int(floor(epics_tst))
    tst.nsec = int((epics_tst % 1) * 1_000_000_000)

    return tst


def epics_now(timestamp: datetime):
    return to_epics_timestamp(timestamp)


class TDriver(Driver):
    def __init__(self):
        Driver.__init__(self)

    def setParam(self, reason, value, timestamp=None):
        super().setParam(reason, value)
        if timestamp is not None:
            self.pvDB[reason].time = timestamp


class EPICS_Server(Server):
    def __init__(self, prefix='', process_delay=0.1):
        super().__init__()
        self.prefix = prefix
        self.driver = None
        self.process_delay = process_delay

    def _CA_events(self, server):
        while True:
            server.process(self.process_delay)

    def set_parameter(self, reason: str, value: Any, timestamp: datetime = None):
        if timestamp is not None:
            timestamp = epics_now(timestamp)
        self.driver.setParam(reason, value, timestamp)

    def get_parameter(self, reason: str) -> Any:
        return self.driver.getParam(reason)

    def update(self):
        self.driver.updatePVs()

    def start(self):
        server = SimpleServer()
        server.createPV(self.prefix, self.parameter_db)
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
        return 'Following PVs are registered:\n' + '\n'.join([f'{self.prefix}{k}' for k in self.parameter_db.keys()])

    def run(self):
        pass
