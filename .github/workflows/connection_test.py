import sys
import epics

file1 = open('old_pvs.txt', 'r')
Lines = file1.readlines()
for line in Lines:
    line = line.split()
    pv_name = line[0]
    pv = epics.PV(pv_name)
    print(pv_name)
    if pv.get() is None:
        raise ValueError("An error occurred: Some old PVs no longer connected.")
print("All old PVs found!")
