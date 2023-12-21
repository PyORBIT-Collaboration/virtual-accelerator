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
    bpm_params = ['x_avg', 'y_avg', 'phi_avg', 'current', 'energy', 'beta']
    ws_params = ['x_histogram', 'y_histogram']

    # Dictionary to keep the above parameters with their designated classes
    param_ref_dict = {Quad: quad_params, RF_Cavity: cavity_params, DCorrectorV: corrector_params,
                      DCorrectorH: corrector_params, BPMclass: bpm_params, WSclass: ws_params}

    # Type hint definitions
    node_classes = Union[Quad, BaseRF_Gap, MarkerLinacNode]
    cavity_classes = RF_Cavity
    child_classes = Union[DCorrectorV, DCorrectorH, BPMclass, WSclass, MarkerLinacNode]

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

    def get_parameter_dict(self) -> dict[str,]:
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
