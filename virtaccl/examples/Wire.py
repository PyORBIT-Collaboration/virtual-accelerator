# This example needs SCL virtual accelerator running
# It requires pyepics installed
# In a separate terminal launch VA for MEBT:
# cd ../EPICS/
#  python virtual_accelerator.py --debug --refresh_rate 0.5 --bunch MEBT_in.dat --sequences MEBT

from epics import caget, caput
from time import sleep
ws = 'MEBT_Diag:WS14'
set_point = f'{ws}:Position_Set'
position = f'{ws}:Position'
speed = f'{ws}:Speed_Set'
x = f'{ws}:Hor_Cont'
y = f'{ws}:Ver_Cont'

print('Retract fork')
caput(speed, 100)
caput(set_point, -25)
sleep(2)
print('Start scan')
caput(speed, 0.5)
caput(set_point, 25)
print(f'{"Position":^12s}  {"x":^8s}  {"y":^8s}')
for i in range(100):
    p = caget(position)
    charge_x = caget(x)
    charge_y = caget(y)
    sleep(1)
    print(f'{p:12.2f}  {charge_x:8.3f}  {charge_y:8.3f}')
