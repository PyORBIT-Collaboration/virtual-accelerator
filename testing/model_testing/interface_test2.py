import math
import sys
import time
from pathlib import Path

from orbit.bunch_generators import TwissContainer

from pyorbit_server_interface import OrbitModel

# Channel access server used to generate fake PV signals analogous to accelerator components.
# The main body of the script instantiates PVs from a file passed by command line argument.
import json
import sys
from pathlib import Path

from pyorbit_server_interface import OrbitModel

with open('../../virtaccl/va_config.json', "r") as json_file:
    input_dicts = json.load(json_file)

lattice = input_dicts['pyorbit_lattice']
cav_params = input_dicts["cavity_parameters"]
cavs = input_dicts["cavities"]
quad_params = input_dicts["quadrupole_parameters"]
quads = input_dicts["quadrupoles"]
corr_params = input_dicts["corrector_parameters"]
corrs = input_dicts["correctors"]
bpm_params = input_dicts["bpm_parameters"]
bpms = input_dicts["bpms"]
pbpm_params = input_dicts["pbpm_parameters"]
pbpms = input_dicts["pbpms"]

lattice_file = Path(lattice['file_name'])
subsections = lattice['subsections']
model = OrbitModel(lattice_file, subsections)

for device_name, pyorbit_name in cavs.items():
    init_values = []
    for pv_param_name, pv_info in cav_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_type'], pyorbit_name, pv_info['parameter_key'])

for device_name, pyorbit_name in quads.items():
    init_values = []
    for pv_param_name, pv_info in quad_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_type'], pyorbit_name, pv_info['parameter_key'])

for device_name, pyorbit_name in corrs.items():
    init_values = []
    for pv_param_name, pv_info in corr_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_type'], pyorbit_name, pv_info['parameter_key'])

for device_name, pyorbit_name in bpms.items():
    init_values = []
    for pv_param_name, pv_info in bpm_params.items():
        pv_name = device_name + ':' + pv_param_name
        model.add_pv(pv_name, pv_info['pv_type'], pyorbit_name, pv_info['parameter_key'])

    for device_name, pyorbit_name in pbpms.items():
        init_values = []
        for pv_param_name, pv_info in pbpm_params.items():
            pv_name = device_name + ':' + pv_param_name
            model.add_pv(pv_name, pv_info['pv_type'], pyorbit_name, pv_info['parameter_key'])

model.order_pvs()

"""
number_particles = 1000
kinetic_energy = 0.0025  # in [GeV]
beam_current = 38.0 # set the beam peak current in mA

mass = 0.939294  # in [GeV]
gamma = (mass + kinetic_energy) / mass
beta = math.sqrt(gamma * gamma - 1.0) / gamma

# ------ emittances are normalized - transverse by gamma*beta and long. by gamma**3*beta
(alphaX, betaX, emittX) = (-1.9620, 0.1831, 0.21)
(alphaY, betaY, emittY) = (1.7681, 0.1620, 0.21)
(alphaZ, betaZ, emittZ) = (0.0196, 0.5844, 0.24153)

alphaZ = -alphaZ

# ---make emittances un-normalized XAL units [m*rad]
emittX = 1.0e-6 * emittX / (gamma * beta)
emittY = 1.0e-6 * emittY / (gamma * beta)
emittZ = 1.0e-6 * emittZ / (gamma**3 * beta)

# ---- long. size in mm
sizeZ = math.sqrt(emittZ * betaZ) * 1.0e3

# ---- transform to pyORBIT emittance[GeV*m]
emittZ = emittZ * gamma**3 * beta**2 * mass
betaZ = betaZ / (gamma**3 * beta**2 * mass)

twissX = TwissContainer(alphaX, betaX, emittX)
twissY = TwissContainer(alphaY, betaY, emittY)
twissZ = TwissContainer(alphaZ, betaZ, emittZ)

model.generate_initial_bunch(number_particles, kinetic_energy, beam_current, twissX, twissY, twissZ)
"""

bunch_file = Path('../../SCL_Wizard/SCL_in.dat')
model.load_initial_bunch(bunch_file, number_of_particles=1000)

print(model.get_measurements('SCL_Phys:BPM11:Beta'))
dict1 = {}
dict1["SCL_LLRF:FCM01a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM01b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM01c:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM02a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM02b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM02c:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM03a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM03b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM03c:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM04a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM04b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM04c:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM05a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM05b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM05c:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM06a:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM06b:BlnkBeam"] = 1
dict1["SCL_LLRF:FCM06c:BlnkBeam"] = 1

model.update_optics(dict1)
model.track()
print(model.get_measurements('SCL_Phys:BPM11:Beta'))



"""
print(model.get_measurements('SCL_Phys:BPM32:Energy'))
dict1 = {}
#dict1["SCL_LLRF:FCM01a:CtlAmpSet"] = 0.0
dict1["SCL_LLRF:FCM12a:CtlAmpSet"] = 0.0
model.update_optics(dict1)
model.track()
print(model.get_measurements('SCL_Phys:BPM32:Energy'))
#print(model.pv_dict.get_pv_ref("SCL_LLRF:FCM01a:CtlAmpSet").element_ref.get_element().getParamsDict()['Amp'])
dict1 = {"SCL_LLRF:FCM12a:CtlAmpSet": 1.0}
model.update_optics(dict1)
model.track()
print(model.get_measurements('SCL_Phys:BPM32:Energy'))

print(model.get_settings("SCL_Mag:DCH00:B"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))

dict1 = {"SCL_Mag:DCH00:B": 0.000001}
model.update_optics(dict1)

print(model.get_settings("SCL_Mag:DCH00:B"))

model.track()

print(model.get_measurements("SCL_Diag:BPM32:xAvg"))

dict1 = {"SCL_Mag:DCH00:B": 0.0}
model.update_optics(dict1)

print(model.get_settings("SCL_Mag:DCH00:B"))

model.track()

print(model.get_measurements("SCL_Diag:BPM32:xAvg"))




print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

dict1 = {"SCL_LLRF:FCM23d:BlnkBeam": False}
model.update_optics(dict1)

print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

print("Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

dict1 = {"SCL_Mag:QV19:B": 0}
model.update_optics(dict1)

dict2 = {"SCL_LLRF:FCM23d:CtlPhaseSet": 0}
model.update_optics(dict2)

model.track()
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

model.save_optics(Path("test.json"))

print("\n reset check")
model.reset_optics()
model.track()

print("\n Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))

model.load_optics(Path("test.json"))
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:Energy"))



avg_time = 0
for i in range(100):
    #init_phase = model.get_settings("SCL_LLRF:FCM01a:CtlPhaseSet")["SCL_LLRF:FCM01a:CtlPhaseSet"]
    #up_dict = {"SCL_LLRF:FCM01a:CtlPhaseSet": init_phase + 0.000000000000001}
    init_field = model.get_settings("SCL_Mag:QH00:B")["SCL_Mag:QH00:B"]
    up_dict = {"SCL_Mag:QH00:B": init_field + 0.00000000001}
    model.update_optics(up_dict)

    start_time = time.time()
    model.track()
    end_time = time.time()
    time_taken = end_time - start_time
    print(time_taken)
    avg_time += time_taken

avg_time /= 100
print(avg_time)

"""