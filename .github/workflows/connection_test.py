from epics import caget

file1 = open('old_pvs.txt', 'r')
Lines = file1.readlines()
for line in Lines:
    line = line.split()
    pv = line[0]
    caget(pv)