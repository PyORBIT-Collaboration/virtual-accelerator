import sys
import time
import math
from random import randint, random
from typing import Dict, Any, Union, Literal

import numpy as np
from virtaccl.PyORBIT_Model.virtual_devices import Cavity, Quadrupole, Corrector, WireScanner

from virtaccl.virtual_devices import Device, AbsNoise, LinearT, PhaseT, PhaseTInv, LinearTInv

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

#class FC_BTF(Device):
#    # EPICS PV names
#    waveform = 'WF'

class BTF_Dummy_Corrector(Device):
    # EPICS PV names
    field_set_pv = 'B_Set' # [T/m]
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
        field_param = self.register_setting(BTF_Dummy_Corrector.field_set_pv, default=init_field)
        self.register_readback(BTF_Dummy_Corrector.field_readback_pv, field_param, noise=field_noise)

        self.register_setting(BTF_Dummy_Corrector.field_high_limit_pv, default=BTF_Dummy_Corrector.field_limits[1])

        self.register_setting(BTF_Dummy_Corrector.field_low_limit_pv, default=BTF_Dummy_Corrector.field_limits[0])

        self.register_readback(BTF_Dummy_Corrector.book_pv, field_param)

#class BTF_Dummy_Screen(Device):
#    # EPICS PV names
#    position_set_pv = 'DesitinationSet'
#    position_readback_pv = 'PositionSync'
#    command_pv = 'Command'
#
#    def __init__(self, name:str, init_position=None, init_command=None):
#        super().__init__(name)
#
#        # Registers the device's PVs with the server
#        position_param = self.register_setting(BTF_Dummy_Screen.position_set_pv, default=init_position)
#        self.register_readback(BTF_Dummy_Screen.position_readback_pv, position_param)
#        
#        self.register_setting(BTF_Dummy_Screen.command_Set_pv, default=init_command)
#        
#    def get_settings(self):
#
#
#    def update_readbacks(self):
#        command_status = self.get_setting[BTF_Dummy_Screen.command_readback_pv]
#
#        if command_status == 'Move':
#            position = self.get_setting(BTF_Dummy_Screen.position_set_pv)
#            rb_param = self.readbacks[BTF_Dummy_Screen.position_readback_pv]
#            rb_param.set_param(position)
#
#        if command_status == 'Park':
#            position = -60
#            rb_param = self.readbacks[BTF_Dummy_Screen.position_readback_pv]
#            rb_param.set_param(position)
#
#        if command_status == 'Stop':
#            position = self.get_setting

class BTF_FC(Device):
    #EPICS PV names
    current_pv = 'WF' # [A?]
    state_set_pv = 'State_Set'
    state_readback_pv = 'State'

    #PyORBIT parameter keys
    current_key = 'current'
    state_key = 'state'

    def __init__(self, name: str, model_name: str = None, init_state=None):
        
        self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server
        self.register_measurement(BTF_FC.current_pv)
        
        state_param = self.register_setting(BTF_FC.state_set_pv, default=init_state)
        self.register_readback(BTF_FC.state_readback_pv, state_param)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_settings(self):
        new_state = self.get_setting(BTF_FC.state_set_pv)
         
        params_dict = {BTF_FC.state_key: new_state}
        model_dict = {self.model_name: params_dict}
        print(model_dict)
        return model_dict

    def update_readbacks(self):
        fc_state = self.get_settings()[self.model_name][BTF_FC.state_key]
        rb_param = self.readbacks[BTF_FC.state_readback_pv]
        rb_param.set_param(fc_state)
        
    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        fc_params = new_params[self.model_name]
        current = fc_params[BTF_FC.current_key]
        self.update_measurement(BTF_FC.current_pv, current)


class BTF_BCM(Device):
    #EPICS PV names
    current_pv = 'WF' # [A?]

    #PyORBIT parameter keys
    current_key = 'current'

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server
        self.register_measurement(BTF_BCM.current_pv)

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        bcm_params = new_params[self.model_name]
        current = bcm_params[BTF_BCM.current_key]
        self.update_measurement(BTF_BCM.current_pv, current)

class BTF_Quadrupole(Device):
    # EPICS PV names
    field_readback_pv = 'B' # [T/m]
    field_noise = 1e-6 # [T/m]

    # PyORBIT parameter keys
    field_key = 'dB/dr'

    def __init__ (self, name: str, model_name: str, power_supply: Device, polarity: Literal[-1,1] = None, coeff_a=None, coeff_b=None, length=None):

        self.model_name = model_name
        self.power_supply = power_supply
        self.coeff_a = coeff_a
        self.coeff_b = coeff_b
        self.length = length

        connected_devices = power_supply

        super().__init__(name, self.model_name, connected_devices)

        self.pol_transfrom = LinearTInv(scaler=polarity)
        field_noise = AbsNoise(noise=BTF_Quadrupole.field_noise)

        # Registers the device's PVs with the server
        self.register_readback(BTF_Quadrupole.field_readback_pv, noise=field_noise)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's values.
    # This is where the PV names are associated with their model keys.
    def get_settings(self):
        new_current = self.power_supply.get_setting(BTF_Quadrupole_Power_Supply.current_set_pv)
        sign = np.sign(new_current)
        new_current = np.abs(new_current)

        GL = sign*(self.coeff_a*new_current + self.coeff_b*new_current**2)

        new_field = - GL/self.length

        if self.model_name == 'MEBT:QV02':
            new_field = -new_field

        params_dict = {BTF_Quadrupole.field_key: new_field}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        rb_field = abs(self.get_settings()[self.model_name][BTF_Quadrupole.field_key])
        rb_param = self.readbacks[BTF_Quadrupole.field_readback_pv]
        rb_param.set_param(rb_field)



class BTF_Quadrupole_Power_Supply(Device):
    #field_set_pv = 'B_Set'  # [T/m]
    #field_readback_pv = 'B'  # [T/m]
    #field_noise = 1e-6  # [T/m]
    
    current_set_pv = 'I_Set' # [Amps]
    current_readback_pv = 'I' # [Amps]

    book_pv = 'B_Book'

    def __init__(self, name: str, init_current=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server.
        #field_param = self.register_setting(BTF_Quadrupole_Power_Supply.field_set_pv, default=init_field)
        #self.register_readback(BTF_Quadrupole_Power_Supply.field_readback_pv, field_param, noise=field_noise)

        #self.register_readback(BTF_Quadrupole_Power_Supply.book_pv, field_param)
        
        current_param = self.register_setting(BTF_Quadrupole_Power_Supply.current_set_pv, default=init_current)
        self.register_readback(BTF_Quadrupole_Power_Supply.current_readback_pv, current_param)
        
        self.register_readback(BTF_Quadrupole_Power_Supply.book_pv, current_param)
