import numpy as np
import matplotlib.pyplot as plt

current_wave = np.load("current.npy")
beta_wave = np.load("beta.npy")

num_phases = current_wave.shape[1]

for i in range(num_phases):
    plt.plot(beta_wave[:, i])
plt.show()
