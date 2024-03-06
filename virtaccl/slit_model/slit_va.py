# Channel access server used to generate fake PV signals for one slit and one FC

import time
import argparse
from virtaccl.ca_server import Server, epics_now, not_ctrlc
from virtaccl.virtual_devices import Device, AbsNoise
from virtaccl.model import Model
from virtaccl.PyORBIT_Model.virtual_devices import WireScanner
from scipy.stats import norm

SLIT_NAME = 'slit'
FC_NAME = 'FC'


class FC(Device):
    current_pv = 'charge'  # [mA]

    def __init__(self, name: str, model_name: str = None, phase_offset=0):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Creates flat noise for associated PVs.
        amp_noise = AbsNoise(noise=1e-4)
        self.register_measurement(FC.current_pv, noise=amp_noise)


class SlitModel(Model):

    def __init__(self):
        self._current_slit_position = - 100
        self._current_FC_charge = 0

    def get_measurements(self) -> dict[str, dict[str,]]:
        return {FC_NAME: {FC.current_pv: self._current_FC_charge}}

    def update_optics(self, changed_optics: dict[str, dict[str,]]) -> None:
        self._current_slit_position = changed_optics['slit_position']

    def track(self):
        slw = 1.0
        wedge = 20.0
        sigma = 2.0
        full_charge = 10.0

        # x is position of the screen's edge
        # the slit is wedge (mm) from the edge
        x = self._current_slit_position
        xl = x - slw / 2 - wedge
        xu = x + slw / 2 - wedge
        self._current_FC_charge = full_charge * (
                    1.0 - norm.cdf(x / sigma) + norm.cdf(xu / sigma) - norm.cdf(xl / sigma))


def main():
    parser = argparse.ArgumentParser(description='Run CA server to run simple slit/FC accelerator')

    # Number (in Hz) determining the update rate for the virtual accelerator.
    parser.add_argument('--refresh_rate', default=1.0, type=float,
                        help='Rate (in Hz) at which the virtual accelerator updates.')

    # Desired amount of output.
    parser.add_argument('--debug', dest='debug', action='store_true', help="Some debug info will be printed.")

    args = parser.parse_args()
    debug = args.debug
    update_period = 1 / args.refresh_rate

    model = SlitModel()
    server = Server()
    ws = WireScanner(SLIT_NAME)
    server.add_device(ws)
    server.add_device(FC(FC_NAME))

    if debug:
        print(server)
    server.start()
    print(f"Server started.")

    while not_ctrlc():
        loop_start_time = time.time()

        now = epics_now()

        new_params = server.get_settings()
        server.update_readbacks()

        # this is a very dirty workaround
        # needed because the model depends on device's readback (not parameter)
        p = ws.get_readback('Position')
        model.update_optics(new_params | {'slit_position': p})

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


if __name__ == '__main__':
    main()
