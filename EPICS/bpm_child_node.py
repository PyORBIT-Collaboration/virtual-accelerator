import math


class BPMclass:
    def __init__(self):
        self.phi_avg = None
        self.x_avg = None
        self.y_avg = None
        self.energy = None

    def trackActions(self, actionsContainer, paramsDict):
        bunch = paramsDict["bunch"]
        part_num = bunch.getSizeGlobal()
        if part_num > 0:
            rf_freq = 402.5e6
            BPM_name = paramsDict["parentNode"].getName()
            sync_part = bunch.getSyncParticle()
            phase_coeff = 360.0 / (sync_part.beta() * 2.99792458e8 / rf_freq)
            sync_phase = (sync_part.time() * rf_freq * 2 * math.pi) % (2 * math.pi) - math.pi
            sync_energy = sync_part.kinEnergy()
            x_avg, xp_avg, y_avg, yp_avg, z_avg, dE_avg = 0, 0, 0, 0, 0, 0
            for n in range(part_num):
                x, xp, y, yp, z, dE = bunch.x(n), bunch.xp(n), bunch.y(n), bunch.yp(n), bunch.z(n), bunch.dE(n)
                x_avg += x
                xp_avg += xp
                y_avg += y
                yp_avg += yp
                z_avg += z
                dE_avg += dE
            x_avg /= part_num
            xp_avg /= part_num
            y_avg /= part_num
            yp_avg /= part_num
            z_avg /= part_num
            phi_avg = phase_coeff * z_avg + sync_phase
            dE_avg /= part_num
            self.phi_avg = phi_avg
            self.x_avg = x_avg
            self.y_avg = y_avg
            self.energy = sync_energy
            #print(BPM_name + " : " + str(self.x_avg))

    def getPhaseAvg(self):
        return self.phi_avg

    def getXAvg(self):
        return self.x_avg

    def getYAvg(self):
        return self.y_avg

    def getEnergy(self):
        return self.energy
