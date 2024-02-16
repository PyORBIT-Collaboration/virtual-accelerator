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


class SNS_Cavity(Device):
    # EPICS PV names
    phase_pv = 'CtlPhaseSet'  # [degrees (-180 - 180)]
    amp_pv = 'CtlAmpSet'  # [arb. units]
    amp_goal_pv = 'cavAmpGoal'  # [arb. units]
    blank_pv = 'BlnkBeam'  # [0 or 1]

    design_amp = 15  # [MV]

    # PyORBIT parameter keys
    phase_key = 'phase'  # [radians]
    amp_key = 'amp'  # [arb. units]

    def __init__(self, name: str, model_name: str = None, initial_dict: dict[str,] = None, phase_offset=0):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Sets initial values for parameters.
        if initial_dict is not None:
            initial_phase = initial_dict[SNS_Cavity.phase_key]
            initial_amp = initial_dict[SNS_Cavity.amp_key]
        else:
            initial_phase = 0
            initial_amp = 1.0

        # Create old amp variable for ramping
        self.old_amp = initial_amp

        # Adds a phase offset. Default is 0 offset.
        offset_transform = PhaseTInv(offset=phase_offset, scaler=180 / math.pi)
        initial_phase = offset_transform.raw(initial_phase)

        self.amp_transform = LinearTInv(scaler=SNS_Cavity.design_amp)
        initial_amp = self.amp_transform.raw(initial_amp)

        # Registers the device's PVs with the server
        self.register_setting(SNS_Cavity.phase_pv, default=initial_phase, transform=offset_transform)
        self.register_setting(SNS_Cavity.amp_pv, default=initial_amp, transform=self.amp_transform)
        self.register_setting(SNS_Cavity.amp_goal_pv, default=initial_amp, transform=self.amp_transform)
        self.register_setting(SNS_Cavity.blank_pv, default=0.0)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the setting PV names are associated with their model keys.
    def get_settings(self):
        params_dict = {}
        for setting in self.settings:
            param_value = self.get_setting(setting)
            if setting == SNS_Cavity.phase_pv:
                params_dict = params_dict | {SNS_Cavity.phase_key: param_value}

            elif setting == SNS_Cavity.amp_pv or setting == SNS_Cavity.amp_goal_pv:
                goal_value = self.get_setting(SNS_Cavity.amp_goal_pv)
                set_value = self.get_setting(SNS_Cavity.amp_pv)
                model_value = self.old_amp
                if goal_value != self.old_amp:
                    model_value = goal_value
                    self.setParam(SNS_Cavity.amp_pv, self.amp_transform.raw(goal_value))
                elif set_value != self.old_amp:
                    model_value = set_value
                    self.setParam(SNS_Cavity.amp_goal_pv, self.amp_transform.raw(set_value))
                self.old_amp = model_value

                # If the cavity is blanked, turn off acceleration.
                blank_value = self.get_setting(SNS_Cavity.blank_pv)
                if blank_value == 0:
                    params_dict = params_dict | {SNS_Cavity.amp_key: param_value}
                else:
                    params_dict = params_dict | {SNS_Cavity.amp_key: 0.0}

            elif setting == SNS_Cavity.blank_pv:
                # placeholder in case something needs to happen here?
                pass

        model_dict = {self.model_name: params_dict}
        return model_dict


class SNS_Dummy_BCM(Device):
    # EPICS PV names
    freq_pv = 'FFT_peak2'

    # PyORBIT parameter keys
    beta_key = 'beta'  # [c]

    c_light = 2.99792458e+8  # [m/s]
    ring_length = 248  # [m]

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server.
        self.register_measurement(SNS_Dummy_BCM.freq_pv)

    # Updates the measurement values on the server. Needs the model key associated with it's value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        for model_name, param_dict in new_params.items():
            if model_name == self.model_name:
                for param_key, model_value in param_dict.items():
                    if param_key == SNS_Dummy_BCM.beta_key:
                        reason = SNS_Dummy_BCM.freq_pv
                        beta = model_value
                        freq = beta * SNS_Dummy_BCM.c_light / SNS_Dummy_BCM.ring_length
                        self.update_measurement(reason, freq)
