import sys
import epics

file1 = open('old_pvs.txt', 'r')
Lines = file1.readlines()
for line in Lines:
    line = line.split()
    pv_name = line[0]
    pv = epics.PV(pv_name)
    if pv.get() is None:
        print("Some old PVs not found!")
        sys.exit()
print("All old PVs found!")
