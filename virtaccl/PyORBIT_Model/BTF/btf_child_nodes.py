import math
from typing import Dict

import numpy as np
from orbit.core.bunch import Bunch


# A collection of classes that are attached to the lattice as child nodes for the virtual accelerator.

class BTF_FCclass:
    def __init__(self, child_name: str):
        self.parameters = {'current': 0.0, 'state': 1}
        self.child_name = child_name
        self.node_type = 'BTF_FC'
        self.si_e_charge = 1.6021773e-19

        super().__init__()

    def trackActions(self, actionsContainer, paramsDict):
        if "bunch" not in paramsDict:
            return
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()

        live_state = self.parameters['state']
        print('child', live_state)
        if live_state == 1:
            if part_num > 0:
                initial_beam_current = paramsDict["beam_current"]
                initial_number = paramsDict['initial_particle_number']
                current = part_num / initial_number * initial_beam_current
                self.parameters['current'] = current
                bunch.deleteAllParticles()
            else:
                self.parameters['current'] = 0.0

        else:
            self.parameters['current'] =  0.0

    def getCurrent(self):
        return self.parameters['current']

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
