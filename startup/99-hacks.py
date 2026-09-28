print(f'LOADING {__file__}...')

from ophyd import (PVPositioner, Component as Cpt, EpicsSignal, EpicsSignalRO,
        Signal, EpicsMotor, DerivedSignal)
from ophyd.utils import ReadOnlyError

from bluesky.preprocessors import SupplementalData

import numpy as np
from scipy.interpolate import CubicSpline
import asyncio

#use BPM as monitor for now.  add ion chambers later
sd = SupplementalData(baseline=None,monitors=[tetra.posX,tetra.posY,tetra.sumI],flyers=None)
RE.preprocessors.append(sd)

gap_ev = [
    [ 4629,   1637],
    [ 4799,   1707],
    [ 4999,   1792],
    [ 5199,   1880],
    [ 5399,   1968],
    [ 5450,   1991],
    [ 5599,   2060],
    [ 5799,   2153],
    [ 5999,   2248],
    [ 7001,   2721],
    [ 8001,   3152],
    [ 9000,   3520],
    [10001,   3822],
    [12001,   4243],
    [14001,   4479],
    [16001,   4605],
    [18001,   4670],
    [20001,   4702],
    [25001,   4731],
]

def make_energy_lists(E1,E2,n):
    cs = CubicSpline([x[1] for x in gap_ev], [x[0] for x in gap_ev],
            extrapolate=False)

    gap = np.zeros(n)
    bragg = np.zeros(n)
    i = 0

    for ev in np.linspace(E1,E2,num=n):
        for h in range(11, 1, -2):
            gap[i] = cs(ev/h)
            if not np.isnan(gap[i]):
                break
        gap[i]=int(gap[i])
        bragg[i]= (np.arcsin(12398. / ev / 2. / 3.136) + 0.0001744) * 180./3.14
        i+=1

    return gap, bragg

vpm_x = EpicsMotor("XF:09IDA-OP:1{Mir:VPM-Ax:TX}Mtr",name='vpm_x')

async def co_get_T():
    T = await bank.read()
    return T['bank-total_transmission']['value']

def get_T():
	t = asyncio.run(co_get_T())
	print(f"Current transmission is {t:0.3f}.")
	return t

#TDMS doesn't have an offset field in its EPICS implementation
class OffsetTDMSSignal(DerivedSignal):
    def __init__(self, *args, offset=0., **kwargs):
        self._offset = offset
        super().__init__(*args,**kwargs)

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, val):
        self._offset = val

#don't want a forward for the TDMS at this point
#    def forward(self,value):
#        return value - self._offset

    def inverse(self, value):
        if value is None:
            return None
        return value + self._offset

class OffsetTDMSDevice(Device):
    dial_val = Cpt(EpicsSignal, 'MTR:RBV-RB0', kind='normal')
    user_val = Cpt(OffsetTDMSSignal, derived_from='dial_val', offset=0., kind='hinted')

tdms_arm1_ay = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A1-Ax:AY}', name='arm1_ay')
tdms_arm1_ay.user_val.offset = -11.74
tdms_arm2_ay = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A2-Ax:AY}', name='arm2_ay')
tdms_arm2_ay.user_val.offset = -21. 

tdms_arm1_tz = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A1-Ax:TZ}', name='arm1_tz')
tdms_arm1_tz.user_val.offset = -0. 
tdms_arm2_tz = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A2-Ax:TZ}', name='arm2_tz')
tdms_arm2_tz.user_val.offset = -0. 

tdms_arm1_ty = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T1-Ax:TY}', name='arm1_ty')
tdms_arm1_ty.user_val.offset = -0. 
tdms_arm2_ty = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T2-Ax:TY}', name='arm2_ty')
tdms_arm2_ty.user_val.offset = -0. 
