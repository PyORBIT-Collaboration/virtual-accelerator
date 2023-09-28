import numpy as np
import matplotlib.pyplot as plt

beta_wave = np.load("delta_energies.npy")

num_phases = beta_wave.shape[0]

for i in range(num_phases):
    plt.plot(beta_wave[i,:])
plt.show()
