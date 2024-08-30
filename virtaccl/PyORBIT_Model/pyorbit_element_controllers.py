from typing import Union, Dict, Any, List

from orbit.py_linac.lattice.LinacAccNodes import BaseLinacNode
from orbit.py_linac.lattice.LinacRfGapNodes import BaseRF_Gap
from orbit.py_linac.lattice.LinacAccLatticeLib import RF_Cavity


class PyorbitElement:
    """PyorbitElement is a generic class all the others inherit. This should not be used directly by the controller but
    inherited by the classes that are used by the controller.

        Parameters
        ----------
        element : pyorbit_classes
            Instance of a PyORBIT element (node, cavity, etc.) to be used in the controller.
    """

    def __init__(self, element: Union[BaseLinacNode, RF_Cavity], node_type: str = None):
        name = element.getName()

        if node_type is not None:
            element_type = node_type
        else:
            element_type = element.getType()

        self.element = element
        self.name = name
        self.element_type = element_type

    def get_name(self) -> str:
        """Return the name of the element in PyORBIT.

        Returns
        ----------
        out : string
            Name of the element.
        """

        return self.name

    def get_type(self) -> str:
        """Return the key associated with the type of the element in PyORBIT.

        Returns
        ----------
        out : string
            Key of the element's type.
        """

        return self.element_type

    def get_parameter_dict(self) -> Dict[str, Any]:
        """Returns the dictionary of parameters of the element from PyORBIT.

        Returns
        ----------
        out : dictionary
            The element's parameter dictionary
        """

        return self.element.getParamsDict()

    def set_parameter_dict(self, new_params: Dict[str, Any]) -> None:
        """Changes the parameters of the element. Needs a dictionary that matches the keys in the PyORBIT ParamsDict for
         the element connected with the new values. If any keys are not within that elements list of keys, that
         parameter will be ignored.

        Parameters
        ----------
        new_params : dictionary
            Dictionary containing PyORBIT keys for the element's parameters connected to their new values.
        """

        pyorbit_params = self.element.keys()
        new_params_fixed = {key: new_params[key] for key in pyorbit_params}
        self.element.setParamsDict(new_params_fixed)

        bad_params = set(new_params.keys()) - set(pyorbit_params)
        if bad_params:
            print(f'The following parameters are not in the "{self.element_type}" element: {", ".join(bad_params)}.')

    def get_parameter(self, param_key: str):
        """Returns the value of the parameter for the element for the given parameter key.

        Returns
        ----------
        out : any
            The value of the given parameter.
        """

        pyorbit_params = self.element.keys()
        if param_key in pyorbit_params:
            param = self.element.getParam(param_key)
            return param
        else:
            print(f'The key "{param_key}" is not in the "{self.element_type}" element.')

    def set_parameter(self, param_key: str, new_param) -> None:
        """Changes the value for the given parameter key with the given new value for the element.

        Parameters
        ----------
        param_key : string
            Key for the parameter in the element that will be changed.
        new_param : any
            The new value for the parameter.
        """

        pyorbit_params = self.element.keys()
        if param_key in pyorbit_params:
            self.element.setParam(param_key, new_param)
        else:
            print(f'The key "{param_key}" is not in the "{self.element_type}" element.')


class PyorbitNode(PyorbitElement):
    """Class for handling PyORBIT nodes that are direct children of the lattice. Inherits from PyorbitElement.

        Parameters
        ----------
        node : BaseLinacNode
            Instance of a PyORBIT node (Quadrupole, etc.) to be used in the controller.
    """

    def __init__(self, node: BaseLinacNode):
        super().__init__(node)
        self.node = node

    def get_element(self) -> BaseLinacNode:
        """Returns the node.

        Returns
        ----------
        out : BaseLinacNode
            The instance of the node given when initialized.
        """

        return self.node

    def get_position(self) -> float:
        """Returns the position of the node in meters.

        Returns
        ----------
        out : float
            The position of the node from the start of its sequence in meters.
        """

        position = self.node.getPosition()
        return position

    def get_tracking_node(self) -> BaseLinacNode:
        """Returns the node on the lattice this node is located at. This is for other classes and just returns the
        original node here.

        Returns
        ----------
        out : BaseLinacNode
            The instance of the node given when initialized.
        """

        return self.node


class PyorbitCavity(PyorbitElement):
    """Class for PyORBIT accelerating cavities. Inherits from PyorbitElement.

        Parameters
        ----------
        cavity : RF_Cavity
            Instance of a PyORBIT cavity to be used in the controller.
    """

    def __init__(self, cavity: RF_Cavity, cavity_key: str):
        super().__init__(cavity, cavity_key)
        self.cavity = cavity

    def get_element(self) -> RF_Cavity:
        """Returns the cavity.

        Returns
        ----------
        out : RF_Cavity
            The instance of the cavity given when initialized.
        """

        return self.cavity

    def get_first_node(self) -> BaseRF_Gap:
        """Returns the first RF gap node of the cavity.

        Returns
        ----------
        out : BaseRF_Gap
            The instance of the first RF gap node associated with the cavity given when initialized.
        """

        first_node = self.cavity.getRF_GapNodes()[0]
        return first_node

    def get_tracking_node(self) -> BaseRF_Gap:
        """Returns the node directly on the lattice that begins the cavity. This uses get_first_node to do so.

        Returns
        ----------
        out : BaseRF_Gap
            The instance of the RF gap node at the entrance of the cavity given when initialized.
        """

        first_node = self.get_first_node()
        return first_node

    def get_position(self) -> float:
        """Returns the position of the entrance of the cavity in meters.

        Returns
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
        child : BaseLinacNode
            Instance of a PyORBIT child to be used in the controller.
        ancestor_node : BaseLinacNode
            Instance of the PyORBIT node that is a direct child of the lattice and through which the child node can be
            found.
    """

    def __init__(self, child: BaseLinacNode, ancestor_node: BaseLinacNode):
        super().__init__(child)
        self.child = child
        self.ancestor_node = ancestor_node

    def get_element(self) -> BaseLinacNode:
        """Returns the child node.

        Returns
        ----------
        out : BaseLinacNode
            The instance of the child node given when initialized.
        """

        return self.child

    def get_ancestor_node(self) -> BaseLinacNode:
        """Returns the ancestor node.

        Returns
        ----------
        out : BaseLinacNode
            The instance of the node on the lattice through which the child node is reached.
        """

        return self.ancestor_node

    def get_tracking_node(self) -> BaseLinacNode:
        """Returns the node on the lattice that the child is under. In this case, the ancestor node.

        Returns
        ----------
        out : BaseLinacNode
            The instance of the node on the lattice through which the child node is reached.
        """

        return self.ancestor_node

    def get_position(self) -> float:
        """Returns the position of the child node in meters.

        Returns
        ----------
        out : float
            The position of the ancestor node relative to its sequence in meters.
        """

        position = self.ancestor_node.getPosition()
        return position
