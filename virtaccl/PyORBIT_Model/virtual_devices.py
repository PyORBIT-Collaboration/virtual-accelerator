import sys
import time
import math
from random import randint, random
from typing import Dict, Any, Union, Literal

import numpy as np
from scipy.interpolate import interp2d

from virtaccl.virtual_devices import Device, AbsNoise, LinearT, PhaseT, PhaseTInv, LinearTInv, PosNoise, NormalizePeak


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
    field_readback_pv = 'B'  # [T/m]
    field_noise = 1e-6  # [T/m]

    # PyORBIT parameter keys
    field_key = 'dB/dr'  # [T/m]

    def __init__(self, name: str, model_name: str, power_supply: Device, power_shunt: Device = None,
                 polarity: Literal[-1, 1] = None):

        self.model_name = model_name
        self.power_supply = power_supply
        self.power_shunt = power_shunt

        if power_shunt is not None:
            connected_devices = [power_supply, power_shunt]
        else:
            connected_devices = power_supply

        super().__init__(name, self.model_name, connected_devices)

        self.pol_transform = LinearTInv(scaler=polarity)

        field_noise = AbsNoise(noise=Quadrupole.field_noise)

        # Registers the device's PVs with the server
        self.register_readback(Quadrupole.field_readback_pv, noise=field_noise)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_settings(self):
        new_field = self.power_supply.get_setting(Quadrupole_Power_Supply.field_set_pv)
        new_field = self.pol_transform.real(new_field)

        if self.power_shunt:
            shunt_field = self.power_shunt.get_setting(Quadrupole_Power_Shunt.field_set_pv)
            shunt_field = self.pol_transform.real(shunt_field)
            new_field += shunt_field

        params_dict = {Quadrupole.field_key: new_field}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        rb_field = abs(self.get_settings()[self.model_name][Quadrupole.field_key])
        rb_param = self.readbacks[Quadrupole.field_readback_pv]
        rb_param.set_param(rb_field)


class Corrector(Device):
    # EPICS PV names
    field_readback_pv = 'B'  # [T]
    field_noise = 1e-6  # [T/m]

    # PyORBIT parameter keys
    field_key = 'B'  # [T]

    def __init__(self, name: str, model_name: str, power_supply: Device, polarity: Literal[-1, 1] = None):
        self.model_name = model_name
        self.power_supply = power_supply

        super().__init__(name, self.model_name, self.power_supply)

        self.pol_transform = LinearTInv(scaler=polarity)

        field_noise = AbsNoise(noise=Corrector.field_noise)

        # Registers the device's PVs with the server
        self.register_readback(Corrector.field_readback_pv, noise=field_noise)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    # These settings have been limited by field_limits, meaning that if the server has a value outside that range, the
    # model will receive the max or min limit defined above.
    def get_settings(self):
        new_field = self.power_supply.get_setting(Corrector_Power_Supply.field_set_pv)

        field_limit_high = self.power_supply.get_setting(Corrector_Power_Supply.field_high_limit_pv)
        field_limit_low = self.power_supply.get_setting(Corrector_Power_Supply.field_low_limit_pv)
        if new_field > field_limit_high:
            new_field = field_limit_high
        elif new_field < field_limit_low:
            new_field = field_limit_low

        new_field = self.pol_transform.real(new_field)

        params_dict = {Corrector.field_key: new_field}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        rb_field = self.get_settings()[self.model_name][Corrector.field_key]
        rb_param = self.readbacks[Corrector.field_readback_pv]
        rb_param.set_param(rb_field)


class Bend(Device):
    # EPICS PV names
    field_readback_pv = 'B'  # [T]
    field_noise = 1e-6  # [T/m]

    # PyORBIT parameter keys
    field_key = 'B'  # [T]

    def __init__(self, name: str, model_name: str, power_supply: Device):
        self.model_name = model_name
        self.power_supply = power_supply

        super().__init__(name, self.model_name, self.power_supply)

        field_noise = AbsNoise(noise=Bend.field_noise)

        # Registers the device's PVs with the server
        self.register_readback(Bend.field_readback_pv, noise=field_noise)

    def update_readbacks(self):
        field = self.power_supply.get_setting(Bend_Power_Supply.field_set_pv)
        rb_param = self.readbacks[Bend.field_readback_pv]
        rb_param.set_param(field)


class Cavity(Device):
    # EPICS PV names
    phase_pv = 'CtlPhaseSet'  # [degrees (-180 - 180)]
    amp_pv = 'CtlAmpSet'  # [arb. units]
    amp_goal_pv = 'cavAmpGoal'  # [arb. units]
    blank_pv = 'BlnkBeam'  # [0 or 1]

    # PyORBIT parameter keys
    phase_key = 'phase'  # [radians]
    amp_key = 'amp'  # [arb. units]

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None, phase_offset=0,
                 design_amp=15):
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

        self.design_amp = design_amp  # [MV]

        # Create old amp variable for ramping
        self.old_amp = initial_amp

        # Adds a phase offset. Default is 0 offset.
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)
        amp_transform = LinearTInv(scaler=design_amp)

        initial_phase = offset_transform.raw(initial_phase)
        initial_amp = amp_transform.raw(initial_amp)

        # Registers the device's PVs with the server
        self.register_setting(Cavity.phase_pv, default=initial_phase, transform=offset_transform)
        self.register_setting(Cavity.amp_pv, default=initial_amp, transform=amp_transform)
        self.register_setting(Cavity.amp_goal_pv, default=initial_amp, transform=amp_transform)
        self.register_setting(Cavity.blank_pv, default=0.0)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    def get_settings(self):
        params_dict = {}
        for setting, param in self.settings.items():
            param_value = param.get_param()
            if setting == Cavity.phase_pv:
                params_dict = params_dict | {Cavity.phase_key: param_value}

            elif setting == Cavity.amp_pv or setting == Cavity.amp_goal_pv:
                goal_value = self.get_setting(Cavity.amp_goal_pv)
                set_value = self.get_setting(Cavity.amp_pv)
                model_value = self.old_amp
                if goal_value != self.old_amp:
                    model_value = goal_value
                    amp_param = self.settings[Cavity.amp_pv]
                    amp_param.set_param(goal_value)
                elif set_value != self.old_amp:
                    model_value = set_value
                    goal_param = self.settings[Cavity.amp_goal_pv]
                    goal_param.set_param(set_value)
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
        amp_noise = PosNoise(noise=BPM.amp_noise)

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
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        bpm_params = new_params[self.model_name]
        amp = bpm_params[BPM.amp_key]
        self.update_measurement(BPM.amp_pv, amp)

        if amp < 1e-8:
            x_avg = (random() * 2 - 1) * 0.1
            y_avg = (random() * 2 - 1) * 0.1
            phase_avg = (random() * 2 - 1) * 0.1
        else:
            x_avg = bpm_params[BPM.x_key]
            y_avg = bpm_params[BPM.y_key]
            phase_avg = bpm_params[BPM.phase_key]

        self.update_measurement(BPM.x_pv, x_avg)
        self.update_measurement(BPM.y_pv, y_avg)
        self.update_measurement(BPM.phase_pv, phase_avg)


class WireScanner(Device):
    # EPICS PV names
    x_charge_pv = 'Hor_Cont'  # [arb. units]
    y_charge_pv = 'Ver_Cont'  # [arb. units]
    position_pv = 'Position_Set'  # [mm]
    position_readback_pv = 'Position'  # [mm]
    speed_pv = 'Speed_Set'  # [mm/s]
    x_avg_pv = 'Hor_Mean_gs'  # [mm]
    y_avg_pv = 'Ver_Mean_gs'  # [mm]

    # PyORBIT parameter keys
    x_hist_key = 'x_histogram'  # [arb. units]
    y_hist_key = 'y_histogram'  # [arb. units]
    x_avg_key = 'x_avg'  # [m]
    y_avg_key = 'y_avg'  # [m]

    # Device keys
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
        self.milli_units = LinearTInv(scaler=1e3)

        # Sets initial values for parameters.
        if initial_dict is not None:
            initial_position = initial_dict[WireScanner.position_key]
            initial_speed = initial_dict[WireScanner.speed_key]
        else:
            initial_position = -0.05  # [m]
            initial_speed = 0.001  # [mm/s]

        # Defines internal parameters to keep track of the wire position.
        self.last_wire_pos = initial_position
        self.last_wire_time = time.time()
        self.wire_speed = initial_speed

        initial_position = self.milli_units.raw(initial_position)
        initial_speed = self.milli_units.raw(initial_speed)

        # Creates flat noise for associated PVs.
        xy_noise = AbsNoise(noise=1e-9)
        pos_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        self.register_measurement(WireScanner.x_charge_pv, noise=xy_noise)
        self.register_measurement(WireScanner.y_charge_pv, noise=xy_noise)
        self.register_measurement(WireScanner.x_avg_pv, noise=xy_noise, transform=self.milli_units)
        self.register_measurement(WireScanner.y_avg_pv, noise=xy_noise, transform=self.milli_units)

        self.register_setting(WireScanner.speed_pv, default=initial_speed, transform=self.milli_units)
        pos_param = self.register_setting(WireScanner.position_pv, default=initial_position, transform=self.milli_units)
        self.register_readback(WireScanner.position_readback_pv, pos_param, transform=self.milli_units, noise=pos_noise)

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
        wire_goal = self.settings[WireScanner.position_pv].get_param()
        wire_speed = self.settings[WireScanner.speed_pv].get_param()
        params_dict = {WireScanner.position_key: wire_goal, WireScanner.speed_key: wire_speed}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model.
    def update_readbacks(self):
        wire_pos = WireScanner.get_wire_position(self)
        self.update_readback(WireScanner.position_readback_pv, wire_pos)

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        # Find the current position of the center of the wire scanner
        wire_pos = WireScanner.get_wire_position(self)

        ws_params = new_params[self.model_name]
        x_hist = ws_params[WireScanner.x_hist_key]
        y_hist = ws_params[WireScanner.y_hist_key]

        # Find the location of the vertical wire. Then interpolate the histogram from the model at that value.
        x_pos = WireScanner.wire_coeff * wire_pos + WireScanner.x_offset
        x_value = np.interp(x_pos, x_hist[:, 0], x_hist[:, 1], left=0, right=0)
        self.update_measurement(WireScanner.x_charge_pv, x_value)
        y_pos = WireScanner.wire_coeff * wire_pos + WireScanner.y_offset
        y_value = np.interp(y_pos, y_hist[:, 0], y_hist[:, 1], left=0, right=0)
        self.update_measurement(WireScanner.y_charge_pv, y_value)

        self.update_measurement(WireScanner.x_avg_pv, ws_params[WireScanner.x_avg_key])
        self.update_measurement(WireScanner.y_avg_pv, ws_params[WireScanner.y_avg_key])


class Screen(Device):
    # EPICS PV names
    x_profile_pv = 'resultsHorProf'  # [au]
    y_profile_pv = 'resultsVerProf'  # [au]
    image_pv = 'resultsImg'  # [au]
    image_noise = 5  # [au]
    x_axis_pv = 'resultsHorProfX'  # [mm]
    y_axis_pv = 'resultsVerProfX'  # [mm]

    # PyORBIT parameter keys
    hist_key = 'xy_histogram'  # [au]
    x_axis_key = 'x_axis'  # [m]
    y_axis_key = 'y_axis'  # [m]
    x_key = 'x_avg'  # [m]
    y_key = 'y_avg'  # [m]

    def __init__(self, name: str, model_name: str = None, x_pixels: int = 600, y_pixels: int = 960,
                 x_scale=100, y_scale=100):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        x_pixels = x_pixels
        y_pixels = y_pixels
        x_scale = x_scale
        y_scale = y_scale

        # Define new grid for higher resolution
        self.x_axis_new = np.linspace(-x_scale / 2, x_scale / 2, x_pixels)
        self.y_axis_new = np.linspace(-y_scale / 2, y_scale / 2, y_pixels)

        # Creates flat noise for associated PVs.
        self.image_noise = PosNoise(noise=Screen.image_noise, count=(y_pixels, x_pixels))

        signal_max = 254
        self.signal_normalize = NormalizePeak(max_value=signal_max)

        # Registers the device's PVs with the server.
        self.register_measurement(Screen.x_profile_pv, definition={'count': x_pixels})
        self.register_measurement(Screen.y_profile_pv, definition={'count': y_pixels})
        self.register_measurement(Screen.image_pv, definition={'type': 'char', 'count': x_pixels * y_pixels})

        self.register_readback(Screen.x_axis_pv, definition={'count': x_pixels})
        self.register_readback(Screen.y_axis_pv, definition={'count': y_pixels})

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        screen_params = new_params[self.model_name]
        xy_hist = screen_params[Screen.hist_key]
        x_axis = screen_params[Screen.x_axis_key] * 1000
        y_axis = screen_params[Screen.y_axis_key] * 1000

        # Calculate bin centers
        x_centers = (x_axis[:-1] + x_axis[1:]) / 2
        y_centers = (y_axis[:-1] + y_axis[1:]) / 2

        # Create linearly interpolated function
        interp_func = interp2d(x_centers, y_centers, xy_hist, kind='linear', fill_value=False)

        # Interpolate histogram to higher resolution
        xy_hist_new = interp_func(self.x_axis_new, self.y_axis_new)
        xy_hist_new = self.image_noise.add_noise(xy_hist_new)
        xy_hist_new = self.signal_normalize.raw(xy_hist_new)

        x_profile = np.sum(xy_hist_new, axis=0)
        y_profile = np.sum(xy_hist_new, axis=1)
        image_list = xy_hist_new.flatten()

        self.update_measurement(Screen.image_pv, image_list)
        self.update_measurement(Screen.x_profile_pv, x_profile)
        self.update_measurement(Screen.y_profile_pv, y_profile)

    def update_readbacks(self):
        self.update_readback(Screen.x_axis_pv, self.x_axis_new)
        self.update_readback(Screen.y_axis_pv, self.y_axis_new)


class Quadrupole_Power_Supply(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]
    field_noise = 1e-6  # [T/m]

    book_pv = 'B_Book'

    def __init__(self, name: str, init_field=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        field_param = self.register_setting(Quadrupole_Power_Supply.field_set_pv, default=init_field)
        self.register_readback(Quadrupole_Power_Supply.field_readback_pv, field_param, noise=field_noise)

        self.register_readback(Quadrupole_Power_Supply.book_pv, field_param)


class Quadrupole_Power_Shunt(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]
    field_noise = 1e-6  # [T/m]

    book_pv = 'B_Book'

    def __init__(self, name: str, init_field=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        field_param = self.register_setting(Quadrupole_Power_Shunt.field_set_pv, default=init_field)
        self.register_readback(Quadrupole_Power_Shunt.field_readback_pv, field_param, noise=field_noise)

        self.register_readback(Quadrupole_Power_Shunt.book_pv, field_param)


class Bend_Power_Supply(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]
    field_noise = 1e-6  # [T/m]

    book_pv = 'B_Book'

    def __init__(self, name: str, init_field=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        field_param = self.register_setting(Bend_Power_Supply.field_set_pv, default=init_field)
        self.register_readback(Bend_Power_Supply.field_readback_pv, field_param, noise=field_noise)

        self.register_readback(Bend_Power_Supply.book_pv, field_param)


class Corrector_Power_Supply(Device):
    # EPICS PV names
    field_set_pv = 'B_Set'  # [T/m]
    field_readback_pv = 'B'  # [T/m]
    field_noise = 1e-6  # [T/m]

    # Initial field limits
    field_high_limit_pv = 'B_Set.HOPR'
    field_low_limit_pv = 'B_Set.LOPR'
    field_limits = [-0.1, 0.1]  # [T]

    book_pv = 'B_Book'

    def __init__(self, name: str, init_field=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        field_param = self.register_setting(Corrector_Power_Supply.field_set_pv, default=init_field)
        self.register_readback(Corrector_Power_Supply.field_readback_pv, field_param, noise=field_noise)

        self.register_setting(Corrector_Power_Supply.field_high_limit_pv,
                              default=Corrector_Power_Supply.field_limits[1])
        self.register_setting(Corrector_Power_Supply.field_low_limit_pv, default=Corrector_Power_Supply.field_limits[0])

        self.register_readback(Corrector_Power_Supply.book_pv, field_param)


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
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        for model_name, param_dict in new_params.items():
            if model_name == self.model_name:
                for param_key, model_value in param_dict.items():
                    reason = None
                    if param_key == P_BPM.energy_key:
                        reason = P_BPM.energy_pv
                    elif param_key == P_BPM.beta_key:
                        reason = P_BPM.beta_pv
                    elif param_key == P_BPM.num_key:
                        reason = P_BPM.num_pv

                    if reason is not None:
                        self.update_measurement(reason, model_value)
