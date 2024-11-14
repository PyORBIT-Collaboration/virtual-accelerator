from virtaccl.beam_line import BeamLine, PhysicsDevice
from virtaccl.model import Model
from virtaccl.server import Server
from virtaccl.virtual_accelerator import VA_Parser, VirtualAcceleratorBuilder


def add_pyorbit_arguments(va_parser: VA_Parser) -> VA_Parser:
    # Lattice xml input file and the sequences desired from that file.
    va_parser.add_model_argument('--lattice', type=str, help='Pathname of lattice file.')
    va_parser.add_model_argument("--start", default="MEBT", type=str,
                                 help='Desired sequence of the lattice to start the model with.')
    va_parser.add_model_argument("end", nargs='?', type=str,
                                 help='Desired sequence of the lattice to end the model with.')
    va_parser.add_model_argument('--drift_length', default=1.0, type=float,
                                 help='Maximum length of a drift node in meters. Will determine frequency of Physics '
                                      'and Space Charge Nodes.')

    va_parser.add_model_argument('--space_charge', const=0.01, nargs='?', type=float,
                                 help="Adds Uniform Ellipse Space Charge nodes to the lattice. The minimum distance "
                                      "in meters between nodes can be specified; the default is 0.01m if no minimum "
                                      "is given. If the argument is not used, no space charge nodes are added.")
    va_parser.add_model_argument('--physics_nodes', dest='physics_nodes', action='store_true',
                                 help="Adds physics child nodes to each node on the lattice.")

    # Desired initial bunch file and the desired number of particles from that file.
    va_parser.add_model_argument('--bunch', type=str, help='Pathname of input bunch file.')
    va_parser.add_model_argument('--particle_number', default=1000, type=int,
                                 help='Number of particles to use.')
    va_parser.add_model_argument('--beam_current', default=38.0, type=float,
                                 help='Initial beam current in mA.')
    va_parser.add_model_argument('--save_bunch', const='end_bunch.dat', nargs='?', type=str,
                                 help="Saves the bunch at the end of the lattice after each track in the given "
                                      "location. If no location is given, the bunch is saved as 'end_bunch.dat' in "
                                      "the working directory.")
    return va_parser


class PyorbitVirtualAcceleratorBuilder(VirtualAcceleratorBuilder):
    def __init__(self, model: Model, beam_line: BeamLine, server: Server, **kwargs):
        super().__init__(model, beam_line, server, **kwargs)

        if kwargs['physics_nodes']:
            self.add_physics_elements()

    def add_physics_elements(self):
        physics_elements = self.model.add_physics_elements()
        for physics_name in physics_elements:
            phys_device = PhysicsDevice(physics_name)
            self.beam_line.add_device(phys_device)
