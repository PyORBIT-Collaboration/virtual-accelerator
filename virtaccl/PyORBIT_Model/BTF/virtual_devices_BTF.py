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

class BTF_Actuator(Device):
    # EPICS PV names
    position_set_pv = 'DestinationSet' #[mm]
    position_readback_pv = 'Position' # [mm]
    speed_set_pv = 'Speed_Set' # [mm/s]
    speed_readback_pv = 'Speed' # [mm/s]
    state_set_pv = 'COMMAND'
    state_readback_pv = 'COMMAND_RB'

    # Device keys
    position_key = 'position' # [m]
    speed_key = 'speed' # [m/s]

    def __init__(self, name: str, model_name: str, park_location = None, speed = None, limit = None):
        self.model_name = model_name
        self.park_location = park_location
        self.speed = speed
        self.limit = limit
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        self.milli_units = LinearTInv(scaler=1e3)
        
        # Sets initial values for parameters.
        initial_state = 0
        initial_position = self.park_location
        initial_speed = self.speed

        if park_location is None or speed is None or limit is None:
            print('Missing initial conditions for',self.model_name+',','using preset values')
            print('park_location', park_location)
            print('speed', speed)
            print('limit', limit)
            initial_position = -0.07
            initial_speed = 0.0015
            self.limit = -0.016
            self.park_location = -0.07

        # Defines internal parameters to keep track of the screen position
        self.last_actuator_pos = initial_position
        self.last_actuator_time = time.time()
        self.screen_speed = initial_speed
        self.current_state = initial_state

        initial_position = self.milli_units.raw(initial_position)
        initial_speed = self.milli_units.raw(initial_speed)

        # Creates flat noise for associated PVs
        pos_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server
        speed_param = self.register_setting(BTF_Actuator.speed_set_pv, default=initial_speed, transform=self.milli_units)
        self.register_readback(BTF_Actuator.speed_readback_pv, speed_param, transform=self.milli_units)

        pos_param = self.register_setting(BTF_Actuator.position_set_pv, default = initial_position, transform = self.milli_units)
        self.register_readback(BTF_Actuator.position_readback_pv, pos_param, transform=self.milli_units, noise=pos_noise)

        state_param = self.register_setting(BTF_Actuator.state_set_pv, default = initial_state)
        self.register_readback(BTF_Actuator.state_readback_pv, state_param)

    # Function to find the position of the virtual screen using time of flight from the previous position and the speed of the screen
    def get_actuator_position(self):
        last_pos = self.last_actuator_pos
        last_time = self.last_actuator_time

        current_state = self.get_setting(BTF_Actuator.state_set_pv)
        actuator_speed = self.get_setting(BTF_Actuator.speed_set_pv)

        # Limit the speed of the actuator to the maximum speed of physical actuator
        if actuator_speed > self.speed:
            actuator_speed = self.speed

        if current_state == 1:
            pos_goal = self.get_setting(BTF_Actuator.position_set_pv)

            # Defining where the actuator reaches the limit it can insert and should not be moved past
            # Multiple cases needed to ensure it correctly determines limit
            if self.limit < 0 and self.park_location < 0 and pos_goal > self.limit:
                pos_goal = self.limit
            elif self.limit < 0 and self.park_location > 0 and pos_goal < self.limit:
                pos_goal = self.limit
            elif self.limit > 0  and self.park_location < 0 and pos_goal > self.limit:
                pos_goal = self.limit
            elif self.limit > 0 and self.park_location > 0 and pos_goal < self.limit:
                pos_goal = self.limit

            direction = np.sign(pos_goal - last_pos)
            current_time = time.time()
            actuator_pos = direction * actuator_speed * (current_time - last_time) + last_pos

            if last_pos == pos_goal:
                actuator_pos = pos_goal
            elif direction < 0 and actuator_pos < pos_goal:
                actuator_pos = pos_goal
            elif direction > 0 and actuator_pos > pos_goal:
                actuator_pos = pos_goal

        elif current_state == 2:
            actuator_pos = last_pos
            current_time = time.time()

        elif current_state == 0:
            pos_goal = -0.070 # position of parked BTF actuator

            direction = np.sign(pos_goal - last_pos)
            current_time = time.time()
            actuator_pos = direction * actuator_speed * (current_time - last_time) + last_pos

            if last_pos == pos_goal:
                actuator_pos = pos_goal
            elif direction < 0 and actuator_pos < pos_goal:
                actuator_pos = pos_goal
            elif direction > 0 and actuator_pos > pos_goal:
                actuator_pos = pos_goal

        else:
            actuator_pos = last_pos
            current_time = time.time()
        
        # Reset variables for the next calculation
        self.last_actuator_time = current_time
        self.last_actuator_pos = actuator_pos

        return actuator_pos

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value.
    # This is where the setting PV names are associated with their model keys
    def get_settings(self):
        actuator_position = self.last_actuator_pos
        actuator_speed = self.settings[BTF_Actuator.speed_set_pv].get_param()
        params_dict = {BTF_Actuator.position_key: actuator_position, BTF_Actuator.speed_key: actuator_speed}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model
    def update_readbacks(self):
        actuator_pos = BTF_Actuator.get_actuator_position(self)
        self.update_readback(BTF_Actuator.position_readback_pv, actuator_pos)


class BTF_FC(Device):
    #EPICS PV names
    current_pv = 'WF' # [A]
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
        new_state = self.settings[BTF_FC.state_set_pv].get_param()
         
        params_dict = {BTF_FC.state_key: new_state}
        model_dict = {self.model_name+'_obj': params_dict}
        return model_dict

    def update_readbacks(self):
        fc_state = self.get_settings()[self.model_name+'_obj'][BTF_FC.state_key]
        rb_param = self.readbacks[BTF_FC.state_readback_pv]
        rb_param.set_param(fc_state)
        
    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        current_state = self.settings[BTF_FC.state_set_pv].get_param()
        
        if current_state == 1:
            fc_params = new_params[self.model_name]
            current = fc_params[BTF_FC.current_key]
        else:
            current = 0
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

    def __init__ (self, name: str, model_name: str, power_supply: Device, coeff_a=None, coeff_b=None, length=None):

        self.model_name = model_name
        self.power_supply = power_supply
        self.coeff_a = coeff_a
        self.coeff_b = coeff_b
        self.length = length

        connected_devices = power_supply

        super().__init__(name, self.model_name, connected_devices)

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
    current_set_pv = 'I_Set' # [Amps]
    current_readback_pv = 'I' # [Amps]

    def __init__(self, name: str, init_current=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        current_param = self.register_setting(BTF_Quadrupole_Power_Supply.current_set_pv, default=init_current)
        self.register_readback(BTF_Quadrupole_Power_Supply.current_readback_pv, current_param)
