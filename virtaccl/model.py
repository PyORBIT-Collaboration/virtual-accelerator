from typing import Dict, Any, List


class Model:
    """This is a generic model that other models can inherit."""

    def __init__(self):
        pass

    def get_measurements(self) -> Dict[str, Dict[str, Any]]:
        """Output values from the model. This needs to return a dictionary with the model name of the element as a key
        to a dictionary of the element's parameters.

        Returns
        ----------
        out : dictionary
            A dictionary of element names as keys connected to that element's parameter dictionary.
        """
        return {}

    def track(self) -> None:
        """Updates values within your model."""
        pass

    def update_optics(self, changed_optics: Dict[str, Dict[str, Any]]) -> None:
        """Take external values and update the model. Needs an input of a dictionary with the model name of the element
        as a key to a dictionary of the element's parameters with their new values.

        Parameters
        ----------
        changed_optics : dictionary
            Dictionary using the element names as keys. Each key is connected to a parameter dictionary containing the
            new parameter values.
        """
        pass

    def add_physics_elements(self) -> List[str]:
        """Adds physics elements to the model. These are to be used in conjunction with the Physics Devices found in
        BeamLine.

        Returns
        ----------
        out : list
            A list of the names of the new physics elements added to the model.
        """
        pass

