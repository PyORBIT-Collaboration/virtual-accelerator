from typing import Union
from functools import partial

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity


class PVDict:
    node_types = {'markerLinacNode', 'linacQuad', 'RF_Cavity', 'dch', 'dcv'}
    pv_types = {'setting', 'readback', 'diagnostic', 'physics'}

    def __init__(self, acc_lattice: LinacAccLattice):
        self.acc_lattice = acc_lattice
        self.pv_dict = {}

    def add_pv(self, pv_name: str, pv_type: str, node: Union[Quad, MarkerLinacNode, DCorrectorV, DCorrectorH, RF_Cavity]
               , node_param: str):
        if pv_type not in self.pv_types:
            raise ValueError(f'Invalid input. Allowed pv types are {self.pv_types}.')

        if isinstance(node, RF_Cavity):
            node_type = 'RF_Cavity'
            node_get = partial(node.getParam, node_param)
            if pv_type == 'setting':
                node_set = partial(node.setParam, node_param)
                new_pv = PVClass(pv_type, node, node_type, node_get, node_set)
            else:
                new_pv = PVClass(pv_type, node, node_type, node_get)

        elif isinstance(node, MarkerLinacNode):
            node_type = 'markerLinacNode'
            bpm_node = node.getChildNodes(node.ENTRANCE)[0]
            node_get = partial(bpm_node.getParam, node_param)
            if pv_type == 'setting':
                node_set = partial(bpm_node.setParam, node_param)
                new_pv = PVClass(pv_type, node, node_type, node_get, node_set)
            else:
                new_pv = PVClass(pv_type, node, node_type, node_get)

        elif isinstance(node, Quad):
            node_type = 'linacQuad'
            node_get = partial(node.getParam, node_param)
            if pv_type == 'setting':
                node_set = partial(node.setParam, node_param)
                new_pv = PVClass(pv_type, node, node_type, node_get, node_set)
            else:
                new_pv = PVClass(pv_type, node, node_type, node_get)

        elif isinstance(node, DCorrectorH):
            node_type = 'dch'
            node_get = partial(node.getParam, node_param)
            if pv_type == 'setting':
                node_set = partial(node.setParam, node_param)
                new_pv = PVClass(pv_type, node, node_type, node_get, node_set)
            else:
                new_pv = PVClass(pv_type, node, node_type, node_get)

        elif isinstance(node, DCorrectorV):
            node_type = 'dcv'
            node_get = partial(node.getParam, node_param)
            if pv_type == 'setting':
                node_set = partial(node.setParam, node_param)
                new_pv = PVClass(pv_type, node, node_type, node_get, node_set)
            else:
                new_pv = PVClass(pv_type, node, node_type, node_get)

        else:
            raise ValueError(f'Invalid input. Allowed node types are {self.node_types}.')

        self.pv_dict[pv_name] = new_pv

    def get_pv(self, pv_name: str) -> "PVClass":
        return self.pv_dict[pv_name]

    def get_pv_dict(self) -> dict:
        return self.pv_dict

    def order_pvs(self):
        self.pv_dict = dict(sorted(self.pv_dict.items(), key=lambda item: item[1].get_position()))


class PVClass:

    def __init__(self, pv_type: str, node: Union[Quad, MarkerLinacNode, DCorrectorV, DCorrectorH, RF_Cavity],
                 node_type: str, node_get: partial, node_set: partial = None):

        self.pv_type = pv_type
        self.node = node
        self.node_type = node_type
        self.node_get = node_get
        self.node_set = node_set
        self.position = self.node.getPosition()
        self.pv_value = self.node_get()

    def get_value(self) -> float:
        if self.pv_type == 'setting':
            if isinstance(self.node, RF_Cavity):
                if not self.node.getParam('blanked'):
                    self.pv_value = self.node_get()
                return self.pv_value
            else:
                self.pv_value = self.node_get()
                return self.pv_value

        elif self.pv_type == 'readback':
            if isinstance(self.node, RF_Cavity):
                self.pv_value = self.node_get()
                return self.pv_value
            else:
                self.pv_value = self.node_get()
                return self.pv_value

        elif self.pv_type == 'diagnostic':
            self.pv_value = self.node_get()
            return self.pv_value

        if self.pv_type == 'physics':
            self.pv_value = self.node_get()
            return self.pv_value

    def set_value(self, new_value):
        if self.pv_type == 'setting':
            self.pv_value = new_value
            self.node_set(new_value)
            if isinstance(self.node, RF_Cavity) and self.node.getParam('blanked'):
                self.node.setAmp(0.0)
        else:
            print("Invalid PV type. PV type must be 'setting' to change its value.")

    def get_pv_type(self):
        return self.pv_type

    def get_node_type(self):
        return self.node_type

    def get_node_name(self):
        return self.node.getName()

    def get_position(self):
        return self.position
