import sys
from pathlib import Path
from typing import Union
from functools import partial

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from bpm_child_node import BPMclass


class nodeDict:

    def __init__(self, acc_lattice: LinacAccLattice, ignored_nodes: set = None):
        self.acc_lattice = acc_lattice

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.
        unique_nodes = set()
        if ignored_nodes is None:
            ignored_nodes = {'drift', 'tilt', 'fringe', 'markerLinacNode'}
        list_of_nodes = self.acc_lattice.getNodes()

        def create_node_dict(node_list, node_dict=None, level=0, location_node=None):
            if node_dict is None:
                node_dict = {}
            for node in node_list:
                node_type = node.getType()
                if level == 0:
                    location_node = node
                if not any(substring in node_type for substring in ignored_nodes):
                    if node.getType() == 'baserfgap':
                        node_ref = node.getRF_Cavity()
                    else:
                        node_ref = node
                    node_name = node_ref.getName()
                    if node_name not in unique_nodes:
                        unique_nodes.add(node_name)
                        if level == 0:
                            if location_node.getType() == 'baserfgap':
                                location_node = node.getRF_Cavity().getRF_GapNodes()[0]
                                node_dict[node_name] = nodeRefClass(node_ref, location_node)
                            else:
                                node_dict[node_name] = nodeRefClass(node_ref)
                        else:
                            node_dict[node_name] = nodeRefClass(node_ref, location_node)
                children = node.getAllChildren()
                if len(children) > 0:
                    create_node_dict(children, node_dict, level + 1, location_node)
            return node_dict

        self.node_dict = create_node_dict(list_of_nodes)

    def get_nodeRef(self, node_name: str) -> "nodeRefClass":
        return self.node_dict[node_name]

    def get_node_dict(self) -> dict[str, "nodeRefClass"]:
        return self.node_dict

    def get_node(self, node_name: str):
        node = self.node_dict[node_name].get_node()
        return node

    def get_location_node(self, node_name: str):
        location_node = self.node_dict[node_name].get_location_node()
        return location_node

    def get_location_node_name(self, node_name: str):
        location_name = self.node_dict[node_name].get_location_name()
        return location_name

    def get_node_position(self, node_name: str) -> float:
        position = self.node_dict[node_name].get_position()
        return position

    def get_node_index(self, node_name: str) -> int:
        node_ref = self.node_dict[node_name]
        if node_ref.get_location_node() is None:
            location_node = node_ref.get_node()
        else:
            location_node = node_ref.get_location_node()
        node_index = self.acc_lattice.getNodeIndex(location_node)
        return node_index

    def get_node_paramsDict(self, node_name: str) -> dict[str,]:
        params_dict = self.node_dict[node_name].get_paramsDict()
        return params_dict

    def set_node_paramsDict(self, node_name: str, new_params: dict) -> None:
        self.node_dict[node_name].set_paramsDict(new_params)

    def get_node_param(self, node_name: str, param_key: str):
        param = self.node_dict[node_name].get_param(param_key)
        return param

    def set_node_param(self, node_name: str, param_key: str, new_param) -> None:
        self.node_dict[node_name].set_param(param_key, new_param)


class nodeRefClass:
    node_types = Union[Quad, DCorrectorV, DCorrectorH, RF_Cavity, BPMclass, MarkerLinacNode]

    def __init__(self, node: node_types, location_node: node_types = None):
        self.node = node
        self.location_node = location_node
        self.params_dict_override = node.getParamsDict()

    def get_node(self) -> node_types:
        return self.node

    def get_location_node(self) -> node_types:
        return self.location_node

    def get_location_name(self) -> str:
        if self.location_node is None:
            location_name = self.node.getName()
        else:
            location_name = self.location_node.getName()
        return location_name

    def get_position(self) -> float:
        if self.location_node is None:
            position = self.node.getPosition()
        else:
            position = self.location_node.getPosition()
        return position

    def get_paramsDict(self) -> dict[str,]:
        node = self.node
        params_dict = node.getParamsDict()
        if isinstance(node, RF_Cavity) and node.getParam('blanked'):
            params_dict['amp'] = self.params_dict_override['amp']
        return params_dict

    def set_paramsDict(self, new_params: dict) -> None:
        node = self.node
        node.setParamsDict(new_params)
        self.params_dict_override = new_params
        if isinstance(node, RF_Cavity) and node.getParam('blanked'):
            node.setAmp(0.0)

    def get_param(self, param_key: str):
        node = self.node
        if isinstance(node, RF_Cavity) and param_key == 'amp' and node.getParam('blanked'):
            param = self.params_dict_override[param_key]
        else:
            param = node.getParam(param_key)
        return param

    def set_param(self, param_key: str, new_param) -> None:
        node = self.node
        node.setParam(param_key, new_param)
        if isinstance(node, RF_Cavity) and node.getParam('blanked'):
            node.setAmp(0.0)


class PVDict:
    allowed_pv_types = {'setting', 'readback', 'diagnostic', 'physics'}

    def __init__(self, node_dict: nodeDict):
        self.node_dict = node_dict
        self.pv_dict = {}

    def add_pv(self, pv_name: str, pv_types: list[str], node_name: str, param_key: str):
        bad_pv_types = [pv_type for pv_type in pv_types if pv_type not in self.allowed_pv_types]
        if bad_pv_types:
            print("Unrecognized PV types:", ", ".join(bad_pv_types))

        new_pv = PVClass(pv_types, node_name, param_key, self.node_dict)

        self.pv_dict[pv_name] = new_pv

    def get_pv_ref(self, pv_name: str) -> "PVClass":
        return self.pv_dict[pv_name]

    def get_pvref_dict(self) -> dict[str, "PVClass"]:
        return self.pv_dict

    def get_pvs(self) -> dict[str,]:
        pv_dict = {}
        for key, pv_ref in self.pv_dict.items():
            value = pv_ref.get_value()
            pv_dict[key] = value
        return pv_dict

    def set_pvs(self, new_values: dict) -> None:
        for key, new_value in new_values.items():
            self.pv_dict[key].set_value(new_value)

    def get_pv(self, pv_name: str):
        value = self.pv_dict[pv_name].get_value()
        return value

    def set_pv(self, pv_name: str, new_value) -> None:
        self.pv_dict[pv_name].set_value(new_value)

    def get_pv_types(self, pv_name: str) -> list[str]:
        pv_types = self.pv_dict[pv_name].get_types()
        return pv_types

    def get_node_name(self, pv_name: str) -> str:
        node_name = self.pv_dict[pv_name].get_node_name()
        return node_name

    def order_pvs(self):
        pv_dict = self.pv_dict
        temp_dict = {}
        for key, pv in pv_dict.items():
            node_name = pv.get_node_name()
            index = self.node_dict.get_node_index(node_name)
            temp_dict[key] = index
        temp_dict = dict(sorted(temp_dict.items(), key=lambda item: item[1]))
        sorted_pv_dict = {}
        for key, position in temp_dict.items():
            sorted_pv_dict[key] = pv_dict[key]
        self.pv_dict = sorted_pv_dict


class PVClass:

    def __init__(self, pv_types: list[str], node_name: str, param_key: str, node_dict: "nodeDict"):

        self.pv_types = pv_types
        self.param_key = param_key
        self.node_name = node_name
        self.node_dict = node_dict

    def get_value(self):
        param = self.node_dict.get_node_param(self.node_name, self.param_key)
        return param

    def set_value(self, new_value) -> None:
        if any('setting' for pv_type in self.pv_types):
            self.node_dict.set_node_param(self.node_name, self.param_key, new_value)
        else:
            print("Invalid PV type. PV type must be 'setting' to change its value.")

    def get_types(self) -> list[str]:
        return self.pv_types

    def get_param_key(self) -> str:
        return self.param_key

    def get_node_name(self) -> str:
        return self.node_name
