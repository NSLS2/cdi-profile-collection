print(f"Loading {__file__!r} ...")

import numpy as np
import scipy as sp
from decimal import Decimal
import xrayutilities as xu
import bluesky.plan_stubs as bps

def trunc(inp):
    num = Decimal(str(inp))

    return float(num.quantize(Decimal('0.000001')))

def decomp_dev(dev):
    comp_list = bps.read(dev)
    dev_list = {key: val for key, val in comp_list.items() if not key.endswith('setpoint')}
    return dev_list 

def get_flux():
    e = -1.602e-19
    w_e = 34.8
    gn2=xu.materials.Amorphous("N2", density = 1.25)
    
    E = energy.energy.position*1000.

    I1 = f460.channel1.get()
    I2 = f460.channel2.get()  
    
    eff = 1-np.exp(-5e4/gn2.absorption_length(E)) 
    att1to2 = np.exp(-220e3/gn2.absorption_length(E))
    
    F1 = (I1/e)/(E/w_e)/eff
    F2 = 1.13*(I2/e)/(E/w_e)/eff

    print(f"incident flux (I1): {F1:.2g}, transmitted flux (I2): {F2:.2g}, adjust for drift {F2/att1to2:.3g}")

    return F1,F2

