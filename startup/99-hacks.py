print(f'LOADING {__file__}...')

from ophyd import (PVPositioner, Component as Cpt, EpicsSignal, EpicsSignalRO,
        Signal, EpicsMotor)
from ophyd.utils import ReadOnlyError

from bluesky.preprocessors import SupplementalData

import numpy as np
from scipy.interpolate import CubicSpline

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
#class IVUGap(PVPositioner):
#   setpoint = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr-SP") 
#   readback = Cpt(EpicsSignalRO,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.RBV")
#   actuate = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr-Go")
#   done = Cpt(EpicsSignalRO, "SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.DMOV")
#   stp = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.STOP")

#class InsertionDevice(Device):
#    gap = Cpt(IVUGap, name='')
#
#    def set(self, *args, **kwargs):
#        return self.gap.set(*args, **kwargs)
#
#    def stop(self, *, success=False):
#        return self.gap.stp(success=success)
#
#
#ivu = InsertionDevice('SR:C09-ID:G1{IVU18:1', name='ivu')
