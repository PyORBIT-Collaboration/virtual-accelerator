import math
from random import randint, random
from time import sleep
import argparse
from datetime import datetime, timedelta

from ca_server import Server, Device, AbsNoise, LinearT, PhaseT, not_ctrlc, PhaseTInv
from interface_lib import PyorbitElement

PRINT_DELTA = timedelta(seconds=1)
RESET_DELTA = timedelta(seconds=5)


class Quadrupole(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    field_set_pv = 'B_Set'
    field_readback_pv = 'B'

    field_key = 'dB/dr'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_field = initial_dict[Quadrupole.field_key]
        else:
            initial_field = 0.0

        # enum setting with default and no transforms
        self.register_setting(Quadrupole.field_set_pv, default=initial_field, reason_rb=Quadrupole.field_readback_pv)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Quadrupole.field_set_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Quadrupole.field_key] = model_value
        return model_dict

    def update_readback(self, reason):
        value = None
        if reason == Quadrupole.field_set_pv:
            value = self.get_setting(Quadrupole.field_set_pv)[Quadrupole.field_key]

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Corrector(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    field_set_pv = 'B_Set'
    field_readback_pv = 'B'

    field_key = 'B'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_field = initial_dict[Corrector.field_key]
        else:
            initial_field = 0.0

        # enum setting with default and no transforms
        self.register_setting(Corrector.field_set_pv, default=initial_field, reason_rb=self.field_readback_pv)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Corrector.field_set_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Corrector.field_key] = model_value
        return model_dict

    def update_readback(self, reason):
        value = None
        if reason == Corrector.field_set_pv:
            value = self.get_setting(Corrector.field_set_pv)[Corrector.field_key]

        if value is not None:
            *_, reason_rb, transform, noise = self.settings[reason]
            self.setParam(reason_rb, transform.raw(noise.add_noise(value)))


class Cavity(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    phase_pv = 'CtlPhaseSet'
    amp_pv = 'CtlAmpSet'
    blank_pv = 'BlnkBeam'

    phase_key = 'phase'
    amp_key = 'amp'

    def __init__(self, pv_name: str, model_name: str, initial_dict=None):
        super().__init__(pv_name, model_name)
        self.model_name = model_name

        if initial_dict is not None:
            initial_phase = initial_dict[Cavity.phase_key]
            initial_amp = initial_dict[Cavity.amp_key]
        else:
            initial_phase = 180
            initial_amp = 1.0

        rand_offset = (2 * random() - 1) * 180
        phase_offset = PhaseTInv(offset=rand_offset, scaler=180 / math.pi)
        initial_phase = phase_offset.raw(initial_phase)

        # enum setting with default and no transforms
        self.register_setting(Cavity.phase_pv, default=initial_phase, transform=phase_offset)
        self.register_setting(Cavity.amp_pv, default=initial_amp)
        self.register_setting(Cavity.blank_pv, default=0.0)

    def get_setting(self, reason):
        *_, transform, _ = self.settings[reason]
        model_dict = {}
        if reason == Cavity.phase_pv:
            model_value = transform.real(self.getParam(reason))
            model_dict[Cavity.phase_key] = model_value

        elif reason == Cavity.amp_pv:
            blank_value = transform.real(self.getParam(Cavity.blank_pv))
            if blank_value == 0:
                model_value = transform.real(self.getParam(reason))
                model_dict[Cavity.amp_key] = model_value
            else:
                model_dict[Cavity.amp_key] = 0.0

        elif reason == Cavity.blank_pv:
            # placeholder in case something needs to happen here?
            pass

        return model_dict


class BPM(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    x_pv = 'xAvg'
    y_pv = 'yAvg'
    phase_pv = 'phaseAvg'

    x_key = 'x_avg'
    y_key = 'y_avg'
    phase_key = 'phi_avg'

    def __init__(self, pv_name: str, model_name: str):
        super().__init__(pv_name, model_name)

        xy_noise = AbsNoise(noise=1e-8)
        phase_noise = AbsNoise(noise=1e-4)

        rand_offset = (2 * random() - 1) * 180
        phase_offset = PhaseTInv(offset=rand_offset, scaler=180 / math.pi)

        self.register_measurement(BPM.x_pv, noise=xy_noise)
        self.register_measurement(BPM.y_pv, noise=xy_noise)
        self.register_measurement(BPM.phase_pv, noise=phase_noise, transform=phase_offset)

    def update_measurement(self, model_key, value):
        reason = None
        if model_key == BPM.x_key:
            reason = BPM.x_pv
        if model_key == BPM.y_key:
            reason = BPM.y_pv
        if model_key == BPM.phase_key:
            reason = BPM.phase_pv
        if reason is not None:
            *_, transform, noise = self.measurements[reason]
            self.setParam(reason, noise.add_noise(transform.raw(value)))


class Droid(Device):
    # Here is the only place we have raw PV suffix.
    # So if it's changed you need to modify one line
    BEEP = 'BeepFrequency'
    LED = 'LED'

    def __init__(self, name):
        super().__init__(name)
        # simplest measurement PV, definition is omitted => will be float
        self.register_measurement(Droid.BEEP)
        # enum setting with default and no transforms
        self.register_setting(Droid.LED, {'type': 'enum', 'enums': ['OFF', 'ON']}, default=1)

    def change_beeping_tone(self, new_frequency):
        self.update_measurement(Droid.BEEP, new_frequency)


class Jedi(Device):
    COOL = 'Midichlorian'
    BEARING = 'Bearing'
    HAPPY = 'Happiness'

    def __init__(self, name, initial_level=100, offset=0):
        super().__init__(name)

        # register setting without  readback but still with an offset
        self.register_setting(Jedi.COOL, default=initial_level,
                              transform=LinearT(offset=offset))

        # register setting with a readback and noise for it
        self.register_setting(Jedi.BEARING, default=180,
                              transform=PhaseT(offset=80),
                              reason_rb=Jedi.BEARING + 'Rb',
                              noise=AbsNoise(1.0))

        # There is no default HAPPY since it's a measurement
        self.register_measurement(Jedi.HAPPY)

    def get_level(self):
        return self.get_setting(Jedi.COOL)

    def happiness(self, value):
        self.update_measurement(Jedi.HAPPY, value)


parser = argparse.ArgumentParser(description='Run CA server')
parser.add_argument('--prefix', '-p', default='example', type=str,
                    help='Prefix for PVs')
args = parser.parse_args()
prefix = args.prefix + ':'

if __name__ == '__main__':
    server = Server(prefix)
    yoda = server.add_device(Jedi('Yoda', 314, offset=30))
    r2d2 = server.add_device(Droid('R2D2'))

    # create another jedi indirectly
    # the first element of the list is the class name (type)
    # the rest elements are arguments for corresponding constructor (name, initial_level)
    parameters = ['Jedi', 'Windu', 2718, 10]
    windu = globals()[parameters[0]](*parameters[1:])
    server.add_device(windu)

    all_devices = [yoda, windu, r2d2]

    print(server)
    server.start()
    # We can stop here, as a functional CA server is running and serving PVs for yoda, windu and r2d2.
    # Client can caget, caput and camonitor their PVs.
    # There is no interactions between them though.
    # We can add it right here because the server.start() call was not blocking.

    last_print = datetime.now()
    last_reset = datetime.now()
    while not_ctrlc():

        # printout all PVs
        # with period DELTA
        now = datetime.now()
        if now - last_print > PRINT_DELTA:
            # server.get_params() gives all possible PVs
            print(f'Params: {server.get_params()}')
            last_print = now
            for d in all_devices:
                d.update_readbacks()

        # reset all devices with another period
        # uses gets all setting from the server in generic way
        if now - last_reset > RESET_DELTA:
            print(f'Setting before reset {server.get_settings()}')
            for d in all_devices:
                d.reset()
            print(f'Setting after reset {server.get_settings()}')
            last_reset = now

        # In this loop we shouldn't care about EPICS specifics anymore.
        # We will just call functions of our specific devices: r2d2 and yoda.

        # So the beeping frequency is random but depends on Yoda's coolness
        # it is set with helper user-friendly functions
        r2d2.change_beeping_tone(randint(0, yoda.get_level()))
        yoda.happiness(randint(0, 100))

        # Windu's happiness is set with server's generic function
        server.update_measurements({f'{windu.name}:{Jedi.HAPPY}': randint(0, 100) - 50})

        # next line is still needed to update all clients with new values
        server.update()
        sleep(0.1)

    server.stop()

    print("Exiting... May the Force be with you!")
