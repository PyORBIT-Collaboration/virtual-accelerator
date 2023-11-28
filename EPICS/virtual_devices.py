import math
from random import randint, random
from time import sleep
import argparse
from datetime import datetime, timedelta

from ca_server import Server, Device, AbsNoise, LinearT, PhaseT, not_ctrlc, PhaseTInv

PRINT_DELTA = timedelta(seconds=1)
RESET_DELTA = timedelta(seconds=5)


class Quadrupole(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    field_set_pv = 'B_Set'
    field_readback_pv = 'B'

    field_key = 'dB/dr'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_field = initial_dict[Quadrupole.field_key]
        else:
            initial_field = 0.0

        # enum setting with default and no transforms
        self.register_setting(Quadrupole.field_set_pv, default=initial_field, reason_rb=Quadrupole.field_readback_pv)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Quadrupole.field_set_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Quadrupole.field_key] = model_value
        return model_dict

    def update_readback(self, reason):
        value = None
        if reason == Quadrupole.field_set_pv:
            value = self.get_setting(Quadrupole.field_set_pv)[Quadrupole.field_key]

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Corrector(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    field_set_pv = 'B_Set'
    field_readback_pv = 'B'

    field_key = 'B'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_field = initial_dict[Corrector.field_key]
        else:
            initial_field = 0.0

        # enum setting with default and no transforms
        self.register_setting(Corrector.field_set_pv, default=initial_field, reason_rb=self.field_readback_pv)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Corrector.field_set_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Corrector.field_key] = model_value
        return model_dict

    def update_readback(self, reason):
        value = None
        if reason == Corrector.field_set_pv:
            value = self.get_setting(Corrector.field_set_pv)[Corrector.field_key]

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Cavity(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    phase_pv = 'CtlPhaseSet'
    amp_pv = 'CtlAmpSet'
    blank_pv = 'BlnkBeam'

    phase_key = 'phase'
    amp_key = 'amp'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None, phase_offset=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_phase = initial_dict[Cavity.phase_key]
            initial_amp = initial_dict[Cavity.amp_key]
        else:
            initial_phase = 180
            initial_amp = 1.0

        if phase_offset is None:
            phase_offset = (2 * random() - 1) * 180
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)
        initial_phase = offset_transform.raw(initial_phase)

        # enum setting with default and no transforms
        self.register_setting(Cavity.phase_pv, default=initial_phase, transform=offset_transform)
        self.register_setting(Cavity.amp_pv, default=initial_amp)
        self.register_setting(Cavity.blank_pv, default=0.0)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Cavity.phase_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Cavity.phase_key] = model_value

        elif reason == Cavity.amp_pv:
            blank_value = transform.real(self.getParam(Cavity.blank_pv))
            if blank_value == 0:
                model_value = transform.real(self.getParam(reason))
                model_dict[Cavity.amp_key] = model_value
            else:
                model_dict[Cavity.amp_key] = 0.0

        elif reason == Cavity.blank_pv:
            # placeholder in case something needs to happen here?
            pass

        return model_dict


class BPM(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    x_pv = 'xAvg'
    y_pv = 'yAvg'
    phase_pv = 'phaseAvg'

    x_key = 'x_avg'
    y_key = 'y_avg'
    phase_key = 'phi_avg'

    def __init__(self, pv_name: str, model_name: str, phase_offset=None):
        super().__init__(pv_name, model_name)

        xy_noise = AbsNoise(noise=1e-8)
        phase_noise = AbsNoise(noise=1e-4)

        if phase_offset is None:
            phase_offset = (2 * random() - 1) * 180
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)

        self.register_measurement(BPM.x_pv, noise=xy_noise)
        self.register_measurement(BPM.y_pv, noise=xy_noise)
        self.register_measurement(BPM.phase_pv, noise=phase_noise, transform=offset_transform)

    def update_measurement(self, model_key, model_value):
        reason = None
        virtual_value = None
        if model_key == BPM.x_key:
            reason = BPM.x_pv
            virtual_value = model_value
        if model_key == BPM.y_key:
            reason = BPM.y_pv
            virtual_value = model_value
        if model_key == BPM.phase_key:
            reason = BPM.phase_pv
            virtual_value = model_value
        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(virtual_value)))


class WireScanner(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    current_pv = 'Current'
    position_pv = 'Position'

    x_key = 'x_positions'
    y_key = 'y_positions'
    position_key = 'wire_position'
    thick_key = 'wire_thickness'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)

        if initial_dict is not None:
            initial_position = initial_dict[WireScanner.position_key]
            wire_thickness = initial_dict[WireScanner.thick_key]
        else:
            initial_position = -10
            wire_thickness = 10e-6

        self.wire_thickness = wire_thickness

        xy_noise = AbsNoise(noise=1e-8)

        self.register_measurement(WireScanner.current_pv, noise=xy_noise)

        self.register_setting(WireScanner.position_pv, default=initial_position)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == WireScanner.position_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[WireScanner.position_key] = model_value
            return model_dict

    def update_measurement(self, model_key, model_value):
        wire_pos = self.get_setting(WireScanner.position_pv)[WireScanner.position_key]
        wire_thick = self.wire_thickness
        reason = None
        virtual_value = None

        if model_key == WireScanner.x_key:
            virtual_value = 0
            for part_pos in model_value:
                if abs(part_pos - wire_pos) <= wire_thick:
                    virtual_value += 1
            reason = WireScanner.current_pv

        if model_key == WireScanner.y_key:
            virtual_value = 0
            for part_pos in model_value:
                if abs(part_pos - wire_pos) <= wire_thick:
                    virtual_value += 1
            reason = WireScanner.current_pv

        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(virtual_value)))


class pBPM(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    energy_pv = 'Energy'
    beta_pv = 'Beta'

    energy_key = 'energy'
    beta_key = 'beta'

    def __init__(self, pv_name: str, model_name: str):
        super().__init__(pv_name, model_name)

        self.register_measurement(pBPM.energy_pv)
        self.register_measurement(pBPM.beta_pv)

    def update_measurement(self, model_key, value):
        reason = None
        if model_key == pBPM.energy_key:
            reason = pBPM.energy_pv
        if model_key == pBPM.beta_key:
            reason = pBPM.beta_pv
        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(value)))
