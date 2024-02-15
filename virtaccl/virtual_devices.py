import time
import math
from random import randint, random
from typing import Dict, Any

import numpy as np

from .ca_server import Device, AbsNoise, LinearT, PhaseT, not_ctrlc, PhaseTInv, LinearTInv


# Here are the device definitions that take the information from PyORBIT and translates/packages it into information for
# the server.
#
# All the devices need a name that will determine the name of the device in the EPICS server. If the corresponding
# element in PyORBIT has a different name, then it will need to be specified in the declaration as the model_name. If
# the device has settings (values changed by the user), they can be given initial values to match the model using
# initial_dict. These initial settings need to be in a dictionary using the appropriate keys defined by PyORBIT to
# differentiate different parameters. And finally, if the device has a phase, both setting and measurement, they can be
# given an offset using phase_offset.
#
# The strings denoted with a "_pv" are labels for EPICS. Changing these will alter the EPICS labels for values on the
# server. The strings denoted with a "_key" are the keys for parameters in PyORBIT for that device. These need to match
# the keys PyORBIT uses in the paramsDict for that devices corresponding PyORBIT element.

class Quadrupole(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]

    # PyORBIT parameter keys
    field_key = 'dB/dr'  # [T/m]

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Sets up initial values.
        if initial_dict is not None:
            initial_field = initial_dict[Quadrupole.field_key]
        else:
            initial_field = 0.0

        # Registers the device's PVs with the server
        self.register_setting(Quadrupole.field_set_pv, default=initial_field,
                              reason_rb=Quadrupole.field_readback_pv)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == Quadrupole.field_set_pv:
                params_dict = params_dict | {Quadrupole.field_key: param_value}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readback(self, reason):
        value = None
        if reason == Quadrupole.field_set_pv:
            value = self.get_setting(Quadrupole.field_set_pv)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Quadrupole_Doublet(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]

    # PyORBIT parameter keys
    field_key = 'dB/dr'  # [T/m]

    def __init__(self, name: str, h_model_name: str, v_model_name: str, initial_dict: Dict[str, Any] = None):
        self.h_name = h_model_name
        self.v_name = v_model_name
        self.model_names = [h_model_name, v_model_name]
        super().__init__(name, self.model_names)

        # Sets up initial values.
        if initial_dict is not None:
            initial_field = initial_dict[Quadrupole_Doublet.field_key]
        else:
            initial_field = 0.0

        # Registers the device's PVs with the server
        self.register_setting(Quadrupole_Doublet.field_set_pv, default=initial_field,
                              reason_rb=Quadrupole_Doublet.field_readback_pv)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_settings(self):
        h_params = {}
        v_params = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == Quadrupole_Doublet.field_set_pv:
                h_param = param_value
                h_params = h_params | {Quadrupole_Doublet.field_key: h_param}
                v_param = -param_value
                v_params = v_params | {Quadrupole_Doublet.field_key: v_param}
        model_dict = {self.h_name: h_params, self.v_name: v_params}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readback(self, reason):
        value = None
        if reason == Quadrupole_Doublet.field_set_pv:
            value = self.get_setting(Quadrupole_Doublet.field_set_pv)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Quadrupole_Set(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]

    # PyORBIT parameter keys
    field_key = 'dB/dr'  # [T/m]

    def __init__(self, name: str, model_names: list[str], initial_dict: Dict[str, Any] = None):
        self.model_names = model_names
        super().__init__(name, self.model_names)

        # Sets up initial values.
        if initial_dict is not None:
            initial_field = initial_dict[Quadrupole.field_key]
        else:
            initial_field = 0.0

        # Registers the device's PVs with the server
        self.register_setting(Quadrupole.field_set_pv, default=initial_field,
                              reason_rb=Quadrupole.field_readback_pv)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_settings(self):
        model_dict = {}
        for model_name in self.model_names:
            params_dict = {}
            for setting in self.settings:
                param_value = self.get_setting(setting)
                if setting == Quadrupole.field_set_pv:
                    params_dict = params_dict | {Quadrupole.field_key: param_value}
            model_dict = model_dict | {model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readback(self, reason):
        value = None
        if reason == Quadrupole.field_set_pv:
            value = self.get_setting(Quadrupole.field_set_pv)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Corrector(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T]
    field_readback_pv = 'B'  # [T]

    # PyORBIT parameter keys
    field_key = 'B'  # [T]

    # Setting limits
    field_limits = [-0.1, 0.1]  # [T]

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Sets initial values for parameters.
        if initial_dict is not None:
            initial_field = initial_dict[Corrector.field_key]
        else:
            initial_field = 0.0

        # Registers the device's PVs with the server
        self.register_setting(Corrector.field_set_pv, default=initial_field, reason_rb=self.field_readback_pv)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    # These settings have been limited by field_limits, meaning that if the server has a value outside that range, the
    # model will receive the max or min limit defined above.
    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == Corrector.field_set_pv:
                if param_value < self.field_limits[0]:
                    param_value = self.field_limits[0]
                elif param_value > self.field_limits[1]:
                    param_value = self.field_limits[1]
                params_dict = params_dict | {Corrector.field_key: param_value}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readback(self, reason):
        value = None
        if reason == Corrector.field_set_pv:
            value = self.get_setting(Corrector.field_set_pv)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Cavity(Device):
    # EPICS PV names
    phase_pv = 'CtlPhaseSet'  # [degrees (-180 - 180)]
    amp_pv = 'CtlAmpSet'  # [arb. units]
    amp_goal_pv = 'cavAmpGoal'  # [arb. units]
    blank_pv = 'BlnkBeam'  # [0 or 1]

    # PyORBIT parameter keys
    phase_key = 'phase'  # [radians]
    amp_key = 'amp'  # [arb. units]

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None, phase_offset=0):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Sets initial values for parameters.
        if initial_dict is not None:
            initial_phase = initial_dict[Cavity.phase_key]
            initial_amp = initial_dict[Cavity.amp_key]
        else:
            initial_phase = 0
            initial_amp = 1.0

        # Create old amp variable for ramping
        self.old_amp = initial_amp

        # Adds a phase offset. Default is 0 offset.
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)
        initial_phase = offset_transform.raw(initial_phase)

        # Registers the device's PVs with the server
        self.register_setting(Cavity.phase_pv, default=initial_phase, transform=offset_transform)
        self.register_setting(Cavity.amp_pv, default=initial_amp)
        self.register_setting(Cavity.amp_goal_pv, default=initial_amp)
        self.register_setting(Cavity.blank_pv, default=0.0)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == Cavity.phase_pv:
                params_dict = params_dict | {Cavity.phase_key: param_value}

            elif setting == Cavity.amp_pv or setting == Cavity.amp_goal_pv:
                goal_value = self.get_setting(Cavity.amp_goal_pv)
                set_value = self.get_setting(Cavity.amp_pv)
                model_value = self.old_amp
                if goal_value != self.old_amp:
                    model_value = goal_value
                    self.setParam(Cavity.amp_pv, goal_value)
                elif set_value != self.old_amp:
                    model_value = set_value
                    self.setParam(Cavity.amp_goal_pv, set_value)
                self.old_amp = model_value

                # If the cavity is blanked, turn off acceleration.
                blank_value = self.get_setting(Cavity.blank_pv)
                if blank_value == 0:
                    params_dict = params_dict | {Cavity.amp_key: param_value}
                else:
                    params_dict = params_dict | {Cavity.amp_key: 0.0}

            elif setting == Cavity.blank_pv:
                # placeholder in case something needs to happen here?
                pass

        model_dict = {self.model_name: params_dict}
        return model_dict


class BPM(Device):
    # EPICS PV names
    x_pv = 'xAvg'  # [mm]
    y_pv = 'yAvg'  # [mm]
    xy_noise = 1e-8  # [mm]
    phase_pv = 'phaseAvg'  # [degrees]
    phase_noise = 1e-4  # [degrees]
    amp_pv = 'amplitudeAvg'  # [mA]
    amp_noise = 1e-6  # mA
    oeda_pv = 'OEDA'  # Off Energy Delay Adjustment. Should be 0 during production.

    # PyORBIT parameter keys
    x_key = 'x_avg'  # [m]
    y_key = 'y_avg'  # [m]
    phase_key = 'phi_avg'  # [radians]
    amp_key = 'amp_avg'  # [A]

    def __init__(self, name: str, model_name: str = None, phase_offset=0):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        milli_units = LinearTInv(scaler=1e3)

        # Creates flat noise for associated PVs.
        xy_noise = AbsNoise(noise=BPM.xy_noise)
        phase_noise = AbsNoise(noise=BPM.phase_noise)
        amp_noise = AbsNoise(noise=BPM.amp_noise)

        # Adds a phase offset. Default is 0 offset.
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)

        # Registers the device's PVs with the server.
        self.register_measurement(BPM.x_pv, noise=xy_noise, transform=milli_units)
        self.register_measurement(BPM.y_pv, noise=xy_noise, transform=milli_units)
        self.register_measurement(BPM.phase_pv, noise=phase_noise, transform=offset_transform)
        self.register_measurement(BPM.amp_pv, noise=amp_noise, transform=milli_units)

        self.register_setting(BPM.oeda_pv, default=0)

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]]):
        for model_name, param_dict in new_params.items():
            if model_name == self.model_name:
                for param_key, new_value in param_dict.items():
                    reason = None
                    if param_key == BPM.x_key:
                        reason = BPM.x_pv
                    elif param_key == BPM.y_key:
                        reason = BPM.y_pv
                    elif param_key == BPM.phase_key:
                        reason = BPM.phase_pv
                    elif param_key == BPM.amp_key:
                        reason = BPM.amp_pv

                    if reason is not None:
                        self.update_measurement(reason, new_value)

    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == BPM.oeda_pv:
                pass
        model_dict = {self.model_name: params_dict}
        return model_dict


class WireScanner(Device):
    # EPICS PV names
    x_charge_pv = 'Hor_Cont'  # [arb. units]
    y_charge_pv = 'Ver_Cont'  # [arb. units]
    position_pv = 'Position_Set'  # [mm]
    position_readback_pv = 'Position'  # [mm]
    speed_pv = 'Speed_Set'  # [mm/s]

    # PyORBIT parameter keys
    x_key = 'x_histogram'  # [arb. units]
    y_key = 'y_histogram'  # [arb. units]
    position_key = 'wire_position'  # [m]
    speed_key = 'wire_speed'  # [m]

    x_offset = -0.01  # [m]
    y_offset = 0.01  # [m]
    wire_coeff = 1 / math.sqrt(2)

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        milli_units = LinearTInv(scaler=1e3)

        # Sets initial values for parameters.
        if initial_dict is not None:
            initial_position = initial_dict[WireScanner.position_key]
            initial_speed = initial_dict[WireScanner.speed_key]
        else:
            initial_position = -50  # [mm]
            initial_speed = 1  # [mm/s]

        # Defines internal parameters to keep track of the wire position.
        self.last_wire_pos = milli_units.real(initial_position)
        self.last_wire_time = time.time()
        self.wire_speed = milli_units.real(initial_speed)

        # Creates flat noise for associated PVs.
        xy_noise = AbsNoise(noise=1e-9)

        # Registers the device's PVs with the server.
        self.register_measurement(WireScanner.x_charge_pv, noise=xy_noise)
        self.register_measurement(WireScanner.y_charge_pv, noise=xy_noise)

        self.register_setting(WireScanner.speed_pv, default=initial_speed, transform=milli_units)
        self.register_setting(WireScanner.position_pv, default=initial_position, transform=milli_units,
                              reason_rb=WireScanner.position_readback_pv)

    # Function to find the position of the virtual wire using time of flight from the previous position and the speed of
    # the wire.
    def get_wire_position(self):
        last_pos = self.last_wire_pos
        last_time = self.last_wire_time
        wire_speed = self.get_setting(WireScanner.speed_pv)
        pos_goal = self.get_setting(WireScanner.position_pv)
        direction = np.sign(pos_goal - last_pos)
        current_time = time.time()
        wire_pos = direction * wire_speed * (current_time - last_time) + last_pos

        # If the wire has passed it's objective, place it at it's objective.
        if last_pos == pos_goal:
            wire_pos = pos_goal
        elif direction < 0 and wire_pos < pos_goal:
            wire_pos = pos_goal
        elif direction > 0 and wire_pos > pos_goal:
            wire_pos = pos_goal

        # Reset variables for next calculation.
        self.last_wire_time = current_time
        self.last_wire_pos = wire_pos

        return wire_pos

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == WireScanner.position_pv:
                params_dict = params_dict | {WireScanner.position_key: param_value}
            elif setting == WireScanner.speed_pv:
                params_dict = params_dict | {WireScanner.speed_key: param_value}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readback(self, reason):
        value = None
        if reason == WireScanner.position_pv:
            value = WireScanner.get_wire_position(self)

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]]):
        # Find the current position of the center of the wire scanner
        wire_pos = WireScanner.get_wire_position(self)

        for model_name, param_dict in new_params.items():
            if model_name == self.model_name:
                for param_key, model_value in param_dict.items():
                    reason = None
                    virtual_value = 0
                    if param_key == WireScanner.x_key:
                        # Find the location of the vertical wire. Then interpolate the histogram from the model at that value.
                        x_pos = WireScanner.wire_coeff * wire_pos + WireScanner.x_offset
                        virtual_value = np.interp(x_pos, model_value[:, 0], model_value[:, 1])
                        reason = WireScanner.x_charge_pv

                    elif param_key == WireScanner.y_key:
                        # Find the location of the horizontal wire. Then interpolate the histogram from the model at that value.
                        y_pos = WireScanner.wire_coeff * wire_pos + WireScanner.y_offset
                        virtual_value = np.interp(y_pos, model_value[:, 0], model_value[:, 1])
                        reason = WireScanner.y_charge_pv

                    if reason is not None:
                        self.update_measurement(reason, virtual_value)


# An unrealistic device associated with BPMs in the PyORBIT model that tracks values that cannot be measured directly.
# (Physics-BPM)
class P_BPM(Device):
    # EPICS PV names
    energy_pv = 'Energy'  # [GeV]
    beta_pv = 'Beta'  # [c]
    num_pv = 'Particle_Number'

    # PyORBIT parameter keys
    energy_key = 'energy'  # [GeV]
    beta_key = 'beta'  # [c]
    num_key = 'part_num'

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server.
        self.register_measurement(P_BPM.energy_pv)
        self.register_measurement(P_BPM.beta_pv)
        self.register_measurement(P_BPM.num_pv)

    # Updates the measurement values on the server. Needs the model key associated with it's value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurement(self, model_key, value):
        reason = None
        if model_key == P_BPM.energy_key:
            reason = P_BPM.energy_pv
        elif model_key == P_BPM.beta_key:
            reason = P_BPM.beta_pv
        elif model_key == P_BPM.num_key:
            reason = P_BPM.num_pv

        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(value)))
