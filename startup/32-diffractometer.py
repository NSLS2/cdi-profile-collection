from __future__ import annotations

import contextlib
import math

import ad_hoc_diffractometer as ahd
import bluesky.plans as bp
import hklpy2
import hklpy2.blocks.reflection
import hklpy2.user
from cditools.tdms import TDMSAxis
from ophyd import Component as Cpt, FormattedComponent as FCpt
from ophyd import EpicsMotor
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from hklpy2.user import cahkl_table
from hklpy2.utils import pick_closest_solution
from cditools.diffractometer import CDIDiffractometer


"""
There is a lot of setup for the diffractometer.

We register the custom geometry before creating the diffractometer object.
For this to work, hklpy_solvers and ad-hod-diffractometer must be available.

The TDMS angles must be defined as KeyValueMaps in order to get the
setpoint, readback, actuate, and done signals. This requires that we also
use hklpy2.creator() rather than DiffractometerBase directly, because the
DiffractometerBase.__init__() method does not accept a KeyValueMap for the
angles.
"""

# Register geometry
try:
    ahd.register_geometry_file("../diffractometer-geometry.yml", name="cdi-geometry")
except ValueError:  # geometry already registered
    contextlib.suppress(ValueError)


real_gon_angles = {
    "mu": "OP:1{Gon:1-Ax:Ry}Mtr",
    "omega1": "OP:1{Gon:1-Ax:Rx2}Mtr",
    "chi1": "OP:1{Gon:1-Ax:Rz2}Mtr",
    "omega2": "OP:1{Gon:1-Ax:Rx1}Mtr",
    "chi2": "OP:1{Gon:1-Ax:Rz1}Mtr"
}
real_tdms1_angles = {
    "gamma": {
        "class": TDMSAxis,
        "prefix": "XF:09IDC-ES:1{TDMS:T1-Ax:AX}MTR:"
    },
    "delta": {
        "class": TDMSAxis,
        "prefix": "XF:09IDC-ES:1{TDMS:A1-Ax:AY}MTR:"
    }
}
real_tdms2_angles = {
    "gamma": {
        "class": TDMSAxis,
        "prefix": "XF:09IDC-ES:1{TDMS:T2-Ax:AX}MTR:"
    },
    "delta": {
        "class": TDMSAxis,
        "prefix": "XF:09IDC-ES:1{TDMS:A2-Ax:AY}MTR:"
    }
}

diffr = hklpy2.creator(
    prefix="XF:09IDC-",
    name="diffr",
    solver="ad_hoc",
    geometry="cdi-geometry",
    reals=real_gon_angles | real_tdms1_angles,
    class_bases=[CDIDiffractometer]
)
