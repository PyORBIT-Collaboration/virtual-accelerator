# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import sys

sys.path.append('../../../../SNS_CA_Server/caserver')
from time import sleep
from castst import Server, epics_now, not_ctrlc
import argparse
from devices import BLM, BCM, BPM, PBPM, Magnet, Cavity, genPV

# update rate in Hz
REP_RATE = 5.0

# A function to parse BLMs and attributes from file
# Returns a list of lines (split into sublists)

def read_file(file):
    with open(file, "r") as f:
        file = f.read().splitlines()
        # filter out comments while reading the file
        parameters = [i.split() for i in file if not i.strip().startswith('#')]
        return parameters


if __name__ == '__main__':
    # Set a default prefix if unspecified at server initialization
    parser = argparse.ArgumentParser(description='Run CA server')
    parser.add_argument('--prefix', '-p', default='test', type=str, help='Prefix for PVs')
    parser.add_argument('--file', '-f', default='server_devices.txt', type=str,
                        help='Pathname of pv file. Relative to Server/')

    args = parser.parse_args()
    prefix = args.prefix + ':'
    print(f'Using prefix: {args.prefix}.')

    server = Server(prefix)
    all_devices = []

    # Dynamically create device objects and add them to the server. Append to list for iterability
    for parameters in read_file(args.file):
        all_devices.append(server.add_device(globals()[parameters[0]](*parameters[1:])))

    server.start()
    print(f"Server started.")
    print(f"Devices in use: {[p.name for p in all_devices]}")

    blms = [item for item in server.devices if type(item).__name__ == 'BLM']
    cavs = [item for item in server.devices if type(item).__name__ == 'Cavity']
    mags = [item for item in server.devices if type(item).__name__ == 'Magnet']
    diag_devices = set(all_devices) - set(blms) - set(cavs) - set(mags)

# Our new data acquisition routine
    while not_ctrlc():
        now = epics_now()

        server.update()
        sleep(1.0 / REP_RATE)

    print('Exiting. Thank you for using our epics server!')
