from epics import caget, caput
from time import sleep

magnet = 'BTF_MEBT_Mag:PS_QH01'
current_set = f'{magnet}:I_Set'
current = f'{magnet}:I'

original_value = caget(current)

caput(current_set, 200)
sleep(1)
print(f'Quadrupole value: {caget(current)}')
sleep(1)
caput(current_set, original_value)
