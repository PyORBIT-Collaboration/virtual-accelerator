from typing import Union, Dict

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from server_child_nodes import BPMclass


class PyorbitElementTypes:
    node_classes = Union[Quad, BaseRF_Gap, MarkerLinacNode]
    cavity_classes = RF_Cavity
    child_classes = Union[DCorrectorV, DCorrectorH, BPMclass]


class PyorbitLibrary:
    node_classes = Union[Quad, BaseRF_Gap, MarkerLinacNode]
    cavity_classes = RF_Cavity
    child_classes = Union[DCorrectorV, DCorrectorH, BPMclass]

    def __init__(self, acc_lattice: LinacAccLattice, ignored_nodes=None):
        if ignored_nodes is None:
            ignored_nodes = set()
        ignored_nodes |= {'baserfgap', 'drift', 'tilt', 'fringe', 'markerLinacNode', 'baseLinacNode'}
        unique_elements = set()

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.

        self.acc_lattice = acc_lattice
        element_dict_hint = Dict[str, PyorbitElement]
        element_dict: element_dict_hint = {}

        def add_child_nodes(ancestor_node, children_nodes, element_dictionary):
            for child in children_nodes:
                child_type = child.getType()
                if not any(substring in child_type for substring in ignored_nodes):
                    child_name = child.getName()
                    if child_name not in unique_elements:
                        unique_elements.add(child_name)
                        element_dictionary[child_name] = PyorbitChild(child, ancestor_node)
                grandchildren = child.getAllChildren()
                if len(grandchildren) > 0:
                    add_child_nodes(ancestor_node, grandchildren, element_dictionary)

        list_of_nodes = self.acc_lattice.getNodes()
        for node in list_of_nodes:
            node_type = node.getType()
            if not any(substring in node_type for substring in ignored_nodes):
                element_name = node.getName()
                if element_name not in unique_elements:
                    unique_elements.add(element_name)
                    element_dict[element_name] = PyorbitNode(node)
            children = node.getAllChildren()
            if len(children) > 0:
                add_child_nodes(node, children, element_dict)

        list_of_cavities = self.acc_lattice.getRF_Cavities()
        for cavity in list_of_cavities:
            element_name = cavity.getName()
            unique_elements.add(element_name)
            element_dict[element_name] = PyorbitCavity(cavity)

        self.pyorbit_dictionary = element_dict

    def get_element_reference(self, pyorbit_name: str) -> "PyorbitElement":
        return self.pyorbit_dictionary[pyorbit_name]

    def get_element_dictionary(self) -> dict[str, "PyorbitElement"]:
        return self.pyorbit_dictionary

    def get_element(self, pyorbit_name: str) -> Union[node_classes, cavity_classes, child_classes]:
        element = self.pyorbit_dictionary[pyorbit_name].get_element()
        return element

    def get_element_position(self, pyorbit_name: str) -> float:
        position = self.pyorbit_dictionary[pyorbit_name].get_position()
        return position

    def get_location_node(self, pyorbit_name: str) -> node_classes:
        location_node = self.pyorbit_dictionary[pyorbit_name].get_tracking_node()
        return location_node

    def get_location_name(self, pyorbit_name: str) -> str:
        location_node_name = self.get_location_node(pyorbit_name).getName()
        return location_node_name

    def get_element_index(self, pyorbit_name: str) -> int:
        location_node = self.get_location_node(pyorbit_name)
        element_index = self.acc_lattice.getNodeIndex(location_node)
        return element_index

    def get_element_parameters(self, pyorbit_name: str) -> dict[str,]:
        params_dict = self.pyorbit_dictionary[pyorbit_name].get_parameter_dict()
        return params_dict

    def set_element_parameters(self, pyorbit_name: str, new_params: dict) -> None:
        self.pyorbit_dictionary[pyorbit_name].set_parameter_dict(new_params)

    def get_element_parameter(self, pyorbit_name: str, param_key: str):
        param = self.pyorbit_dictionary[pyorbit_name].get_parameter(param_key)
        return param

    def set_element_parameter(self, pyorbit_name: str, param_key: str, new_param) -> None:
        self.pyorbit_dictionary[pyorbit_name].set_parameter(param_key, new_param)


class PyorbitElement:

    def __init__(self, element):
        self.element = element
        self.params_dict_override = element.getParamsDict()

    def get_element(self):
        return self.element

    def get_tracking_node(self):
        return self.element

    def get_name(self) -> str:
        name = self.element.getName()
        return name

    def get_position(self) -> float:
        position = self.element.getPosition()
        return position

    def get_parameter_dict(self) -> dict[str,]:
        params_dict = self.element.getParamsDict()
        return params_dict

    def set_parameter_dict(self, new_params: dict) -> None:
        element = self.element
        element.setParamsDict(new_params)
        self.params_dict_override = new_params

    def get_parameter(self, param_key: str):
        param = self.element.getParam(param_key)
        return param

    def set_parameter(self, param_key: str, new_param) -> None:
        self.element.setParam(param_key, new_param)


class PyorbitNode(PyorbitElement):
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, node: node_types):
        super().__init__(node)
        self.node = node
        self.params_dict_override = node.getParamsDict()

    def get_element(self) -> node_types:
        return self.node

    def get_tracking_node(self) -> node_types:
        return self.node

    def get_name(self) -> str:
        name = self.node.getName()
        return name

    def get_position(self) -> float:
        position = self.node.getPosition()
        return position

    def get_parameter_dict(self) -> dict[str,]:
        params_dict = self.node.getParamsDict()
        return params_dict

    def set_parameter_dict(self, new_params: dict) -> None:
        node = self.node
        node.setParamsDict(new_params)
        self.params_dict_override = new_params

    def get_parameter(self, param_key: str):
        param = self.node.getParam(param_key)
        return param

    def set_parameter(self, param_key: str, new_param) -> None:
        self.node.setParam(param_key, new_param)


class PyorbitCavity(PyorbitElement):
    cavity_type = PyorbitElementTypes.cavity_classes
    rf_gap_type = PyorbitElementTypes.node_classes

    def __init__(self, cavity: cavity_type):
        super().__init__(cavity)
        self.cavity = cavity
        self.params_dict_override = cavity.getParamsDict()

    def get_element(self) -> cavity_type:
        return self.cavity

    def get_first_node(self) -> rf_gap_type:
        first_node = self.cavity.getRF_GapNodes()[0]
        return first_node

    def get_tracking_node(self) -> rf_gap_type:
        first_node = self.get_first_node()
        return first_node

    def get_position(self) -> float:
        position = self.cavity.getRF_GapNodes()[0].getPosition()
        return position

    def get_parameter_dict(self) -> dict[str,]:
        params_dict = self.cavity.getParamsDict()
        if params_dict['blanked'] != 0:
            params_dict['amp'] = self.params_dict_override['amp']
        return params_dict

    def set_parameter_dict(self, new_params: dict) -> None:
        cavity = self.cavity
        cavity.setParamsDict(new_params)
        self.params_dict_override = new_params
        if cavity.getParam('blanked') != 0:
            cavity.setAmp(0.0)

    def get_parameter(self, param_key: str):
        cavity = self.cavity
        if param_key == 'amp' and cavity.getParam('blanked') != 0:
            param = self.params_dict_override[param_key]
        else:
            param = cavity.getParam(param_key)
        return param

    def set_parameter(self, param_key: str, new_param) -> None:
        cavity = self.cavity
        cavity.setParam(param_key, new_param)
        if cavity.getParam('blanked') != 0:
            cavity.setAmp(0.0)


class PyorbitChild(PyorbitElement):
    child_types = PyorbitElementTypes.child_classes
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, child: child_types, ancestor_node: node_types):
        super().__init__(child)
        self.child = child
        self.ancestor_node = ancestor_node
        self.params_dict_override = child.getParamsDict()

    def get_element(self) -> child_types:
        return self.child

    def get_ancestor_node(self) -> node_types:
        return self.ancestor_node

    def get_tracking_node(self) -> node_types:
        return self.ancestor_node

    def get_name(self) -> str:
        name = self.child.getName()
        return name

    def get_position(self) -> float:
        position = self.ancestor_node.getPosition()
        return position

    def get_parameter_dict(self) -> dict[str,]:
        params_dict = self.child.getParamsDict()
        return params_dict

    def set_parameter_dict(self, new_params: dict) -> None:
        child = self.child
        child.setParamsDict(new_params)
        self.params_dict_override = new_params

    def get_parameter(self, param_key: str):
        param = self.child.getParam(param_key)
        return param

    def set_parameter(self, param_key: str, new_param) -> None:
        self.child.setParam(param_key, new_param)


class PVLibrary:
    allowed_pv_types = {'setting', 'readback', 'diagnostic', 'physics'}

    def __init__(self, pyorbit_element_library: PyorbitLibrary):
        self.pyorbit_library = pyorbit_element_library
        pv_dict_hint = Dict[str, PVReference]
        self.pv_dict: pv_dict_hint = {}

    def add_pv(self, pv_name: str, pv_type: str, pyorbit_name: str, param_key: str):
        if pv_type not in self.allowed_pv_types:
            print('"' + pv_type + '" is not a recognized PV type.')
            # Need to check if element and key exist
        else:
            pyorbit_element = self.pyorbit_library.get_element_reference(pyorbit_name)
            new_pv = PVReference(pv_type, pyorbit_element, param_key)
            self.pv_dict[pv_name] = new_pv

    def get_pv_ref(self, pv_name: str) -> "PVReference":
        return self.pv_dict[pv_name]

    def get_pv_dictionary(self) -> dict[str, "PVReference"]:
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

    def get_pv_type(self, pv_name: str) -> str:
        pv_type = self.pv_dict[pv_name].get_type()
        return pv_type

    def get_pyorbit_name(self, pv_name: str) -> str:
        element_name = self.pv_dict[pv_name].get_pyorbit_element_name()
        return element_name

    def get_pyorbit_reference(self, pv_name: str) -> "PyorbitElement":
        element_ref = self.pv_dict[pv_name].get_pyorbit_element_ref()
        return element_ref

    def order_pvs(self):
        pv_dict = self.pv_dict
        temp_dict = {}
        for key, pv_ref in pv_dict.items():
            element_name = pv_ref.get_pyorbit_element_name()
            index = self.pyorbit_library.get_element_index(element_name)
            temp_dict[key] = index
        temp_dict = dict(sorted(temp_dict.items(), key=lambda item: item[1]))
        sorted_pv_dict = {}
        for key, position in temp_dict.items():
            sorted_pv_dict[key] = pv_dict[key]
        self.pv_dict = sorted_pv_dict


class PVReference:

    def __init__(self, pv_type: str, element_ref: "PyorbitElement", param_key: str):

        self.pv_type = pv_type
        self.param_key = param_key
        self.element_ref = element_ref

    def get_value(self):
        param = self.element_ref.get_parameter(self.param_key)
        return param

    def set_value(self, new_value) -> None:
        if self.pv_type == 'setting':
            self.element_ref.set_parameter(self.param_key, new_value)
        else:
            print("Invalid PV type. PV type must include 'setting' to change its value.")

    def get_type(self) -> str:
        return self.pv_type

    def get_param_key(self) -> str:
        return self.param_key

    def get_pyorbit_element_name(self) -> str:
        pyorbit_name = self.element_ref.get_name()
        return pyorbit_name

    def get_pyorbit_element_ref(self) -> "PyorbitElement":
        return self.element_ref
