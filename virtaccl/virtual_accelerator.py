# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import math
import os
import sys
import time
import argparse
from pathlib import Path
from importlib.metadata import version

from orbit.lattice import AccNode
from orbit.py_linac.lattice import LinacPhaseApertureNode
from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice

from virtaccl.PyORBIT_Model.pyorbit_child_nodes import BPMclass, WSclass

from orbit.core.bunch import Bunch
from orbit.core.linac import BaseRfGap

from virtaccl.ca_server import Server, epics_now, not_ctrlc
from virtaccl.model import Model

from virtaccl.site.SNS_Linac.orbit_model.sns_linac_lattice_factory import PyORBIT_Lattice_Factory
from virtaccl.site.SNS_Linac.virtual_devices import BPM, Quadrupole, Corrector, P_BPM, \
    WireScanner, Quadrupole_Power_Supply, Corrector_Power_Supply, Bend_Power_Supply, Bend, Quadrupole_Power_Shunt
from virtaccl.site.SNS_Linac.virtual_devices_SNS import SNS_Dummy_BCM, SNS_Cavity, SNS_Dummy_ICS

from virtaccl.PyORBIT_Model.pyorbit_lattice_controller import OrbitModel


def va_parser():
    va_version = version('virtaccl')
    parser = argparse.ArgumentParser(
        description='Run the Virac virtual accelerator server. Version ' + va_version)
    # parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates (default=1.0).')

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


def virtual_accelerator(model: Model, server: Server, arguments: argparse.ArgumentParser):
    os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '10000000'

    args = arguments.parse_args()
    debug = args.debug

    update_period = 1 / args.refresh_rate

    if args.print_settings:
        for setting in server.get_setting_pvs():
            print(setting)
        sys.exit()
    elif args.print_pvs:
        for pv in server.get_pvs():
            print(pv)
        sys.exit()

    delay = args.ca_proc
    server.process_delay = delay
    server.start()
    print(f"Server started.")

    # Our new data acquisition routine
    while not_ctrlc():
        loop_start_time = time.time()

        now = epics_now()

        new_params = server.get_settings()
        server.update_readbacks()
        model.update_optics(new_params)
        model.track()
        new_measurements = model.get_measurements()
        server.update_measurements(new_measurements)

        server.update()

        loop_time_taken = time.time() - loop_start_time
        sleep_time = update_period - loop_time_taken
        if sleep_time < 0.0:
            print('Warning: Update took longer than refresh rate.')
        else:
            time.sleep(sleep_time)

    print('Exiting. Thank you for using our virtual accelerator!')
