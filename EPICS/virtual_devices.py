import time
import math
from random import randint, random

import numpy as np

from ca_server import Device, AbsNoise, LinearT, PhaseT, not_ctrlc, PhaseTInv, LinearTInv


class Quadrupole(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    field_set_pv = 'B_Set'
    field_readback_pv = 'B'

    field_key = 'dB/dr'

    def __init__(self, name: str, model_name: str, initial_dict=None):
        super().__init__(name, model_name)
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

    field_limits = [-0.1, 0.1]

    def __init__(self, name: str, model_name: str, initial_dict=None):
        super().__init__(name, model_name)
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
            if model_value < self.field_limits[0]:
                model_value = self.field_limits[0]
            elif model_value > self.field_limits[1]:
                model_value = self.field_limits[1]
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
    phase_pv = 'CtlPhaseSet'  # [degrees (-180 - 180)]
    amp_pv = 'CtlAmpSet'  # [arb. units]
    blank_pv = 'BlnkBeam'  # [0 or 1]

    phase_key = 'phase'  # [radians]
    amp_key = 'amp'  # [arb. units]

    def __init__(self, name: str, model_name: str, initial_dict=None, phase_offset=None):
        super().__init__(name, model_name)
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
    x_pv = 'xAvg'  # [mm]
    y_pv = 'yAvg'  # [mm]
    phase_pv = 'phaseAvg'  # [degrees]
    current_pv = 'amplitudeAvg'  # [mA]

    x_key = 'x_avg'  # [m]
    y_key = 'y_avg'  # [m]
    phase_key = 'phi_avg'  # [radians]
    current_key = 'current'  # [A]

    def __init__(self, name: str, model_name: str, phase_offset=None):
        super().__init__(name, model_name)

        xy_noise = AbsNoise(noise=1e-8)
        phase_noise = AbsNoise(noise=1e-4)
        current_noise = AbsNoise(noise=1e-4)

        milli_units = LinearTInv(scaler=1000)

        if phase_offset is None:
            phase_offset = (2 * random() - 1) * 180
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)

        self.register_measurement(BPM.x_pv, noise=xy_noise, transform=milli_units)
        self.register_measurement(BPM.y_pv, noise=xy_noise, transform=milli_units)
        self.register_measurement(BPM.phase_pv, noise=phase_noise, transform=offset_transform)
        self.register_measurement(BPM.current_pv, noise=current_noise, transform=milli_units)

    def update_measurement(self, model_key, model_value):
        reason = None
        virtual_value = None
        if model_key == BPM.x_key:
            reason = BPM.x_pv
            virtual_value = model_value
        elif model_key == BPM.y_key:
            reason = BPM.y_pv
            virtual_value = model_value
        elif model_key == BPM.phase_key:
            reason = BPM.phase_pv
            virtual_value = model_value
        elif model_key == BPM.current_key:
            reason = BPM.current_pv
            virtual_value = model_value
        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(virtual_value)))


class WireScanner(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    x_charge_pv = 'Hor_Cont'  # [arb. units]
    y_charge_pv = 'Ver_Cont'  # [arb. units]
    position_pv = 'Position_Set'  # [mm]
    position_readback_pv = 'Position'  # [mm]
    speed_pv = 'Speed_Set'  # [mm/s]

    x_key = 'x_histogram'  # [arb. units]
    y_key = 'y_histogram'  # [arb. units]
    position_key = 'wire_position'  # [m]
    speed_key = 'wire_speed'  # [m]

    x_offset = -0.01
    y_offset = 0.01
    wire_coeff = 1 / math.sqrt(2)

    def __init__(self, name: str, model_name: str, initial_dict=None):
        super().__init__(name, model_name)

        if initial_dict is not None:
            initial_position = initial_dict[WireScanner.position_key]
            initial_speed = initial_dict[WireScanner.speed_key]
        else:
            initial_position = -50  # [mm]
            initial_speed = 1  # [mm/s]

        xy_noise = AbsNoise(noise=1e-9)
        milli_units = LinearTInv(scaler=1e3)

        self.last_wire_pos = milli_units.real(initial_position)
        self.last_wire_time = time.time()
        self.wire_speed = milli_units.real(initial_speed)

        self.register_measurement(WireScanner.x_charge_pv, noise=xy_noise)
        self.register_measurement(WireScanner.y_charge_pv, noise=xy_noise)

        self.register_setting(WireScanner.speed_pv, default=initial_speed, transform=milli_units)
        self.register_setting(WireScanner.position_pv, default=initial_position, transform=milli_units,
                              reason_rb=WireScanner.position_readback_pv)

    def get_wire_position(self):
        last_pos = self.last_wire_pos
        last_time = self.last_wire_time
        wire_speed = self.get_setting(WireScanner.speed_pv)[WireScanner.speed_key]
        pos_goal = self.get_setting(WireScanner.position_pv)[WireScanner.position_key]
        direction = np.sign(pos_goal - last_pos)
        current_time = time.time()

        wire_pos = direction * wire_speed * (current_time - last_time) + last_pos
        if last_pos == pos_goal:
            wire_pos = pos_goal
        elif direction < 0 and wire_pos < pos_goal:
            wire_pos = pos_goal
        elif direction > 0 and wire_pos > pos_goal:
            wire_pos = pos_goal

        self.last_wire_time = current_time
        self.last_wire_pos = wire_pos
        return wire_pos

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == WireScanner.position_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[WireScanner.position_key] = model_value
        elif reason == WireScanner.speed_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[WireScanner.speed_key] = model_value
        return model_dict

    def update_readback(self, reason):
        value = None
        if reason == WireScanner.position_pv:
            value = WireScanner.get_wire_position(self)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))

    def update_measurement(self, model_key, model_value):
        wire_pos = WireScanner.get_wire_position(self)

        reason = None
        virtual_value = None
        if model_key == WireScanner.x_key:
            x_pos = WireScanner.wire_coeff * wire_pos + WireScanner.x_offset
            virtual_value = np.interp(x_pos, model_value[:, 0], model_value[:, 1])
            reason = WireScanner.x_charge_pv

        elif model_key == WireScanner.y_key:
            y_pos = WireScanner.wire_coeff * wire_pos + WireScanner.y_offset
            virtual_value = np.interp(y_pos, model_value[:, 0], model_value[:, 1])
            reason = WireScanner.y_charge_pv

        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(virtual_value)))


class PBPM(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    energy_pv = 'Energy'  # [GeV]
    beta_pv = 'Beta'  # [c]

    energy_key = 'energy'  # [GeV]
    beta_key = 'beta'  # [c]

    def __init__(self, name: str, model_name: str):
        super().__init__(name, model_name)

        self.register_measurement(PBPM.energy_pv)
        self.register_measurement(PBPM.beta_pv)

    def update_measurement(self, model_key, value):
        reason = None
        if model_key == PBPM.energy_key:
            reason = PBPM.energy_pv
        elif model_key == PBPM.beta_key:
            reason = PBPM.beta_pv

        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(value)))
