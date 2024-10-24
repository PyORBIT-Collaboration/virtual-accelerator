import sys
import time
import math
from random import randint, random
from typing import Dict, Any, Union, Literal

import numpy as np
from virtaccl.site.SNS_Linac.virtual_devices import Cavity, Quadrupole, Corrector, WireScanner

from virtaccl.beam_line import Device, AbsNoise, LinearT, PhaseT, PhaseTInv, LinearTInv, PosNoise

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

class BTF_Actuator(Device):
    # EPICS PV names
    position_set_pv = 'DestinationSet' #[mm]
    position_readback_pv = 'PositionSync' # [mm]
    speed_set_pv = 'Velocity_Set' # [mm/s]
    speed_readback_pv = 'Velocity' # [mm/s]
    state_set_pv = 'Command'

    # Device keys
    position_key = 'position' # [m]
    speed_key = 'speed' # [m/s]

    def __init__(self, name: str, model_name: str, park_location = None, speed = None, limit = None):
        self.model_name = model_name
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        self.milli_units = LinearTInv(scaler=1e3)

        # Sets initial values for parameters.
        if park_location is not None:
            self.park_location = park_location
        else:
            self.park_location = -0.07

        if speed is not None:
            self.speed = speed
        else:
            self.speed = 0.0015

        if limit is not None:
            self.limit = limit
        else:
            self.limit = -0.016

        initial_state = 0
        initial_position = self.park_location
        initial_speed = self.speed

        # Defines internal parameters to keep track of the screen position
        self.last_actuator_pos = initial_position
        self.last_actuator_time = time.time()
        self.screen_speed = initial_speed
        self.current_state = initial_state

        initial_position = initial_position
        initial_speed = initial_speed
        
        # Creates flat noise for associated PVs
        pos_noise = AbsNoise(noise=1e-6)

        # Registers the device's PVs with the server
        speed_param = self.register_setting(BTF_Actuator.speed_set_pv, default=initial_speed, transform=self.milli_units)
        self.register_readback(BTF_Actuator.speed_readback_pv, speed_param, transform=self.milli_units)

        pos_param = self.register_setting(BTF_Actuator.position_set_pv, default = initial_position, transform=self.milli_units)
        self.register_readback(BTF_Actuator.position_readback_pv, pos_param, transform=self.milli_units, noise=pos_noise)

        state_param = self.register_setting(BTF_Actuator.state_set_pv, default = initial_state)

    # Function to find the position of the virtual screen using time of flight from the previous position and the speed of the screen
    def get_actuator_position(self):
        last_pos = self.last_actuator_pos
        last_time = self.last_actuator_time

        current_state = self.get_parameter_value(BTF_Actuator.state_set_pv)
        actuator_speed = self.get_parameter_value(BTF_Actuator.speed_set_pv)

        # Limit the speed of the actuator to the maximum speed of physical actuator
        if actuator_speed > self.speed:
            actuator_speed = self.speed

        if current_state == 1:
            pos_goal = self.get_parameter_value(BTF_Actuator.position_set_pv)

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

            #Defining where the actuator reaches the park location and should not be extracted further
            if self.park_location < 0 and pos_goal < self.park_location:
                pos_goal = self.park_location
            elif self.park_location > 0 and pos_goal > self.park_location:
                pos_goal = self.park_location

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
            pos_goal = self.park_location

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
    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        actuator_position = self.last_actuator_pos
        actuator_speed = self.get_parameter_value(BTF_Actuator.speed_set_pv)
        params_dict = {BTF_Actuator.position_key: actuator_position, BTF_Actuator.speed_key: actuator_speed}
        model_dict = {self.model_name: params_dict}
        return model_dict

    # For the input setting PV (not the readback PV), updates it's associated readback on the server using the model
    def update_readbacks(self):
        actuator_pos = BTF_Actuator.get_actuator_position(self)
        self.update_readback(BTF_Actuator.position_readback_pv, actuator_pos)
        
        # Readback set velocity value only when actuator is moving
        # Note: does not work if destinationset is outside available region
        if self.get_parameter_value(BTF_Actuator.state_set_pv) == 1 and actuator_pos != self.get_parameter_value(BTF_Actuator.position_set_pv):
            actuator_spd = self.get_parameter_value(BTF_Actuator.speed_set_pv)
        else:
            actuator_spd = 0
        self.update_readback(BTF_Actuator.speed_readback_pv, actuator_spd)


class BTF_FC(Device):
    #EPICS PV names
    current_pv = 'CurrentAvrGt' # [mA]
    state_set_pv = 'State_Set'
    state_readback_pv = 'State'
    current_noise = -7e-2

    #PyORBIT parameter keys
    current_key = 'current'
    state_key = 'state'

    def __init__(self, name: str, model_name: str = None, init_state=None):

        self.model_name = model_name
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        self.milli_units = LinearTInv(scaler=1e3)

        current_noise = PosNoise(noise=BTF_FC.current_noise)

        # Registers the device's PVs with the server
        self.register_measurement(BTF_FC.current_pv, noise=current_noise, transform = self.milli_units)

        self.register_setting(BTF_FC.state_set_pv, default=init_state)
        self.register_readback(BTF_FC.state_readback_pv, BTF_FC.state_set_pv)

    # Return the setting value of the PV name for the device as a dictionary using the model key and it's value. This is
    # where the PV names are associated with their model keys.
    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        new_state = self.get_parameter_value(BTF_FC.state_set_pv)

        params_dict = {BTF_FC.state_key: new_state}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        fc_state = self.get_parameter_value(BTF_FC.state_set_pv)
        self.update_readback(BTF_FC.state_readback_pv, fc_state)

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        current_state = self.get_parameter_value(BTF_FC.state_set_pv)

        if current_state == 1:
            fc_params = new_params[self.model_name]
            current = -1.0*fc_params[BTF_FC.current_key]
        else:
            current = 0
        self.update_measurement(BTF_FC.current_pv, current)


class BTF_BCM(Device):
    #EPICS PV names
    current_pv = 'CurrentAvrGt' # [mA]
    current_noise = -7e-2

    #PyORBIT parameter keys
    current_key = 'current'

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Changes the units from meters to millimeters for associated PVs.
        self.milli_units = LinearTInv(scaler=1e3)

        current_noise = PosNoise(noise=BTF_BCM.current_noise)

        # Registers the device's PVs with the server
        self.register_measurement(BTF_BCM.current_pv, noise=current_noise, transform=self.milli_units)

    # Updates the measurement values on the server. Needs the model key associated with its value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        bcm_params = new_params[self.model_name]
        current = -1.0*bcm_params[BTF_BCM.current_key]
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
    def get_current_from_PS(self):
        new_current = self.power_supply.get_parameter_value(BTF_Quadrupole_Power_Supply.current_set_pv)
        sign = np.sign(new_current)
        new_current = np.abs(new_current)

        GL = sign*(self.coeff_a*new_current + self.coeff_b*new_current**2)

        new_field = - GL/self.length

        if self.model_name == 'MEBT:QV02':
            new_field = -new_field

        return new_field

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        new_field = self.get_current_from_PS()

        params_dict = {BTF_Quadrupole.field_key: new_field}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        rb_field = self.get_current_from_PS()
        self.update_readback(BTF_Quadrupole.field_readback_pv, rb_field)



class BTF_Quadrupole_Power_Supply(Device):
    current_set_pv = 'I_Set' # [Amps]
    current_readback_pv = 'I' # [Amps]

    def __init__(self, name: str, init_current=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        self.register_setting(BTF_Quadrupole_Power_Supply.current_set_pv, default=init_current)
        self.register_readback(BTF_Quadrupole_Power_Supply.current_readback_pv, BTF_Quadrupole_Power_Supply.current_set_pv)

class BTF_Corrector(Device):
    # EPICS PV names
    field_readback_pv = 'B'  # [T]
    field_noise = 1e-6  # [T/m]

    # PyORBIT parameter keys
    field_key = 'B'  # [T]

    def __init__ (self, name: str, model_name: str, power_supply: Device, coeff=None, length=None, momentum=None):

        self.model_name = model_name
        self.power_supply = power_supply
        self.coeff = coeff
        self.length = length
        self.momentum = momentum

        super().__init__(name, self.model_name, self.power_supply)

        field_noise = AbsNoise(noise=BTF_Corrector.field_noise)

        # Registers the device's PVs with the server
        self.register_readback(BTF_Corrector.field_readback_pv, noise=field_noise)

    def get_current_from_PS(self):
        new_current = self.power_supply.get_parameter_value(BTF_Corrector_Power_Supply.current_set_pv)

        new_field = (self.coeff * 1e-3 * new_current * self.momentum) / (self.length * 0.299792)

        return new_field

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        new_field = self.get_current_from_PS()

        params_dict = {BTF_Corrector.field_key: new_field}
        model_dict = {self.model_name: params_dict}
        return model_dict

    def update_readbacks(self):
        rb_field = self.get_current_from_PS()
        self.update_readback(BTF_Corrector.field_readback_pv, rb_field)

class BTF_Corrector_Power_Supply(Device):
    current_set_pv = 'I_Set' # [Amps]
    current_readback_pv = 'I' # [Amps]

    def __init__(self, name: str, init_current=None):
        super().__init__(name)

        field_noise = AbsNoise(noise=1e-6)

        self.register_setting(BTF_Corrector_Power_Supply.current_set_pv, default=init_current)
        self.register_readback(BTF_Corrector_Power_Supply.current_readback_pv, BTF_Corrector_Power_Supply.current_set_pv)

