from typing import Union, Dict

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from server_child_nodes import BPMclass, WSclass


# A collection of PyORBIT classes useful for hinting and PyORBIT keys we are using.
class PyorbitElementTypes:
    # Class check definitions from PyORBIT. Usefully for hinting and checking.
    optic_classes = (Quad, RF_Cavity, DCorrectorV, DCorrectorH)  # Classes that can change the beam
    diagnostic_classes = (MarkerLinacNode, BPMclass, WSclass)  # Classes that measure the beam

    # PyORBIT keys for parameters we want to pass to the virtual accelerator.
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


# What follows are different classes that unifies the functions of different PyORBIT classes. PyorbitElement is a
# generic class all the others inherit. The actual PyOBIT instance of that element is needed as the input.
class PyorbitElement:
    def __init__(self, element):
        self.element = element

        # Determine if the element is an optic or diagnositc.
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

    # Returns the PyORBIT ParamsDict from the element.
    def get_parameter_dict(self) -> dict[str,]:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        params_out_dict = {key: element.getParamsDict()[key] for key in modeled_params}
        return params_out_dict

    # Changes the parameters of the element. Needs a dictionary that matches the PyORBIT ParamsDict for the element with
    # the new values. If any keys are not within that elements list of keys define in PyorbitElementTypes, that
    # parameter will be ignored.
    def set_parameter_dict(self, new_params: dict[str,]) -> None:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        new_params_fixed = {key: new_params[key] for key in modeled_params}
        element.setParamsDict(new_params_fixed)

        bad_params = set(new_params.keys()) - set(modeled_params)
        if bad_params:
            print(f'The following parameters are not in the "{element_class.__name__}" model: {", ".join(bad_params)}.')

    # Returns the value for the given parameter key.
    def get_parameter(self, param_key: str):
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        if param_key in modeled_params:
            param = element.getParam(param_key)
            return param
        else:
            print(f'The key "{param_key}" is not in the "{element_class.__name__}" model.')

    # Changes the value for the given parameter key with the given new value.
    def set_parameter(self, param_key: str, new_param) -> None:
        element = self.element
        element_class = type(element)
        modeled_params = PyorbitElementTypes.param_ref_dict[element_class]
        if param_key in modeled_params:
            element.setParam(param_key, new_param)
        else:
            print(f'The key "{param_key}" is not in the "{element_class.__name__}" model.')

    # Is the element an optic or not
    def is_optic(self) -> bool:
        return self.is_optic_bool


# Class for handling PyORBIT nodes that are not children of any other nodes. The node instance is needed as the input.
class PyorbitNode(PyorbitElement):
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, node: node_types):
        super().__init__(node)
        self.node = node

    # Returns the reference to the node in PyORBIT
    def get_element(self) -> node_types:
        return self.node

    # Returns the position of the node in meters.
    def get_position(self) -> float:
        position = self.node.getPosition()
        return position

    # As this node has no children, returns itself as the node to track from.
    def get_tracking_node(self) -> node_types:
        return self.node


# Class for PyORBIT accelerating cavity classes. The cavity instance is needed as the input.
class PyorbitCavity(PyorbitElement):
    cavity_type = PyorbitElementTypes.cavity_classes
    rf_gap_type = PyorbitElementTypes.node_classes

    def __init__(self, cavity: cavity_type):
        super().__init__(cavity)
        self.cavity = cavity

    # Returns the instance of the cavity (not the accelerating gap nodes).
    def get_element(self) -> cavity_type:
        return self.cavity

    # Returns the first accelerating gap node of the cavity.
    def get_first_node(self) -> rf_gap_type:
        first_node = self.cavity.getRF_GapNodes()[0]
        return first_node

    # Returns the node to track from for this cavity (the first accelerating gap node).
    def get_tracking_node(self) -> rf_gap_type:
        first_node = self.get_first_node()
        return first_node

    # Returns the position of the first accelerating gap node.
    def get_position(self) -> float:
        position = self.cavity.getRF_GapNodes()[0].getPosition()
        return position


# This class is for nodes that are children of other nodes. It needs both the child instance, and the instance of the
# node on the lattice that this node is a descendant of.
class PyorbitChild(PyorbitElement):
    child_types = PyorbitElementTypes.child_classes
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, child: child_types, ancestor_node: node_types):
        super().__init__(child)
        self.child = child
        self.ancestor_node = ancestor_node

    # Return the instance of the child node.
    def get_element(self) -> child_types:
        return self.child

    # Return the instance of the lattice node.
    def get_ancestor_node(self) -> node_types:
        return self.ancestor_node

    # Return the instance of the node from which to track from (the lattice node).
    def get_tracking_node(self) -> node_types:
        return self.ancestor_node

    # Return the position of this child node (the position of the lattice node).
    def get_position(self) -> float:
        position = self.ancestor_node.getPosition()
        return position
