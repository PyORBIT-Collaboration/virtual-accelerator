from time import sleep

import pytest
import subprocess

from epics import caget, caput


@pytest.fixture(scope="module")
def va_process():
    # Start VA as a background process
    proc = subprocess.Popen(["btf_va"])

    # Wait for the VA to start serving PVs
    sleep(4.0)
    print('BTF VA should be ready by now')
    yield proc

    # Tear down: stop the background process when tests are done
    print('BTF VA will terminate.')
    proc.terminate()
    proc.wait()


def test_pv_connection(va_process):

    assert va_process.poll() is None
    x = caget('ITSF_Diag:BPM04_4:xAvg', connection_timeout=0.1)
    assert x is not None


def test_bad_pv(va_process):

    assert va_process.poll() is None
    x = caget('BAD:PV:Name', connection_timeout=0.1)
    assert x is None


def test_corrector(va_process):
    corrector = "BTF_MEBT_Mag:DCH00:B"
    corrector_set = "BTF_MEBT_Mag:PS_DCH00:I_Set"
    bpm_device = "ITSF_Diag:BPM04_4:xAvg"

    original_val = caget(corrector_set)
    settings = [(0.0, -0.03, 0.0),
                (0.5, -0.13, -0.0009),
                (1.0, -0.24, -0.0019),
                (1.5, -0.35, -0.0028),
                (2.0, -0.45, -0.0037)]

    for i_set, bpm, b_field in settings:

        caput(corrector_set, i_set)
        sleep(1.5)
        b_reading = caget(corrector)
        bpm_reading = caget(bpm_device)

        print(f'Corrector value: {b_reading:.4f}/{b_field:.3f}')
        assert b_reading == pytest.approx(b_field, abs=0.001)

        print(f'BPM value: {bpm_reading:.4f}/{bpm:.1f}')
        assert bpm_reading == pytest.approx(bpm, abs=0.1)

    caput(corrector_set, original_val)

