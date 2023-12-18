import json
import epics
import numpy as np
import time
import matplotlib.pyplot as plt

# epics.caput("SCL_Mag:PS_DCH00:B_Set", -0.01)
# time.sleep(0.7)

with open('epics_names.json', "r") as json_file:
    names_all = json.load(json_file)

perturb = 0.001

cor_names = names_all['Correctors']
all_bpm_names = names_all['BPMs']

hor_names = []
ver_names = []
for name in cor_names:
    if 'HEBT' in name or 'PS_DCH33' in name:
        pass
    elif 'DCH' in name:
        hor_names.append(name)
    elif 'DCV' in name:
        ver_names.append(name)

bpm_names = []
for name in all_bpm_names:
    if 'HEBT' in name or 'SCL_Diag:BPM00a' in name:
        pass
    else:
        bpm_names.append(name)
extra_bpms = len(bpm_names) - len(hor_names)
if extra_bpms > 0:
    bpm_names = bpm_names[extra_bpms:]

print(len(hor_names), len(ver_names), len(bpm_names))

hor_cor_orig = {}
for name in hor_names:
    field = epics.caget(name + ":B")
    hor_cor_orig[name] = field

ver_cor_orig = {}
for name in ver_names:
    field = epics.caget(name + ":B")
    ver_cor_orig[name] = field

hor_bpm_orig = {}
ver_bpm_orig = {}
init_hor_pos = []
init_ver_pos = []
for name in all_bpm_names:
    x_pos = epics.caget(name + ":xAvg")
    y_pos = epics.caget(name + ":yAvg")
    if name in bpm_names:
        hor_bpm_orig[name] = x_pos
        ver_bpm_orig[name] = y_pos
    init_hor_pos.append(x_pos)
    init_ver_pos.append(y_pos)


num_hor_cors, num_hor_bpms = len(hor_cor_orig), len(hor_bpm_orig)
num_ver_cors, num_ver_bpms = len(ver_cor_orig), len(ver_bpm_orig)

hor_pos_start = np.zeros(num_hor_bpms)
ver_pos_start = np.zeros(num_ver_bpms)
j = 0
for bpm_name in bpm_names:
    x_start = hor_bpm_orig[bpm_name]
    hor_pos_start[j] = x_start
    y_start = ver_bpm_orig[bpm_name]
    ver_pos_start[j] = y_start
    j += 1

hor_pos_goal = np.zeros(num_hor_bpms)
ver_pos_goal = np.zeros(num_ver_bpms)

hor_diff_vector = hor_pos_goal - hor_pos_start
ver_diff_vector = ver_pos_goal - ver_pos_start

hor_response_matrix = np.zeros([num_hor_bpms, num_hor_cors])
ver_response_matrix = np.zeros([num_ver_bpms, num_ver_cors])

i = 0
for cor_name in hor_names:
    print(i, num_hor_cors, cor_name)
    j = 0
    orig_field = hor_cor_orig[cor_name]
    field = orig_field + perturb
    epics.caput(cor_name + ":B_Set", field)
    d_field = field - orig_field
    time.sleep(0.7)

    for bpm_name in bpm_names:
        orig_pos = hor_bpm_orig[bpm_name]
        new_hor_pos = epics.caget(bpm_name + ":xAvg")
        dxdB = (new_hor_pos - orig_pos) / d_field
        hor_response_matrix[j, i] = dxdB
        j += 1
    epics.caput(cor_name + ":B_Set", orig_field)
    i += 1

inv_hor_response = np.linalg.inv(hor_response_matrix)
hor_correction_vector = np.dot(inv_hor_response, hor_diff_vector)

i = 0
for cor_name in ver_names:
    print(i, num_ver_cors, cor_name)
    j = 0
    orig_field = ver_cor_orig[cor_name]
    field = orig_field + perturb
    epics.caput(cor_name + ":B_Set", field)
    d_field = field - orig_field
    time.sleep(0.7)

    for bpm_name in bpm_names:
        orig_pos = ver_bpm_orig[bpm_name]
        new_ver_pos = epics.caget(bpm_name + ":yAvg")
        dxdB = (new_ver_pos - orig_pos) / d_field
        ver_response_matrix[j, i] = dxdB
        j += 1
    epics.caput(cor_name + ":B_Set", orig_field)
    i += 1

inv_ver_response = np.linalg.inv(ver_response_matrix)
ver_correction_vector = np.dot(inv_ver_response, ver_diff_vector)

# print(hor_correction_vector)

i = 0
for cor_name in hor_names:
    epics.caput(cor_name + ":B_Set", hor_correction_vector[i] + hor_cor_orig[cor_name])
    i += 1
i = 0
for cor_name in ver_names:
    epics.caput(cor_name + ":B_Set", ver_correction_vector[i] + ver_cor_orig[cor_name])
    i += 1
time.sleep(0.7)

final_hor_vector = np.zeros(len(all_bpm_names))
final_ver_vector = np.zeros(len(all_bpm_names))

j = 0
for name in all_bpm_names:
    x_pos = epics.caget(name + ":xAvg")
    final_hor_vector[j] = x_pos
    y_pos = epics.caget(name + ":yAvg")
    final_ver_vector[j] = y_pos
    j += 1
plt.plot(init_hor_pos)
plt.plot(final_hor_vector)
plt.show()

plt.plot(init_ver_pos)
plt.plot(final_ver_vector)
plt.show()
