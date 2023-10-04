import sys
import time
from pathlib import Path
from interface import OrbitModel

lattice_file = Path("../SCL_Wizard/sns_linac.xml")
model = OrbitModel(lattice_file)
model.save_optics(Path("test.json"))

#model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet")
model.get_measurements("SCL_Phys:BPM32:energy")


dict = {}
dict["SCL_LLRF:FCM10a:CtlPhaseSet"] = 0
model.update_optics(dict)

model.track()
model.save_optics(Path("test2.json"))

#model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet")
model.get_measurements("SCL_Phys:BPM32:energy")

#model.reset_optics()
model.load_optics(Path("test.json"))
model.track()

#model.get_settings("SCL_LLRF:FCM10a:CtlPhaseSet")
model.get_measurements("SCL_Phys:BPM32:energy")

model.load_optics(Path("test2.json"))
model.track()

model.get_measurements("SCL_Phys:BPM32:energy")

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
