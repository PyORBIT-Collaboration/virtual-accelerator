import sys
import time
from pathlib import Path
from interface2 import OrbitModel

lattice_file = Path("../SCL_Wizard/sns_linac.xml")
model = OrbitModel(lattice_file)

print("Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM22:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

dict1 = {"SCL_Mag:QV19:B": 0}
model.update_optics(dict1)

dict2 = {"SCL_LLRF:FCM10a:CtlPhaseSet": 0}
model.update_optics(dict2)

model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM22:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

model.save_optics(Path("test.json"))

model.reset_optics()
model.track()

print("\n Original")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM22:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

model.load_optics(Path("test.json"))
model.track()

print("\n Changed")
print(model.get_settings("SCL_Mag:QV19:B"))
print(model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet"))
print(model.get_measurements("SCL_Diag:BPM22:xAvg"))
print(model.get_measurements("SCL_Phys:BPM32:energy"))

"""
avg_time = 0
for i in range(100):
    init_phase = model.get_settings("SCL_LLRF:FCM01a:CtlPhaseSet")
    up_dict = {"SCL_LLRF:FCM01a:CtlPhaseSet": init_phase + 0.00001}
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
