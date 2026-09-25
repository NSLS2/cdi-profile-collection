print(f"Loading {__file__!r} ...")

import numpy as np
import scipy as sp
from decimal import Decimal

import bluesky.plan_stubs as bps

def trunc(inp):
    num = Decimal(str(inp))

    return float(num.quantize(Decimal('0.000001')))

def decomp_dev(dev):
    comp_list = bps.read(dev)
    dev_list = {key: val for key, val in comp_list.items() if not key.endswith('setpoint')}
    return dev_list 
