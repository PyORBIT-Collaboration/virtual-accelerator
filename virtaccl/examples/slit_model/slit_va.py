# Channel access server used to generate fake PV signals for one slit and one FC
import sys
from typing import Dict, Any

from virtaccl.EPICS_Server.ca_server import EPICS_Server
from virtaccl.beam_line import Device, AbsNoise, BeamLine
from virtaccl.model import Model
from virtaccl.site.SNS_Linac.virtual_devices import WireScanner
from scipy.stats import norm

from virtaccl.virtual_accelerator import virtual_accelerator

SLIT_NAME = 'slit'
SLIT_POSITION = 'slit_position'

FC_NAME = 'FC'


class FC(Device):
    current_pv = 'charge'  # [mA]

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Creates flat noise for associated PVs.
        amp_noise = AbsNoise(noise=1e-4)
        self.register_measurement(FC.current_pv, noise=amp_noise)


class Slit(WireScanner):
    def __init__(self, name: str):
        super().__init__(name)

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        return {self.name: {SLIT_POSITION: self.get_wire_position()}}

    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        pass


class SlitModel(Model):

    def __init__(self):
        super().__init__()
        self._current_slit_position = - 100
        self._current_FC_charge = 0

    def get_measurements(self) -> dict[str, dict[str,]]:
        return {FC_NAME: {FC.current_pv: self._current_FC_charge}}

    def update_optics(self, changed_optics: dict[str, dict[str,]]) -> None:
        self._current_slit_position = changed_optics[SLIT_NAME][SLIT_POSITION]

    def track(self):
        slw = 1.0
        wedge = 20.0
        sigma = 2.0
        full_charge = 10.0

        # x is position of the screen's edge
        # the slit is wedge (mm) from the edge
        x = self._current_slit_position * 1000
        xl = x - slw / 2 - wedge
        xu = x + slw / 2 - wedge
        self._current_FC_charge = full_charge * (
                1.0 - norm.cdf(x / sigma) + norm.cdf(xu / sigma) - norm.cdf(xl / sigma))


def main():
    model = SlitModel()
    server = EPICS_Server()
    beam_line = BeamLine()

    slit = Slit(SLIT_NAME)
    beam_line.add_device(slit)
    beam_line.add_device(FC(FC_NAME))

    virtual_accelerator(model, beam_line, server)


if __name__ == '__main__':
    main()
