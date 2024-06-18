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
    def __init__(self, child_name: str, screen_axis = None):
        self.parameters = {'speed': 0.0, 'position': -0.07, 'axis': screen_axis} # axis determines is screen is inserted horizontally (0), or vertically (1)
        self.child_name = child_name
        self.node_type = 'BTF_Screen'
        self.si_e_charge = 1.6021773e-19

    def trackActions(self, actionsCOntainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        
        current_position = self.parameters['position'] + 0.030 # Bunch is centered at 0, a constant is added as screen position can only reach -16
        axis = self.parameters['axis']
        part_num = bunch.getSizeGlobal()
        
        if current_position > -0.01: # Only starts checking particle location if the screen is near the bunch
            if part_num > 0:
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
                    print('screen axis not set correctly')
    
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
    def __init__(self, child_name: str, screen_axis = None):
        self.parameters = {'speed': 0.0, 'position': -0.07, 'axis': screen_axis} # axis determines is screen is inserted horizontally (0), or vertically (1)
        self.child_name = child_name
        self.node_type = 'BTF_Slit'
        self.si_e_charge = 1.6021773e-19

    def trackActions(self, actionsCOntainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        
        current_position = self.parameters['position'] + 0.030
        axis = self.parameters['axis']
        part_num = bunch.getSizeGlobal()
        edge_position = self.parameters['position'] + 0.040
        slit_width = 0.0002
        
        if edge_position > -0.01: # Only checks particles if edge of slit is near bunch
            if part_num > 0:
                if axis == 0:
                    for n in range(part_num):
                        x = bunch.x(n)
                        # Check position of particle and determine if it makes it through slit
                        if x < edge_position and x > current_position + slit_width * 0.5:
                            bunch.deleteParticleFast(n)
                        elif x < current_position - slit_width * 0.5:
                            bunch.deleteParticleFast(n)
                elif axis == 1:
                    for n in range(part_num):
                        y = bunch.y(n)
                        # Check position of particle and determine if it makes it through slit
                        if y < edge_position and y > current_position + slit_width * 0.5:
                            bunch.deleteParticleFast(n)
                        elif y < current_position - slit_width * 0.5:
                            bunch.deleteParticleFast(n)
                else:
                    print('slit axis not set correctly')

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






