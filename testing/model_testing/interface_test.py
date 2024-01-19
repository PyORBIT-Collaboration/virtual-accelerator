import sys
import time
from pathlib import Path

from orbit.py_linac.lattice_modifications import Add_quad_apertures_to_lattice, Add_rfgap_apertures_to_lattice
from orbit.py_linac.linac_parsers import SNS_LinacLatticeFactory
from orbit.core.bunch import Bunch

from pyorbit_server_interface import OrbitModel

lattice_file = Path("../../virtaccl/sns_linac.xml")
sns_linac_factory = SNS_LinacLatticeFactory()
sns_linac_factory.setMaxDriftLength(0.01)
model_lattice = sns_linac_factory.getLinacAccLattice(["SCLMed"], lattice_file)
Add_quad_apertures_to_lattice(model_lattice)
Add_rfgap_apertures_to_lattice(model_lattice)

bunch_in = Bunch()
bunch_in.readBunch('SCL_in.dat')
for n in range(bunch_in.getSizeGlobal()):
    if n + 1 > 1000:
        bunch_in.deleteParticleFast(n)
bunch_in.compress()

model = OrbitModel(model_lattice, bunch_in)
# model.set_initial_bunch(initial_bunch)

# print(model.pyorbit_dict.get_element('SCL:Cav01a').getParamsDict())
# print(model.pyorbit_dict.get_element('SCL_Mag:DCH00').getParamsDict())
# print(model.pyorbit_dict.get_element('SCL_Mag:QV01').getParamsDict())
# print(model.pyorbit_dict.get_element('SCL_Diag:BPM01').getParamsDict())

new_op = {}
new_op['SCL_Mag:QV01'] = {'dB/dr': 0.001}
new_op['SCL:Cav11a'] = {'phase': 0.001}
model.update_optics(new_op)
model.track()

# print(model.get_measurements(['SCL_Mag:QV01', 'SCL_Diag:BPM01']))
# print(model.get_settings())

model.save_optics()

model.reset_optics()
model.track()

model.load_optics("test.dat")
model.track()

"""
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

model = OrbitModel(lattice_file, pv_file=pv_file)


print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

dict1 = {"SCL_LLRF:FCM23d:BlnkBeam": False}
model.update_optics(dict1)

print(model.get_settings("SCL_LLRF:FCM23d:BlnkBeam"))

print("Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM23d:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

dict1 = {"SCL_Mag:QV19:B": 0}
model.update_optics(dict1)

dict2 = {"SCL_LLRF:FCM23d:CtlPhaseSet": 0}
model.update_optics(dict2)

model.track()
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

model.save_optics(Path("test.json"))

print("\n reset check")
model.reset_optics()
model.track()

print("\n Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

model.load_optics(Path("test.json"))
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM32:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

"""
"""
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