import math
from typing import Dict, Any

from virtaccl.beam_line import Device, AbsNoise, PhaseTInv, LinearTInv
from virtaccl.site.SNS_Linac.virtual_devices import Cavity, WireScanner


# Here are the device definitions that take the information from PyORBIT and translates/packages it into information for
# the server.
#
# All the devices need a name that will determine the name of the device in the EPICS server. If the corresponding
# element in PyORBIT has a different name, then it will need to be specified in the declaration as the model_name. If
# the device has settings (values changed by the user), they can be given initial values to match the model using
# initial_dict. These initial settings need to be in a dictionary using the appropriate keys defined by PyORBIT to
# differentiate different parameters. And finally, if the device has a phase, both setting and measurement, they can be
# given an offset using phase_offset.
#
# The strings denoted with a "_pv" are labels for EPICS. Changing these will alter the EPICS labels for values on the
# server. The strings denoted with a "_key" are the keys for parameters in PyORBIT for that device. These need to match
# the keys PyORBIT uses in the paramsDict for that devices corresponding PyORBIT element.


class SNS_Cavity(Cavity):
    # EPICS PV names
    net_power_pv = 'NetPwr'
    mode_pv = 'AFF_Mode'
    reset_pv = 'AFF_Reset'
    MPS_pv = 'FPAR_LDmp_swmask_set'

    def __init__(self, name: str, model_name: str = None, initial_dict: Dict[str, Any] = None, phase_offset=0,
                 design_amp=15):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name, initial_dict, phase_offset, design_amp)

        net_pwr_name = name.split(':')[0] + ':Cav' + name[-1] + ':' + SNS_Cavity.net_power_pv
        mps_name = name.replace('FCM', 'HPM', 1) + ':' + SNS_Cavity.MPS_pv

        if 'SCL' not in name:
            self.register_readback(SNS_Cavity.net_power_pv, Cavity.amp_pv, server_key_override=net_pwr_name)
        self.register_setting(SNS_Cavity.mode_pv, default=0.0)
        self.register_setting(SNS_Cavity.reset_pv, default=0.0)
        self.register_setting(SNS_Cavity.MPS_pv, default=0.0, server_key_override=mps_name)


class SNS_Dummy_BCM(Device):
    # EPICS PV names
    freq_pv = 'FFT_peak2'

    # PyORBIT parameter keys
    beta_key = 'beta'  # [c]

    c_light = 2.99792458e+8  # [m/s]
    ring_length = 247.9672  # [m]

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server.
        self.register_measurement(SNS_Dummy_BCM.freq_pv)

    # Updates the measurement values on the server. Needs the model key associated with it's value and the new value.
    # This is where the measurement PV name is associated with it's model key.
    def update_measurements(self, new_params: Dict[str, Dict[str, Any]] = None):
        for model_name, param_dict in new_params.items():
            if model_name == self.model_name:
                for param_key, model_value in param_dict.items():
                    if param_key == SNS_Dummy_BCM.beta_key:
                        reason = SNS_Dummy_BCM.freq_pv
                        beta = model_value
                        freq = beta * SNS_Dummy_BCM.c_light / SNS_Dummy_BCM.ring_length
                        self.update_measurement(reason, freq)


class SNS_WireScanner(WireScanner):
    x_amp_pv = 'Hor_Amp_gs'
    y_amp_pv = 'Ver_Amp_gs'
    initial_move_pv = 'Scan_InitialMove_rb'
    scan_step_pv = 'Scan_Steps_rb'
    step_size_pv = 'Scan_StepSize_rb'
    trace_pv = 'Scan_Traces/step_rb'
    length_pv = 'Scan_Length'
    stroke_pv = 'Stroke'
    oor_pv = 'Scan_OOR'

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, model_name)

        self.register_setting(SNS_WireScanner.x_amp_pv, default=10)
        self.register_setting(SNS_WireScanner.y_amp_pv, default=10)
        self.register_setting(SNS_WireScanner.initial_move_pv, default=0)
        self.register_setting(SNS_WireScanner.scan_step_pv, default=10)
        self.register_setting(SNS_WireScanner.step_size_pv, default=0.01)
        self.register_setting(SNS_WireScanner.trace_pv, default=0)
        self.register_setting(SNS_WireScanner.length_pv, default=10)
        self.register_setting(SNS_WireScanner.stroke_pv, default=0)
        self.register_setting(SNS_WireScanner.oor_pv, default=0)


class SNS_Dummy_ICS(Device):
    # EPICS PV names
    beam_on_pv = 'Gate_BeamOn:RR'
    event_pv = 'Util:event46'
    trigger_pv = 'Gate_BeamOn:SSTrigger'

    def __init__(self, name: str, model_name: str = None):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        rr_noise = AbsNoise(noise=1e-2)
        event_noise = AbsNoise(noise=1e-9)

        # Registers the device's PVs with the server.
        self.register_measurement(SNS_Dummy_ICS.beam_on_pv, noise=rr_noise)
        self.register_measurement(SNS_Dummy_ICS.event_pv, noise=event_noise)
        self.register_setting(SNS_Dummy_ICS.trigger_pv, default=0)

    def update_measurements(self, new_measurements: Dict[str, Dict[str, Any]] = None):
        self.update_measurement(SNS_Dummy_ICS.beam_on_pv, 1)
        self.update_measurement(SNS_Dummy_ICS.event_pv, 0)

    def get_model_optics(self) -> Dict[str, Dict[str, Any]]:
        return {}


class SNS_Bunch_Dumper(Device):
    # EPICS PV names
    file_name_pv = 'bunch_file'
    file_name_key = 'out_file'

    def __init__(self, name: str, model_name: str = None, initial_file_name: str = 'bunch.dat'):
        if model_name is None:
            self.model_name = name
        else:
            self.model_name = model_name
        super().__init__(name, self.model_name)

        # Registers the device's PVs with the server.
        self.register_setting(SNS_Bunch_Dumper.file_name_pv, default=initial_file_name, definition={'type': 'string'})

    def get_model_optics(self):
        file_name = self.parameters[SNS_Bunch_Dumper.file_name_pv].get_value()
        params_dict = {SNS_Bunch_Dumper.file_name_key: file_name}
        model_dict = {self.model_name: params_dict}
        return model_dict
