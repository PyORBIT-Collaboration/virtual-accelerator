# This example needs BTF virtual accelerator running in a separate window
# It has two parts
# First it will ramp a magnet until beam is lost at BS36
# It will then reset
# Second it will insert FC12 and measure beam
# While FC12 is inserted no beam will be read at BS36


from epics import caget, caput
from time import sleep

magnet = 'BTF_MEBT_Mag:PS_QV10'
current_set = f'{magnet}:I_Set'
current = f'{magnet}:I'

BS = 'ITSF_Diag:BS36_LP:CurrentAvrGt'
FC = 'ITSF_Diag:FC12:CurrentAvrGt'
FC_state = 'ITSF_Diag:FC12:State_Set'

original_value = caget(current)

print(f'Initial: QH10 current: {caget(current)}', f'BS36 value: {caget(BS)}')

for i in range(10):
    new_current = caget(current) + 1/2
    caput(current_set, new_current)
    sleep(1)
    print(f'QH10 current: {caget(current)}', f'BS36 value: {caget(BS)}')

caput(current_set, original_value)
sleep(1)
print(f'Reset values: QH10 current: {caget(current)}', f'BS36 value: {caget(BS)}')
sleep(1)

print(f'Before FC12 insert: FC12 value: {caget(FC)}', f'BS36 value: {caget(BS)}') 
caput(FC_state, 1)
sleep(1)
print(f'FC12 inserted: FC12 value: {caget(FC)}', f'BS36 value: {caget(BS)}')
caput(FC_state, 0)
sleep(1)
print(f'FC12 retracted: FC12 value: {caget(FC)}', f'BS36 value:{caget(BS)}')
