from typing import Union, Dict, Any

from orbit.py_linac.lattice.LinacAccNodes import Quad, MarkerLinacNode, DCorrectorV, DCorrectorH, Bend
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity
from .pyorbit_child_nodes import BPMclass, WSclass

"""A collection of PyORBIT classes (useful for hinting) and PyORBIT keys we are using."""


class PyorbitElementTypes:
    """This is a container of keys and PyORBIT node types to assist with manipulating PYORBIT in
    pyorbit_controller.py"""

    """Keys to designate different PyORBIT node types."""
    cavity_key = 'RF_Cavity'
    quad_key = 'Quadrupole'
    corrector_key = 'Corrector'
    BPM_key = 'BPM'
    pBPM_key = 'Physics_BPM'
    WS_key = 'Wire_Scanner'
    bend_key = 'Bend'

    """PyORBIT keys for parameters we want to pass to the virtual accelerator."""
    quad_params = ['dB/dr']
    corrector_params = ['B']
    cavity_params = ['phase', 'amp']
    bpm_params = ['frequency', 'x_avg', 'y_avg', 'phi_avg', 'amp_avg', 'energy', 'beta', 'part_num']
    ws_params = ['x_histogram', 'y_histogram']

    """Dictionary to keep track of different PyORBIT class types."""
    pyorbit_class_names = {Quad: quad_key,
                           RF_Cavity: cavity_key,
                           DCorrectorV: corrector_key,
                           DCorrectorH: corrector_key,
                           BPMclass: BPM_key,
                           WSclass: WS_key,
                           Bend: bend_key}

    """Dictionary to keep the above parameters with their designated classes."""
    param_ref_dict = {quad_key: quad_params,
                      cavity_key: cavity_params,
                      corrector_key: corrector_params,
                      BPM_key: bpm_params,
                      WS_key: ws_params}

    """Classes that can change the beam."""
    optic_classes = (quad_key, cavity_key, corrector_key)

    """Classes that measure the beam."""
    diagnostic_classes = (BPM_key, WS_key)

    """Type hint definitions"""
    node_classes = Union[Quad, BaseRF_Gap, MarkerLinacNode, Bend]
    cavity_classes = RF_Cavity
    child_classes = Union[DCorrectorV, DCorrectorH, BPMclass, WSclass, MarkerLinacNode]

    """type hint for all classes"""
    pyorbit_classes = Union[node_classes, child_classes, cavity_classes]


class PyorbitElement:
    """PyorbitElement is a generic class all the others inherit. This should not be used directly by the controller but
    inherited by the classes that are used by the controller.

        Parameters
        ----------
        element : pyorbit_classes
            Instance of a PyORBIT element (node, cavity, etc.) to be used in the controller.
    """

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
        """Return the name of the element in PyORBIT.

        Results
        ----------
        out : string
            Name of the element.
        """

        return self.name

    def get_type(self) -> str:
        """Return the key associated with the the type of the element in PyORBIT.

        Results
        ----------
        out : string
            Key of the element's type.
        """

        return self.element_type

    def get_parameter_dict(self) -> Dict[str, Any]:
        """Returns the dictionary of parameters of the element from PyORBIT coinciding the parameters defined in
        PyorbitElementTypes.param_ref_dict.

        Results
        ----------
        out : dictionary
            The element's parameter dictionary
        """

        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        params_out_dict = {key: self.element.getParamsDict()[key] for key in modeled_params}
        return params_out_dict

    def set_parameter_dict(self, new_params: Dict[str, Any]) -> None:
        """Changes the parameters of the element. Needs a dictionary that matches the keys in the PyORBIT ParamsDict for
         the element connected with the new values. If any keys are not within that elements list of keys define in
         PyorbitElementTypes.param_ref_dict, that parameter will be ignored.

        Parameters
        ----------
        new_params : dictionary
            Dictionary containing PyORBIT keys for the element's parameters connected to their new values.
        """

        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        new_params_fixed = {key: new_params[key] for key in modeled_params}
        self.element.setParamsDict(new_params_fixed)

        bad_params = set(new_params.keys()) - set(modeled_params)
        if bad_params:
            print(f'The following parameters are not in the "{element_type}" model: {", ".join(bad_params)}.')

    def get_parameter(self, param_key: str):
        """Returns the value of the parameter for the element for the given parameter key.

        Results
        ----------
        out : any
            The value of the given parameter.
        """

        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        if param_key in modeled_params:
            param = self.element.getParam(param_key)
            return param
        else:
            print(f'The key "{param_key}" is not in the "{element_type}" model.')

    def set_parameter(self, param_key: str, new_param) -> None:
        """Changes the value for the given parameter key with the given new value for the element.

        Parameters
        ----------
        param_key : string
            Key for the parameter in the element that will be changed.
        new_param : any
            The new value for the parameter.
        """

        element_type = self.get_type()
        modeled_params = PyorbitElementTypes.param_ref_dict[element_type]
        if param_key in modeled_params:
            self.element.setParam(param_key, new_param)
        else:
            print(f'The key "{param_key}" is not in the "{element_type}" model.')

    def is_optic(self) -> bool:
        """Returns a boolean depending on if the element is designated as an optic or not.
        PyorbitElementTypes.optic_classes determines which element types are designated as optics.

        Results
        ----------
        out : bool
            True if the element is designated as an optic, false if not.
        """

        return self.is_optic_bool


class PyorbitNode(PyorbitElement):
    """Class for handling PyORBIT nodes that are direct children of the lattice. Inherits from PyorbitElement.

        Parameters
        ----------
        node : PyorbitElementTypes.node_classes
            Instance of a PyORBIT node (Quadrupole, etc.) to be used in the controller.
    """

    node_types = PyorbitElementTypes.node_classes

    def __init__(self, node: node_types):
        super().__init__(node)
        self.node = node

    def get_element(self) -> node_types:
        """Returns the node.

        Results
        ----------
        out : PyorbitElementTypes.node_classes
            The instance of the node given when initialized.
        """

        return self.node

    def get_position(self) -> float:
        """Returns the position of the node in meters.

        Results
        ----------
        out : float
            The position of the node from the start of its sequence in meters.
        """

        position = self.node.getPosition()
        return position

    def get_tracking_node(self) -> node_types:
        """Returns the node on the lattice this node is located at. This is for other classes and just returns the
        original node here.

        Results
        ----------
        out : PyorbitElementTypes.node_classes
            The instance of the node given when initialized.
        """

        return self.node


class PyorbitCavity(PyorbitElement):
    """Class for PyORBIT accelerating cavities. Inherits from PyorbitElement.

        Parameters
        ----------
        cavity : PyorbitElementTypes.cavity_classes
            Instance of a PyORBIT cavity to be used in the controller.
    """

    cavity_type = PyorbitElementTypes.cavity_classes
    rf_gap_type = PyorbitElementTypes.node_classes

    def __init__(self, cavity: cavity_type):
        super().__init__(cavity)
        self.cavity = cavity

    def get_element(self) -> cavity_type:
        """Returns the cavity.

        Results
        ----------
        out : RF_Cavity
            The instance of the cavity given when initialized.
        """

        return self.cavity

    def get_first_node(self) -> rf_gap_type:
        """Returns the first RF gap node of the cavity.

        Results
        ----------
        out : BaseRF_Gap
            The instance of the first RF gap node associated with the cavity given when initialized.
        """

        first_node = self.cavity.getRF_GapNodes()[0]
        return first_node

    def get_tracking_node(self) -> rf_gap_type:
        """Returns the node directly on the lattice that begins the cavity. This uses get_first_node to do so.

        Results
        ----------
        out : BaseRF_Gap
            The instance of the RF gap node at the entrance of the cavity given when initialized.
        """

        first_node = self.get_first_node()
        return first_node

    def get_position(self) -> float:
        """Returns the position of the entrance of the cavity in meters.

        Results
        ----------
        out : float
            The position of the first RF gap node associated with the cavity relative to its sequence in meters.
        """

        position = self.get_first_node().getPosition()
        return position


class PyorbitChild(PyorbitElement):
    """Class for PyORBIT child nodes that are children of other nodes and not the lattice.

        Parameters
        ----------
        child : PyorbitElementTypes.child_types
            Instance of a PyORBIT child to be used in the controller.
        ancestor_node : PyorbitElementTypes.node_types
            Instance of the PyORBIT node that is a direct child of the lattice and through which the child node can be
            found.
    """

    child_types = PyorbitElementTypes.child_classes
    node_types = PyorbitElementTypes.node_classes

    def __init__(self, child: child_types, ancestor_node: node_types):
        super().__init__(child)
        self.child = child
        self.ancestor_node = ancestor_node

    def get_element(self) -> child_types:
        """Returns the child node.

        Results
        ----------
        out : PyorbitElementTypes.child_types
            The instance of the child node given when initialized.
        """

        return self.child

    def get_ancestor_node(self) -> node_types:
        """Returns the ancestor node.

        Results
        ----------
        out : PyorbitElementTypes.node_types
            The instance of the node on the lattice through which the child node is reached.
        """

        return self.ancestor_node

    def get_tracking_node(self) -> node_types:
        """Returns the node on the lattice that the child is under. In this case, the ancestor node.

        Results
        ----------
        out : PyorbitElementTypes.node_types
            The instance of the node on the lattice through which the child node is reached.
        """

        return self.ancestor_node

    def get_position(self) -> float:
        """Returns the position of the child node in meters.

        Results
        ----------
        out : float
            The position of the ancestor node relative to its sequence in meters.
        """

        position = self.ancestor_node.getPosition()
        return position
