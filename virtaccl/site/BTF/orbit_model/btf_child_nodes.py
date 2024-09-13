import math
from typing import Dict

import numpy as np
from orbit.core.bunch import Bunch
from orbit.py_linac.lattice import BaseLinacNode


# A collection of classes that are attached to the lattice as child nodes for the virtual accelerator.

class BTF_Screenclass(BaseLinacNode):
    node_type = "BTF_Screen"
    parameter_list = ['speed', 'position', 'axis', 'axis_polarity', 'interaction_start']

    def __init__(self, child_name: str, screen_axis=None, screen_polarity=None, interaction=None):
        parameters = {'speed': 0.0, 'position': -0.07, 'axis': screen_axis, 'axis_polarity': screen_polarity,
                      'interaction_start': interaction}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(BTF_Screenclass.node_type)
        self.si_e_charge = 1.6021773e-19
        self.near_bunch = 0.015  # value at which to start checking for particles

        # Set a standard value for the edge of the screen crossing the center of the bunch if none is specified
        if self.getParam('interaction_start') is None:
            self.setParam('interaction_start', 0.03)

        if self.getParam('axis_polarity') is None:
            self.setParam('axis_polarity', 1)
            print('No axis polarity set for', child_name + ',', 'using standard value')

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]

        # Bunch is centered at 0, a constant is added as screen position can only reach -16
        current_position = self.getParam('position') + self.getParam('interaction_start')

        # The current position is adjusted to be negative or positive depending on what side of the beam pipe the actuator is on
        current_position = current_position * self.getParam('axis_polarity')

        axis = self.getParam('axis')
        part_num = bunch.getSizeGlobal()

        # Create a dummy value that is changed if particles are lost, changing this value causes a bunch.compress() to happen
        value = 0

        # Creating statements that determine what part of the bunch the screen will be deleting
        # Note this is set up assuming that all actuators work with an initial parked condition that is negative
        # If their park location is positive this set of if statements will work incorrectly

        if self.getParam('axis_polarity') < 0 < part_num and current_position < self.near_bunch:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x > current_position:
                        value = 1
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y > current_position:
                        value = 1
                        bunch.deleteParticleFast(n)
            else:
                print('screen axis not set correctly for', self.child_name)

        elif self.getParam('axis_polarity') > 0 and current_position > -self.near_bunch and part_num > 0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x < current_position:
                        value = 1
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y < current_position:
                        value = 1
                        bunch.deleteParticleFast(n)
            else:
                print('screen axis not set correctly for', self.child_name)

        if value == 1:
            bunch.compress()

    def getSpeed(self):
        return self.getParam('speed')

    def getPosition(self):
        return self.getParam('position')

    def getAxis(self):
        return self.getParam('axis')

    def getAxis_Polarity(self):
        return self.getParam('axis_polarity')

    def getInteraction_Start(self):
        return self.getParam('interaction_start')


class BTF_Slitclass(BaseLinacNode):
    node_type = "BTF_Slit"
    parameter_list = ['speed', 'position', 'axis', 'axis_polarity', 'interaction_start', 'edge_to_slit', 'slit_width']

    def __init__(self, child_name: str, slit_axis=None, slit_polarity=None, interaction=None, edge_to_slit=None,
                 slit_width=None):
        parameters = {'speed': 0.0, 'position': -0.07, 'axis': slit_axis, 'axis_polarity': slit_polarity,
                      'interaction_start': interaction, 'edge_to_slit': edge_to_slit, 'slit_width': slit_width}
        BaseLinacNode.__init__(self, child_name)
        for key, value in parameters.items():
            self.addParam(key, value)
        self.child_name = child_name
        self.setType(BTF_Slitclass.node_type)
        self.si_e_charge = 1.6021773e-19
        self.near_bunch = 0.01  # value at which to start checking for particles

        # Set a standard value for the edge of the screen crossing the center of the bunch if none is specified
        if self.getParam('interaction_start') is None:
            self.setParam('interaction_start', 0.03)

        if self.getParam('axis_polarity') is None:
            self.setParam('axis_polarity', 1)
            print('No axis polarity set for', child_name + ',', 'using standard value')

        if self.getParam('edge_to_slit') is None:
            self.setParam('edge_to_slit', 0.05)

        if self.getParam('slit_width') is None:
            self.setParam('slit_width', 0.0002)

    def track(self, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]

        # Bunch is centered at 0, a constant is added as screen position can only reach -16
        current_position = self.getParam('position') + self.getParam('interaction_start')
        slit_position = current_position - self.getParam('edge_to_slit')

        # The current position is adjusted to be negative or positive depending on what side of the beam pipe the actuator is on
        current_position = current_position * self.getParam('axis_polarity')
        slit_position = slit_position * self.getParam('axis_polarity')

        axis = self.getParam('axis')
        part_num = bunch.getSizeGlobal()
        slit_width = self.getParam('slit_width')

        # Create a dummy value that is changed if particles are lost, changing this value causes a bunch.compress() to happen
        value = 0

        # Creating statements that determine what part of the bunch the screen will be deleting
        # Note this is set up assuming that all actuators work with an initial parked condition that is negative
        # If their park location is positive this set of if statements will work incorrectly

        if self.getParam('axis_polarity') < 0 and current_position < self.near_bunch and part_num > 0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x > current_position and x < slit_position - slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
                    elif x > slit_position + slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y > current_position and y < slit_position - slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
                    elif y > slit_position + slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
            else:
                print('slit axis not set correctly for', self.child_name)

        elif self.getParam('axis_polarity') > 0 and current_position > -self.near_bunch and part_num > 0:
            if axis == 0:
                for n in range(part_num):
                    x = bunch.x(n)
                    if x < current_position and x > slit_position + slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
                    elif x < slit_position - slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
            elif axis == 1:
                for n in range(part_num):
                    y = bunch.y(n)
                    if y < current_position and y > slit_position + slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
                    elif y < slit_position - slit_width * 0.5:
                        value = 1
                        bunch.deleteParticleFast(n)
            else:
                print('slit axis not set correctly for', self.child_name)

        if value == 1:
            bunch.compress()

    def getSpeed(self):
        return self.getParam('speed')

    def getPosition(self):
        return self.getParam('position')

    def getAxis(self):
        return self.getParam('axis')

    def getAxis_Polarity(self):
        return self.getParam('axis_polarity')

    def getInteraction_Start(self):
        return self.getParam('interaction_start')

    def getEdge_to_Slit(self):
        return self.getParam('edge_to_slit')

    def getSlit_Width(self):
        return self.getParam('slit_width')
