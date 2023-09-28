from pathlib import Path


class OrbitModel:
    def __init__(self, *args, **kw):
        # read lattice
        # run design particle
        # initialize all settings (cavity and measurements (BPM)
        # store initial settings
        self.initial_optics = dict()

    def get_settings(self, setting_names: list[str]=None):
        return {'SCL_LLRF:FCM01a:setCtlPhase': 23,
                }

    def get_measurements(self, measurement_names: list[str]=None):
        # think about more useful parameters that are not real
        # for fake parameters use XXX_Phys
        print(self)
        return {'SCL_Diag:BPM00:phaseAvg': 23,
                'SCL_Phys:BPM00:phaseAvg': 188,
                }

    def track(self, number_of_particles=1000) -> dict[str, float]:
        # freeze optics (clone)
        # and track new setup
        # if nothing changed do not track
        pass

    def update_optics(self, changed_optics: dict[str, float]):
        # update optics
        # figure out the most upstream element that changed
        # do not track here yet
        for k, v in changed_optics.items():
            print(f'New value of {k} is {v}')
            # { SCL_LLRF:FCM01a:setPhase: 23,
            #   SCL_Mag:Pkpkpgk: 10 }
        pass

    def reset_optics(self):
        self.update_optics(self.initial_optics)

    def save_optics(self, filename: Path=None):
        # timestamp being default name
        pass

    def load_optics(self, filename: Path):
        pass



class BrandonModel (OrbitModel):
    pass