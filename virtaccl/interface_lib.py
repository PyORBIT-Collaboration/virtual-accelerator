from typing import Union, Dict

from orbit.py_linac.lattice.LinacAccLatticeLib import LinacAccLattice
from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from .server_child_nodes import BPMclass, WSclass


# A collection of PyORBIT classes (useful for hinting) and PyORBIT keys we are using.
class PyorbitElementTypes:
    # Strings to label different PyORBIT elements.
    cavity_key = 'RF_Cavity'
    quad_key = 'Quadrupole'
    corrector_key = 'Corrector'
    BPM_key = 'BPM'
    pBPM_key = 'Physics_BPM'
    WS_key = 'Wire_Scanner'

    # PyORBIT keys for parameters we want to pass to the virtual accelerator.
    quad_params = ['dB/dr']
    corrector_params = ['B']
    cavity_params = ['phase', 'amp']
    bpm_params = ['frequency', 'x_avg', 'y_avg', 'phi_avg', 'current', 'energy', 'beta']
    ws_params = ['x_histogram', 'y_histogram']

    # Dictionary to keep track of different PyORBIT class types.
    pyorbit_class_names = {Quad: quad_key,
                           RF_Cavity: cavity_key,
                           DCorrectorV: corrector_key,
                           DCorrectorH: corrector_key,
                           BPMclass: BPM_key,
                           WSclass: WS_key}

    # Dictionary to keep the above parameters with their designated classes
    param_ref_dict = {quad_key: quad_params,
                      cavity_key: cavity_params,
                      corrector_key: corrector_params,
                      BPM_key: bpm_params,
                      WS_key: ws_params}

    optic_classes = (quad_key, cavity_key, corrector_key)  # Classes that can change the beam
    diagnostic_classes = (BPM_key, WS_key)  # Classes that measure the beam

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
        name = element.getName()
        element_class = type(element)
        element_type = PyorbitElementTypes.pyorbit_class_names[element_class]

        self.element = element
        self.name = name
        self.element_type = element_type

        # Determine if the element is an optic or diagnostic.
        if element_type in PyorbitElementTypes.optic_classes:
            self.is_optic_bool = True
        elif element_type in PyorbitElementTypes.diagnostic_classes:
            self.is_optic_bool = False
        else:
            print(f'Element "{name}" is not defined as optic or diagnostic.')

    def get_name(self) -> str:
        return self.name

    def get_type(self) -> str:
        return self.element_type


    # Returns the PyORBIT ParamsDict from the element.
    def get_parameter_dict(self) -> dict[str,]:
        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        params_out_dict = {key: self.element.getParamsDict()[key] for key in modeled_params}
        return params_out_dict

    # Changes the parameters of the element. Needs a dictionary that matches the PyORBIT ParamsDict for the element with
    # the new values. If any keys are not within that elements list of keys define in PyorbitElementTypes, that
    # parameter will be ignored.
    def set_parameter_dict(self, new_params: dict[str,]) -> None:
        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        new_params_fixed = {key: new_params[key] for key in modeled_params}
        self.element.setParamsDict(new_params_fixed)

        bad_params = set(new_params.keys()) - set(modeled_params)
        if bad_params:
            print(f'The following parameters are not in the "{element_type}" model: {", ".join(bad_params)}.')

    # Returns the value for the given parameter key.
    def get_parameter(self, param_key: str):
        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        if param_key in modeled_params:
            param = self.element.getParam(param_key)
            return param
        else:
            print(f'The key "{param_key}" is not in the "{element_type}" model.')

    # Changes the value for the given parameter key with the given new value.
    def set_parameter(self, param_key: str, new_param) -> None:
        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        if param_key in modeled_params:
            self.element.setParam(param_key, new_param)
        else:
            print(f'The key "{param_key}" is not in the "{element_type}" model.')

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
