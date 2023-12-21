# This example needs SCL virtual accelerator running
# It requires pyepics installed
# In a separate terminal launch VA for MEBT:
# cd ../EPICS/
#  python virtual_accelerator.py --debug --file mebt_config.json --bunch MEBT_in.dat MEBT

from epics import caget, caput
from time import sleep
ws = 'MEBT_Diag:WS14'
setpoint = f'{ws}:Position_Set'
position = f'{ws}:Position'
speed = f'{ws}:Speed_Set'
x = f'{ws}:Hor_Cont'
y = f'{ws}:Ver_Cont'

print('Retract fork')
caput(speed, 10)
caput(setpoint, -0.02)
sleep(2)
print('Start scan')
caput(speed, 0.0005)
caput(setpoint, 0.02)
for i in range(80):
    p = caget(position)
    charge_x = caget(x)
    charge_y = caget(y)
    sleep(1)
    print(f'Position: {p},  x {charge_x} y {charge_y}')
