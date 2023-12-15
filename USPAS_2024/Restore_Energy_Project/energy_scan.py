import json
import math
import time
import numpy as np
from matplotlib import pyplot as plt
import epics
from scipy.optimize import curve_fit

with open('/Users/4wc/SNS/PyORBIT/virtual_accelerator/virtual-accelerator/EPICS/va_offsets.json', "r") as json_file:
    offset_dict = json.load(json_file)


# Define the cosine function to fit
def cosine_function(x, amplitude, frequency, phase, offset):
    return amplitude * np.cos(np.radians(frequency * x - phase)) + offset


cav1_name = "SCL_LLRF:FCM23a"
cav2_name = "SCL_LLRF:FCM23b"
cav3_name = "SCL_LLRF:FCM23c"
cav4_name = "SCL_LLRF:FCM23d"

# Determine the cavity to scan and name of the file
cavity_to_scan = cav4_name
file_path = cavity_to_scan + '_fix.txt'

# Cavity phases for after failure
cav2_phase_fix = -166.586670448
cav3_phase_fix = 154.090498149090992
cav4_phase_fix = -175.03

# Phase such that last cavity is only bunching
bunching_phase = 125.359758635

# Use this to set cavities on and off (0 = off, 1 = on)
cav_amps = {cav1_name: 0.0,
            cav2_name: 1.0,
            cav3_name: 1.0,
            cav4_name: 1.0}

# Use this to change cavity phases (None to keep unchanged)
cav_phases = {cav1_name: None,
              cav2_name: cav2_phase_fix,
              cav3_name: cav3_phase_fix,
              cav4_name: cav4_phase_fix}

cavities = [cav1_name, cav2_name, cav3_name, cav4_name]
for cavity in cavities:
    epics.caput(cavity + ":CtlAmpSet", cav_amps[cavity])
    if cav_phases[cavity] is not None:
        epics.caput(cavity + ":CtlPhaseSet", cav_phases[cavity])

time.sleep(1.1)

BPM1_name = "SCL_Diag:BPM23"
BPM2_name = "SCL_Diag:BPM32"
BPM1_pos = 93.662237
BPM2_pos = 164.680459
length = BPM2_pos - BPM1_pos

# Energy guesses for using the BPMs to measure energy. The first set is for before failure.
# energy_guesses = {cav1_name: 0.945,
#                  cav2_name: 0.96,
#                  cav3_name: 0.975,
#                  cav4_name: 0.987}

# Energy guesses for after cavity failure.
energy_guesses = {cav2_name: 0.945,
                  cav3_name: 0.96,
                  cav4_name: 0.975}

# This function returns the energy (GeV) from the phases of two cavities.
def find_energy(phase_first, phase_second, guess, bpm_distance):
    phase_first += 180
    phase_second += 180
    energy = math.inf
    n = 0
    while energy > guess:
        dt = ((phase_second + n * 360) - phase_first) / (402.5e6 * 360)
        beta = bpm_distance / dt / 299792458
        if 1 > beta > 0:
            gamma = 1 / math.sqrt(1 - beta * beta)
            energy = (gamma - 1) * 0.939294
        n += 1

    low_n = n - 1
    low_dt = ((phase_second + low_n * 360) - phase_first) / (402.5e6 * 360)
    low_beta = bpm_distance / low_dt / 299792458
    if 1 > low_beta > 0:
        low_gamma = 1 / math.sqrt(1 - low_beta * low_beta)
        low_energy = (low_gamma - 1) * 0.939294
    else:
        low_energy = 0
    low_diff = abs(guess - low_energy)

    high_n = n - 2
    high_dt = ((phase_second + high_n * 360) - phase_first) / (402.5e6 * 360)
    high_beta = bpm_distance / high_dt / 299792458
    if 1 > high_beta > 0:
        high_gamma = 1 / math.sqrt(1 - high_beta * high_beta)
        high_energy = (high_gamma - 1) * 0.939294
    else:
        high_energy = 0
    high_diff = abs(guess - high_energy)

    # print(low_energy, guess, high_energy)

    if low_diff < high_diff:
        return low_energy
    else:
        return high_energy


num = 91
phases = np.linspace(-180, 180, num)
energies = np.zeros(num)

initial_phase = epics.caget(cavity_to_scan + ":CtlPhaseSet")
phase1 = epics.caget(BPM1_name + ":phaseAvg") - offset_dict[BPM1_name]
phase2 = epics.caget(BPM2_name + ":phaseAvg") - offset_dict[BPM2_name]
initial_energy = find_energy(phase1, phase2, energy_guesses[cavity_to_scan], length)

print(initial_phase, initial_energy)

for i in range(len(phases)):
    epics.caput(cavity_to_scan + ":CtlPhaseSet", phases[i])

    time.sleep(0.7)

    phase1 = epics.caget(BPM1_name + ":phaseAvg") - offset_dict[BPM1_name]
    phase2 = epics.caget(BPM2_name + ":phaseAvg") - offset_dict[BPM2_name]
    energies[i] = find_energy(phase1, phase2, energy_guesses[cavity_to_scan], length)

    print(phases[i], energies[i])

epics.caput(cavity_to_scan + ":CtlPhaseSet", initial_phase)
print('Initial phase, energy:', initial_phase, initial_energy)

initial_guess = [0.01, 1.0, 0.0, 1.0]
bounds = ([0.0001, 0.5, -180, -np.inf], [0.1, 1.5, 180, np.inf])
fit_params, _ = curve_fit(cosine_function, phases, energies, p0=initial_guess, bounds=bounds, maxfev=10000)
phases2 = np.linspace(-360, 360, num * 2)
fitted_curve = cosine_function(phases2, *fit_params)
fitted_curve_mod = cosine_function(phases, fit_params[0], fit_params[1], 0.0, fit_params[3])

sync_phase = initial_phase - fit_params[2]
if sync_phase > 180:
    sync_phase = -360 + sync_phase
elif sync_phase < -180:
    sync_phase = 360 + sync_phase

# Print the fitted parameters
print('Fitted Parameters:')
print('Amplitude:', fit_params[0])
print('Frequency:', fit_params[1])
print('Phase:', fit_params[2])
print('Offset:', fit_params[3])

print('Initial phase, sync phase:', initial_phase, -sync_phase)

with open(file_path, "w") as file:
    file.write(cavity_to_scan + '\n')
    file.write('\n')

    file.write('Initial Phase:    ' + str(initial_phase) + '\n')
    file.write('Sync Phase:    ' + str(-sync_phase) + '\n')
    file.write('Initial Energy:    ' + str(initial_energy) + '\n')
    file.write('\n')

    file.write('Amplitude:    ' + str(fit_params[0]) + '\n')
    file.write('Frequency:    ' + str(fit_params[1]) + '\n')
    file.write('Phase:    ' + str(fit_params[2]) + '\n')
    file.write('Offset:    ' + str(fit_params[3]) + '\n')
    file.write('\n')

    for i in range(len(phases)):
        row_str = str(phases[i]) + '    ' + str(energies[i]) + '\n'
        file.write(row_str)

plt.plot(phases, energies, 'o')
plt.plot(initial_phase, initial_energy, 'D')
plt.plot(phases2, fitted_curve, label='Fitted Cosine Curve')
plt.plot(phases, fitted_curve_mod, label='Fitted Cosine Curve')
plt.plot(sync_phase, initial_energy, 'D')
plt.show()
