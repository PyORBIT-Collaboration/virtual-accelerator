import sys
import time
from pathlib import Path
from pyorbit_server_interface import OrbitModel

lattice_file = Path("../../EPICS/sns_linac.xml")
pv_file = Path("server_devices.txt")
model = OrbitModel(lattice_file, [])

sys.exit()

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
