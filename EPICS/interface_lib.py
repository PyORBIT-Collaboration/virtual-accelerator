from typing import Union, Dict

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from server_child_nodes import BPMclass, WSclass


class PyorbitElementTypes:
    # Class check definitions
    optic_classes = (Quad, RF_Cavity, DCorrectorV, DCorrectorH)
    diagnostic_classes = (MarkerLinacNode, BPMclass, WSclass)

    # Parameters for model to pass
    quad_params = ['dB/dr']
    corrector_params = ['B']
    cavity_params = ['phase', 'amp']
    bpm_params = ['x_avg', 'y_avg', 'phi_avg', 'energy', 'beta']
    ws_params = ['x_histogram', 'y_histogram']

    # Dictionary to keep the above parameters with their designated classes
    param_ref_dict = {Quad: quad_params, RF_Cavity: cavity_params, DCorrectorV: corrector_params,
                      DCorrectorH: corrector_params, BPMclass: bpm_params, WSclass: ws_params}

    # Type hint definitions
    node_classes = Union[Quad, BaseRF_Gap, MarkerLinacNode]
    cavity_classes = RF_Cavity
    child_classes = Union[DCorrectorV, DCorrectorH, BPMclass]

    # type_hint for all classes
    pyorbit_classes = Union[node_classes, child_classes, cavity_classes]


class PyorbitElement:

    def __init__(self, element):
        self.element = element
        self.params_dict_override = element.getParamsDict()

        if isinstance(element, PyorbitElementTypes.optic_classes):
            self.is_optic_bool = True
        elif isinstance(element, PyorbitElementTypes.diagnostic_classes):
            self.is_optic_bool = False
        else:
            name = element.getName()
            print(f'Element "{name}" is not defined as optic or diagnostic.')

    def get_name(self) -> str:
        name = self.element.getName()
        return name

    def get_parameter_dict(self) -> dict[str, ]:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        params_out_dict = {key: element.getParamsDict()[key] for key in modeled_params}
        return params_out_dict

    def set_parameter_dict(self, new_params: dict) -> None:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        new_params_fixed = {key: new_params[key] for key in modeled_params}
        element.setParamsDict(new_params_fixed)

        bad_params = set(new_params.keys()) - set(modeled_params)
        if bad_params:
            print(f'The following parameters are not in the "{element_class.__name__}" model: {", ".join(bad_params)}.')

    def get_parameter(self, param_key: str):
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        if param_key in modeled_params:
            param = element.getParam(param_key)
            return param
        else:
            print(f'The key "{param_key}" is not in the "{element_class.__name__}" model.')

    def set_parameter(self, param_key: str, new_param) -> None:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        if param_key in modeled_params:
            element.setParam(param_key, new_param)
        else:
            print(f'The key "{param_key}" is not in the "{element_class.__name__}" model.')

    def is_optic(self) -> bool:
        return self.is_optic_bool


class PyorbitNode(PyorbitElement):
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, node: node_types):
        super().__init__(node)
        self.node = node
        self.params_dict_override = node.getParamsDict()

    def get_element(self) -> node_types:
        return self.node

    def get_position(self) -> float:
        position = self.node.getPosition()
        return position

    def get_tracking_node(self) -> node_types:
        return self.node


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

    def get_position(self) -> float:
        position = self.ancestor_node.getPosition()
        return position


class PyorbitLibrary:
    node_classes = PyorbitElementTypes.node_classes
    cavity_classes = PyorbitElementTypes.cavity_classes
    child_classes = PyorbitElementTypes.child_classes
    pyorbit_classes = PyorbitElementTypes.pyorbit_classes

    element_ref_hint = Union[PyorbitNode, PyorbitCavity, PyorbitChild]

    def __init__(self, acc_lattice: LinacAccLattice, ignored_nodes=None):
        if ignored_nodes is None:
            ignored_nodes = set()
        ignored_nodes |= {'baserfgap', 'drift', 'tilt', 'fringe', 'markerLinacNode', 'baseLinacNode'}
        unique_elements = set()

        # Set up a dictionary to reference different objects within the lattice by their name.
        # This way, children nodes (correctors) and RF Cavity parameters are easy to reference.

        self.acc_lattice = acc_lattice
        element_dict_hint = Dict[str, self.element_ref_hint]
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

    def get_element_names(self) -> list[str]:
        return list(self.pyorbit_dictionary.keys())

    def get_element_reference(self, pyorbit_name: str) -> element_ref_hint:
        return self.pyorbit_dictionary[pyorbit_name]

    def get_element_dictionary(self) -> dict[str, element_ref_hint]:
        return self.pyorbit_dictionary

    def get_element(self, pyorbit_name: str) -> pyorbit_classes:
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

    def get_element_parameters(self, pyorbit_name: str) -> dict[str, ]:
        params_dict = self.pyorbit_dictionary[pyorbit_name].get_parameter_dict()
        return params_dict

    def set_element_parameters(self, pyorbit_name: str, new_params: dict) -> None:
        self.pyorbit_dictionary[pyorbit_name].set_parameter_dict(new_params)

    def get_element_parameter(self, pyorbit_name: str, param_key: str):
        param = self.pyorbit_dictionary[pyorbit_name].get_parameter(param_key)
        return param

    def set_element_parameter(self, pyorbit_name: str, param_key: str, new_param) -> None:
        self.pyorbit_dictionary[pyorbit_name].set_parameter(param_key, new_param)
