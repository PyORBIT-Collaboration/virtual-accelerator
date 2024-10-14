from time import sleep

import pytest
import subprocess

from epics import caget, caput


@pytest.fixture(scope="module")
def va_process():
    # Start VA as a background process
    proc = subprocess.Popen(["sns_va"])

    # Wait for the VA to start serving PVs
    sleep(4.0)
    print('SNS VA should be ready by now')
    yield proc

    # Tear down: stop the background process when tests are done
    print('SNS VA will terminate.')
    proc.terminate()
    proc.wait()


def test_pv_connection(va_process):

    assert va_process.poll() is None
    x = caget('SCL_Diag:BPM04:xAvg', connection_timeout=0.1)
    assert x is not None


def test_bad_pv(va_process):

    assert va_process.poll() is None
    x = caget('BAD:PV:Name', connection_timeout=0.1)
    assert x is None


def test_corrector(va_process):
    corrector = "SCL_Mag:DCH00:B"
    corrector_set = "SCL_Mag:PS_DCH00:B_Set"
    bpm_device = "SCL_Diag:BPM04:xAvg"

    original_val = caget(corrector_set)
    settings = [(0.00, 0.0),
                (0.02, 2.3),
                (0.04, 5.0),
                (0.06, 7.7),
                (0.08, 10.0)]

    for b_set, bpm in settings:

        caput(corrector_set, b_set)
        sleep(1.5)
        b_reading = caget(corrector)
        bpm_reading = caget(bpm_device)

        print(f'Corrector value: {b_reading:.4f}/{b_set:.4f}')
        assert b_reading == pytest.approx(b_set, abs=0.001)

        print(f'BPM value: {bpm_reading:.4f}/{bpm:.4f}')
        assert bpm_reading == pytest.approx(bpm, abs=0.1)

    caput(corrector_set, original_val)

