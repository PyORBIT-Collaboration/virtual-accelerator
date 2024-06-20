import math
from typing import Dict

import numpy as np
from orbit.core.bunch import Bunch

# A collection of classes that are attached to the lattice as child nodes for the virtual accelerator.

class BTF_FCclass:
    def __init__(self, child_name: str):
        self.parameters = {'current': 0.0}
        self.child_name = child_name
        self.node_type = 'BTF_FC'
        self.si_e_charge = 1.6021773e-19

        super().__init__()

    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        
        if part_num > 0:
            initial_beam_current = paramsDict["beam_current"]
            initial_number = paramsDict['initial_particle_number']
            current = part_num / initial_number * initial_beam_current
            self.parameters['current'] = current
        else:
            self.parameters['current'] = 0.0

    def getCurrent(self):
        return self.parameters['current']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []

class BTF_FC_Objectclass:
    def __init__(self, child_name: str):
        self.parameters = {'state': 1}
        self.child_name = child_name
        self.node_type = 'BTF_FC_Object'
        self.si_e_charge = 1.6021773e-19

        super().__init__()

    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        dummt_value = 0

        live_state = self.parameters['state']
        if live_state == 1:
            if part_num > 0:
                bunch.deleteAllParticles()
            else:
                dummy_value = 1

        else:
            dummy_value = 1

    def getState(self):
        return self.parameters['state']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []

class BTF_BCMclass:
    def __init__(self, child_name: str):
        self.parameters = {'current': 0.0}
        self.child_name = child_name
        self.node_type = 'BTF_BCM'
        self.si_e_charge = 1.6021773e-19

    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            initial_beam_current = paramsDict["beam_current"]
            initial_number = paramsDict['initial_particle_number']
            current = part_num / initial_number * initial_beam_current
            self.parameters['current'] = current
        else:
            self.parameters['current'] = 0.0

    def getCurrent(self):
        return self.parameters['current']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []

class BTF_Screenclass:
    def __init__(self, child_name: str, screen_axis = None, screen_polarity = None, interaction = None):
        self.parameters = {'speed': 0.0, 'position': -0.07, 'axis': screen_axis, 'axis_polarity': screen_polarity, 'interaction_start': interaction}
        self.child_name = child_name
        self.node_type = 'BTF_Screen'
        self.si_e_charge = 1.6021773e-19
        self.near_bunch = 0.01 # value at which to start checking for particles
        
        # Set a standard value for the edge of the screen crossing the center of the bunch if none is specified
        if self.parameters['interaction_start'] is None:
            self.parameters['interaction_start'] = 0.03

        if self.parameters['axis_polarity'] is None:
            self.parameters['axis_polarity'] = 1
            print('No axis polarity set for', child_name+',', 'using standard value')

    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        
        # Bunch is centered at 0, a constant is added as screen position can only reach -16
        current_position = self.parameters['position'] + self.parameters['interaction_start']

        # The current position is adjusted to be negative or positive depending on what side of the beam pipe the actuator is on
        current_position = current_position * self.parameters['axis_polarity']

        axis = self.parameters['axis']
        part_num = bunch.getSizeGlobal()

        # Creating statements that determine what part of the bunch the screen will be deleting
        # Note this is set up assuming that all actuators work with an initial parked condition that is negative
        # If their park location is positive this set of if statements will work incorrectly

        if self.parameters['axis_polarity'] < 0 and current_position < self.near_bunch and part_num >0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x > current_position:
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y > current_position:
                        bunch.deleteParticleFast(n)
            else:
                print('screen axis not set correctly for', child_name)

        elif self.parameters['axis_polarity'] > 0 and current_position > -self.near_bunch and part_num >0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x < current_position:
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y < current_position:
                        bunch.deleteParticleFast(n)
            else:
                print('screen axis not set correctly for', self.child_name)


    def getSpeed(self):
        return self.parameters['speed']

    def getPosition(self):
        return self.parameters['position']

    def getAxis(self):
        return self.parameters['axis']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []

class BTF_Slitclass:
    def __init__(self, child_name: str, slit_axis = None, slit_polarity = None, interaction = None, edge_to_slit = None, slit_width = None):
        self.parameters = {'speed': 0.0, 'position': -0.07, 'axis': slit_axis, 'axis_polarity': slit_polarity,
                'interaction_start': interaction, 'edge_to_slit': edge_to_slit, 'slit_width': slit_width}
        self.child_name = child_name
        self.node_type = 'BTF_Slit'
        self.si_e_charge = 1.6021773e-19
        self.near_bunch = 0.01 # value at which to start checking for particles

        # Set a standard value for the edge of the screen crossing the center of the bunch if none is specified
        if self.parameters['interaction_start'] is None:
            self.parameters['interaction_start'] = 0.03

        if self.parameters['axis_polarity'] is None:
            self.parameters['axis_polarity'] = 1
            print('No axis polarity set for', child_name+',', 'using standard value')

        if self.parameters['edge_to_slit'] is None:
            self.parameters['edge_to_slit'] = 0.05

        if self.parameters['slit_width'] is None:
            self.parameters['slit_width'] = 0.0002


    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        
        # Bunch is centered at 0, a constant is added as screen position can only reach -16
        current_position = self.parameters['position'] + self.parameters['interaction_start']
        slit_position = current_position - self.parameters['edge_to_slit']

        # The current position is adjusted to be negative or positive depending on what side of the beam pipe the actuator is on
        current_position = current_position * self.parameters['axis_polarity']
        slit_position = slit_position * self.parameters['axis_polarity']

        axis = self.parameters['axis']
        part_num = bunch.getSizeGlobal()
        slit_width = self.parameters['slit_width']

        # Creating statements that determine what part of the bunch the screen will be deleting
        # Note this is set up assuming that all actuators work with an initial parked condition that is negative
        # If their park location is positive this set of if statements will work incorrectly

        if self.parameters['axis_polarity'] < 0 and current_position < self.near_bunch and part_num > 0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x > current_position and x < slit_position - slit_width * 0.5:
                        bunch.deleteParticleFast(n)
                    elif x > slit_position + slit_width * 0.5:
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y > current_position and y < slit_position - slit_width * 0.5:
                        print('why',n)
                        bunch.deleteParticleFast(n)
                    elif y > slit_position + slit_width * 0.5:
                        print('oh why',n)
                        bunch.deleteParticleFast(n)
            else:
                print('slit axis not set correctly for', self.child_name)

        elif self.parameters['axis_polarity'] > 0 and current_position > -self.near_bunch and part_num > 0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x < current_position and x > slit_position + slit_width * 0.5:
                        bunch.deleteParticleFast(n)
                        print('activated')
                    elif x < slit_position - slit_width * 0.5:
                        bunch.deleteParticleFast(n)
                        print('me too')
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y < current_position and y > slit_position + slit_width * 0.5:
                        bunch.deleteParticleFast(n)
                    elif y < slit_position - slit_width * 0.5:
                        bunch.deleteParticleFast(n)
            else:
                print('slit axis not set correctly for', self.child_name)

    def getSpeed(self):
        return self.parameters['speed']

    def getPosition(self):
        return self.parameters['position']

    def getAxis(self):
        return self.parameters['axis']

    def getParam(self, param: str):
        return self.parameters[param]

    def setParam(self, param: str, new_param):
        self.parameters[param] = new_param

    def getParamsDict(self) -> dict:
        return self.parameters

    def getType(self):
        return self.node_type

    def getName(self):
        return self.child_name

    def getAllChildren(self):
        return []






