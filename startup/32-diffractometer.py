from __future__ import annotations

import contextlib
import math

import ad_hoc_diffractometer as ahd
import bluesky.plans as bp
import hklpy2
import hklpy2.blocks.reflection
import hklpy2.user
from cditools.tdms import TDMSAxis
from cditools.motors import Energy
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
    ahd.register_geometry_file("./diffractometer-geometry.yml", name="cdi-geometry")
except ValueError:  # geometry already registered
    contextlib.suppress(ValueError)


# Set up goniometer and tdms angles
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

# TODO - have to combine Energy and WavelengthXRay classes for this to work
# or have a .wavelength method on Energy class
# beam_kwargs = {
#     "class": Energy
# }

# Create diffractometer
diffr = hklpy2.creator(
    prefix="XF:09IDC-",
    name="diffr",
    solver="ad_hoc",
    geometry="cdi-geometry",
    reals=real_gon_angles | real_tdms1_angles,
    class_bases=[CDIDiffractometer],
)

diffr.core.constraints["mu"].limits = (-180, 180)
diffr.core.constraints["omega1"].limits = (-15, 15)
diffr.core.constraints["chi1"].limits = (-15, 15)
diffr.core.constraints["omega2"].limits = (-11, 11)
diffr.core.constraints["chi2"].limits = (-11, 11)
diffr.core.constraints["gamma"].limits = (-6, 117)
diffr.core.constraints["delta"].limits = (-6, 117)

# Add energy
# TODO - check units
diffr.beam.energy.put(energy.energy.readback.get())

"""
# Configure after creating
# hklpy2.user.set_diffractometer(diffr)
# Add sample
diffr.add_sample("Au", a=4.08)

# Set mode
diffr.core.mode = "fixed_incidence"

# Set extras
diffr.core.extras = {
    "n_hat": (1, 1, 1), # pyright: ignore[reportAttributeAccessIssue]
    "incidence": 21.1
    }

# Set reflections
hkl1 = (1,0,0)
diffr.add_reflection(
    pseudos=hkl1,
    reals={
        "mu": 18.2,
        "omega1": 0,
        "chi1": 1.4,
        "omega2": 0,
        "chi2": 0,
        "gamma": 0.47,
        "delta": 31.84
    }
)

hkl2 = (2,0,0)
diffr.add_reflection(
    pseudos=hkl2,
    reals = {
        "mu": 3,
        "omega1": 0,
        "chi1": 0,
        "omega2": 0,
        "chi2": 0,
        "gamma": 2.39,
        "delta": 38.5,
    }
)

ub_mat = diffr.core.calc_UB(*diffr.sample.reflections)

# Done setting up.
hkl_or = (4, 0, 0)
saved_constraints = {name: (c.low_limit, c.high_limit) for name, c in diffr.core.constraints.items()}

for name in diffr.core.constraints:
    diffr.core.constraints[name].limits = (-360, 360)
# diffr1.core.forward gives a list of solutions
# diffr1.forward gives the first solution
solutions = diffr.core.forward(hkl_or)
# print table of solutions:
cahkl_table(hkl_or)
"""
