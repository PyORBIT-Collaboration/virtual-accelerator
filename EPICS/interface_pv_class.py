from typing import Union

from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity


class PV:
    marker_type = "orbit.py_linac.lattice.LinacAccNodes.MarkerLinacNode"
    quad_type = "orbit.py_linac.lattice.LinacAccNodes.Quad"
    rf_type = "orbit.py_linac.lattice.LinacAccLatticeLib.RF_Cavity"

    node_types = {'MarkerLinacNode', 'Quad', 'RF_Cavity'}

    pv_types = {'setting', 'readback', 'diagnostic', 'physics'}

    def __init__(self, pv_name: str, pv_type: str, node: Union[MarkerLinacNode, Quad, RF_Cavity],
                 node_get: classmethod, node_set: classmethod = None):

        if pv_type not in self.pv_types:
            raise ValueError(f'Invalid input. Allowed pv types are {self.pv_types}.')
        self.pv_name = pv_name
        self.node = node
        self.node_get = node_get
        self.node_set = node_set
        self.node_name = node.getName()
        if isinstance(self.node, MarkerLinacNode):
            self.node_type = 'MarkerLinacNode'
        elif isinstance(self.node, Quad):
            self.node_type = 'Quad'
        elif isinstance(self.node, RF_Cavity):
            self.node_type = 'RF_Cavity'
        else:
            raise ValueError(f'Invalid input. Allowed nodes are {self.node_types}.')
        self.position = self.node.getPosition()
        self.pv_value = self.node_get()
        self.pv_type = pv_type

    def get_value(self) -> float:
        if self.pv_type == 'setting':
            if isinstance(self.node, RF_Cavity):
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
        else:
            print("Invalid PV type. PV type must be 'setting' to change its value.")

    def get_pv_type(self):
        return self.pv_type

    def get_node_type(self):
        return self.node_type

    def get_node_name(self):
        return self.node_name

    def get_pv_name(self):
        return self.pv_name

    def get_position(self):
        return self.position
