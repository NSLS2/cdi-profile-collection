from __future__ import annotations

import contextlib
import math

import ad_hoc_diffractometer as ahd
import bluesky.plans as bp
import hklpy2
import hklpy2.blocks.reflection
import hklpy2.user
from hklpy2.incident import WavelengthXray
from hklpy2.run_utils import ConfigurationRunWrapper
from cditools.tdms import TDMSAxis
from cditools.motors import Energy
from ophyd import Component as Cpt, FormattedComponent as FCpt
from ophyd import EpicsMotor, PseudoPositioner, PseudoSingle, Signal
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from ophyd.signal import AttributeSignal
from bluesky.callbacks.best_effort import BestEffortCallback
from hklpy2.user import cahkl_table, pa
from hklpy2.utils import pick_closest_solution
from cditools.hkl_solver import CDIAdHocSolver
import xrayutilities.materials as mat


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

"""Push this to tools repo if it works"""
from ophyd.signal import DerivedSignal, EpicsSignal, EpicsSignalRO

class DegreesFromRadians(DerivedSignal):
    def inverse(self, value):
        return math.degrees(value)

    def forward(self, value):
        return math.radians(value)

class TDMSAngleAxis(TDMSAxis):
    setpoint_rad = Cpt(EpicsSignal, "VAL-SP", kind="omitted")
    readback_rad = Cpt(EpicsSignalRO, "RBV-RB0", kind="omitted")

    setpoint = Cpt(DegreesFromRadians, derived_from="setpoint_rad")
    readback = Cpt(DegreesFromRadians, derived_from="readback_rad", kind="hinted")

from hklpy2.utils import INTERNAL_XRAY_ENERGY_UNITS, INTERNAL_LENGTH_UNITS
from ophyd import Device
XRAY_ENERGY_EQUIVALENT_: float = 8.065_543_937e5
A_KEV: float = 1e7 / XRAY_ENERGY_EQUIVALENT_  # 1 Angstrom ~= 12.39842 keV

class CDIBeam(Device):
    """
    hklpy2 wants to read energy from an ophyd device that has specific signals,
    so this is needed to get energy from the already existing CDI Energy defined 
    in `cditools.motors`. Further, we don't want functionality for setting energy
    through hklpy2, which is why this doesn't inherit from any in `hklpy2.incident`
    """
    energy = Cpt(AttributeSignal, attr="_energy", kind="hinted", write_access=False)
    wavelength = Cpt(AttributeSignal, attr="_wavelength", kind="hinted", write_access=False)
    energy_units = Cpt(Signal, value=INTERNAL_XRAY_ENERGY_UNITS, kind="config")
    wavelength_units = Cpt(Signal, value=INTERNAL_LENGTH_UNITS, kind="config")

    def __init__(self, cdi_energy_device: Energy, *args, **kwargs):
        self.cdi_energy_device = cdi_energy_device
        super().__init__(*args, **kwargs)

        # make sure energy/wavelength are initalized
        self.energy.get()
        self.wavelength.get()

    @property
    def _energy(self) -> float:
        return self.cdi_energy_device.energy.position

    @property
    def _wavelength(self) -> float:
        return self._to_wavelength(self._energy)

    def _to_wavelength(self, value: float) -> float:
        """Convert E to lambda."""
        from hklpy2.utils import convert_units

        energy = convert_units(
            value, self.energy_units.get(), INTERNAL_XRAY_ENERGY_UNITS
        )
        return convert_units(
            A_KEV / energy, INTERNAL_LENGTH_UNITS, self.wavelength_units.get()
        )

    def _to_energy(self, value: float) -> float:
        """Convert lambda to E."""
        from hklpy2.utils import convert_units

        wavelength = convert_units(
            value, self.wavelength_units.get(), INTERNAL_LENGTH_UNITS
        )
        return convert_units(
            A_KEV / wavelength, INTERNAL_XRAY_ENERGY_UNITS, self.energy_units.get()
        )

# Register geometry
try:
    ahd.register_geometry_file("./diffractometer-geometry.yml", name="cdi-geometry")
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

# incase TDMS does use radians
# real_tdms1_angles = {
#     "gamma": {
#         "class": TDMSAngleAxis,
#         "prefix": "XF:09IDC-ES:1{TDMS:T1-Ax:AX}MTR:"
#     },
#     "delta": {
#         "class": TDMSAngleAxis,
#         "prefix": "XF:09IDC-ES:1{TDMS:A1-Ax:AY}MTR:"
#     }
# }

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

if "energy" not in locals():
    energy = Energy(prefix="XF:09IDA-OP:1{", name="energy", labels=["dcm"])

diffr = hklpy2.creator(
    prefix="XF:09IDC-",
    name="diffr",
    solver="cdi_ad_hoc",
    geometry="cdi-geometry",
    beam_kwargs={
        "class": CDIBeam,
        "cdi_energy_device": energy
    },
    reals=real_gon_angles | real_tdms1_angles,
)

# rotation constraints
diffr.core.constraints["mu"].limits = (-180, 180)
diffr.core.constraints["omega1"].limits = (-15, 15)
diffr.core.constraints["chi1"].limits = (-15, 15)
diffr.core.constraints["omega2"].limits = (-11, 11)
diffr.core.constraints["chi2"].limits = (-11, 11)
diffr.core.constraints["gamma"].limits = (-6, 117)
diffr.core.constraints["delta"].limits = (-6, 117)

# ruby sample
diffr.add_sample("Ruby", a=4.7602, c=12.9933, gamma=120)

# gold sample
diffr.add_sample("Au", a=mat.Au.a)

# incase CDIBeam doesn't work
# diffr.beam.energy.put(10.002)

# wait for connection
diffr.wait_for_connection(timeout=10)

hklpy2.user.set_diffractometer(diffr)

# saves configuration of diffractometer in every run
crw = ConfigurationRunWrapper(diffr)
if 'RE' in locals():
    RE.preprocessors.append(crw.wrapper)