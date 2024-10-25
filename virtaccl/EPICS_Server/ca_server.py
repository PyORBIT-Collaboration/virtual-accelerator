import os
import sys
from threading import Thread
from datetime import datetime
from time import sleep

from math import floor
from typing import Any, Dict

from pcaspy import Driver
from pcaspy.cas import epicsTimeStamp
from pcaspy import SimpleServer

from virtaccl.server import Server
from virtaccl.virtual_accelerator import VA_Parser


def add_epics_arguments(va_parser: VA_Parser) -> VA_Parser:
    # Number (in seconds) that determine some delay parameter in the server. Not exactly sure how it works, so use at
    # your own risk.
    va_parser.add_server_argument('--ca_proc', default=0.1, type=float,
                                  help='Number (in seconds) that determine some delay parameter in the server. Not '
                                       'exactly sure how it works, so use at your own risk.')

    va_parser.add_server_argument('--print_pvs', dest='print_pvs', action='store_true',
                                  help="Will print all server PVs. Will NOT run the virtual accelerator.")
    return va_parser


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
    def __init__(self, prefix='', process_delay=0.1, print_pvs=False):
        super().__init__()
        self.prefix = prefix
        self.driver = None
        self.process_delay = process_delay
        self.print_pvs = print_pvs
        self.start_flag = False

        os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '10000000'

    def _CA_events(self, server):
        while True:
            server.process(self.process_delay)

    def add_parameters(self, new_parameters: Dict[str, Dict[str, Any]]):
        super().add_parameters(new_parameters)
        if self.print_pvs:
            for key in self.get_parameter_keys():
                print(key)
            sys.exit()

    def set_parameter(self, reason: str, value: Any, timestamp: datetime = None):
        super().set_parameter(reason, value, timestamp)
        if timestamp is not None:
            timestamp = epics_now(timestamp)
        if self.start_flag:
            self.driver.setParam(reason, value, timestamp)

    def get_parameter(self, reason: str) -> Any:
        if self.start_flag:
            value = self.driver.getParam(reason)
        else:
            value = super().get_parameter(reason)
        return value

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
        self.start_flag = True

    def stop(self):
        # it's unclear how to gracefully stop the server
        self.start_flag = False
        sleep(1)

    def __str__(self):
        return 'Following PVs are registered:\n' + '\n'.join([f'{self.prefix}{k}' for k in self.parameter_db.keys()])

    def run(self):
        pass
