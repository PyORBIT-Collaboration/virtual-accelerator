import sys
import time
from interface import OrbitModel

model = OrbitModel("../SCL_Wizard/sns_linac.xml")

# model.get_measurements("SCL_Phys:BPM32:energy")
# model.get_settings("SCL_Mag:QH18:B")

# dict = {}
# dict["SCL_LLRF:FCM23d:CtlPhaseSet"] = 1.9
# dict["SCL_Mag:QH18:B"] = 1.3
# model.update_optics(dict)

# model.track()

# model.get_measurements("SCL_Phys:BPM32:energy")
# model.get_settings("SCL_Mag:QH18:B")
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
