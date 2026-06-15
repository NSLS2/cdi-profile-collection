"""Four-circle vertical-scattering (E4CV) diffractometers for the CDI TDMS arms.

This module builds, for **each** TDMS detector arm (``T1`` and ``T2``), an
:class:`hklpy2.diffract.DiffractometerBase` (E4CV, Eulerian 4-circle *vertical*
scattering) that drives a subset of the goniometer stack on the sample side and
a *computed* two-theta on the detector (arm) side.

It also defines and instantiates the underlying goniometer (``gon``) and TDMS
detector-arm (``T1_arm``, ``T2_arm``) devices; these were previously split
across ``20-motors.py`` and ``21-tdms.py`` and are now centralized here.

Design
------
The detector "arm" is not a true two-theta circle.  It is a stack of linear
stages riding on a large arm rotation (``ay``).  The effective scattering angle
``tth`` (in the vertical plane) is therefore a *pseudo* quantity computed from
the linear stack.  This is handled in two layers:


1. :class:`TDMSArm` -- an ophyd :class:`~ophyd.pseudopos.PseudoPositioner` that
   **is** the physical TDMS tower: it owns all the tower stages as Components
   (``ty``, ``tz``, ``ay``, ``tx``, ``ax``, ``az``, ``camay``) built directly
   from the EPICS PVs.  Only ``ty``/``tz`` are real axes (``_real``); they are
   converted to/from the detector pseudo-axes ``(tth, det_dist)``.  The ``ay``
   arm rotation is controlled separately by the TDMS system and is not a real
   axis here (it is detector-pose metadata).  The kinematics constants are
   **placeholders** to be filled in from the engineering survey (search for
   ``ENGINEERING``).

2. :class:`Vscatter4C` -- an E4CV :class:`hklpy2.diffract.DiffractometerBase`
   subclass whose ``tth`` real axis is a :class:`ProxyPositioner` forwarding to the
   ``tth`` pseudo-single of the associated :class:`TDMSArm`.  The sample-side
   real axes (``omega``, ``chi``, ``phi``) are bound to existing goniometer
   motors.

Axis mapping (NSLS-II convention: z=beam, y=up, x=inboard/outboard)
------------------------------------------------------------------
+----------+------------------------+-----------------------------+
| E4CV     | rotation about         | motor                       |
+==========+========================+=============================+
| omega    | x (inboard/outboard)   | ``gon.sam.c_lg.lrx`` (Rx2)  |
| chi      | z (beam)               | ``gon.sam.c_sm.lrz`` (Rz1)  |
| phi      | x (inboard/outboard)   | ``gon.sam.c_sm.lrx`` (Rx1)  |
| tth      | (vertical plane)       | computed from TDMS ty/tz    |
+----------+------------------------+-----------------------------+

``omega``, ``chi`` and ``phi`` are *shared* by both arms (same sample); only
``tth`` differs (``T1`` vs ``T2``).
"""

from __future__ import annotations

import numpy as np
from ophyd import Component as Cpt
from ophyd import PseudoSingle, SoftPositioner
from ophyd.pseudopos import (
    PseudoPositioner,
    pseudo_position_argument,
    real_position_argument,
)
from ophyd.device import FormattedComponent as FCpt
from ophyd.pv_positioner import PVPositioner
from ophyd.signal import EpicsSignal, EpicsSignalRO

from hklpy2.diffract import DiffractometerBase, Hklpy2PseudoAxis
from hklpy2.incident import EpicsMonochromatorRO

from cditools.motors import GON

print("LOADING 25")

# TDMS tower devices (physical detector-arm stages).
class TDMSAxis(PVPositioner):
    setpoint = Cpt(EpicsSignal, "MTR:VAL-SP")
    readback = Cpt(EpicsSignalRO, "MTR:RBV-RB0", kind="hinted")
    actuate = Cpt(EpicsSignal, "MTR:GO-CMD", kind="omitted")
    done = Cpt(EpicsSignalRO, "MTR:INPOS-STS", kind="omitted")

    def __init__(
        self,
        prefix="",
        *,
        limits=None,
        name=None,
        read_attrs=None,
        configuration_attrs=None,
        parent=None,
        egu="",
        **kwargs,
    ):
        super().__init__(
            prefix,
            limits=limits,
            name=name,
            read_attrs=read_attrs,
            configuration_attrs=configuration_attrs,
            parent=parent,
            egu=egu,
            **kwargs,
        )
        self.readback.name = self.name


class ProxyPositioner(SoftPositioner):
    """A SoftPositioner that forwards set/readback to an external positioner.

    Unlike :class:`hklpy2.devices.VirtualPositionerBase` (which targets a
    sibling axis), this proxy holds a direct reference to an arbitrary
    positioner object, supplied via the ``target`` Component kwarg.
    """

    def __init__(self, *args, target=None, **kwargs):
        if target is None:
            raise ValueError("ProxyPositioner requires a 'target' positioner.")
        self._target = target
        super().__init__(*args, **kwargs)
        # Seed our position from the target so we never report ``None`` (which
        # would break a downstream PseudoPositioner's inverse()).
        self._position = self._read_target_position()
        # Keep our position in sync with the target's readback.
        try:
            self._target.subscribe(self._target_moved, run=True)
        except Exception:  # not connected yet (e.g. no IOC); sync lazily
            pass

    def _read_target_position(self):
        """Best-effort numeric read of the target's current position."""
        try:
            value = self._target.position
        except Exception:
            value = None
        return 0.0 if value is None else value

    @property
    def position(self):
        # If we were constructed before the target had a position, recover.
        if self._position is None:
            self._position = self._read_target_position()
        return self._position

    def resync(self):
        """Re-emit the current target position to update parent caches.

        A :class:`~ophyd.pseudopos.PseudoPositioner` parent caches each real
        axis via ``SUB_READBACK`` subscriptions made in *its* ``__init__``.
        Because this soft proxy seeds its position during *its own* construction
        (before the parent subscribes), the initial value can be missed.  Call
        this after the parent is built to push the value into the parent cache.
        """
        self._set_position(self._read_target_position())

    @property
    def limits(self):
        try:
            return self._target.limits
        except Exception:
            return super().limits

    def _target_moved(self, *, value=None, **kwargs):
        if value is not None:
            self._set_position(value)

    def _setup_move(self, position, status):
        # Forward the move to the target positioner and chain its completion.
        target_status = self._target.set(position)
        self._set_position(position)

        def _finish(*args, **kwargs):
            self._done_moving()

        target_status.add_callback(_finish)
        self._started_moving = True


def _resync_real_proxies(pseudo_positioner):
    """Push each :class:`ProxyPositioner` real axis into the parent's cache.

    See :meth:`ProxyPositioner.resync`.  Run after a PseudoPositioner that uses
    proxy reals is fully constructed so its ``_real_cur_pos`` cache is seeded.
    """
    for real in pseudo_positioner._real:
        if isinstance(real, ProxyPositioner):
            real.resync()


class TDMSArm(PseudoPositioner):
    """The physical TDMS detector tower, with a computed ``tth``/``det_dist``.

    This device is the TDMS tower: it owns every physical stage as a
    Component built directly from the EPICS PVs (prefix index ``num``).  On top
    of the stages it adds two pseudo-axes -- ``tth`` and ``det_dist`` -- computed
    from the ``ty``/``tz`` linear stack.

    Likely the detector pitch and rotation will be included in the real axis as well.

    Pseudo axes
    -----------
    tth : float
        Effective scattering angle in the vertical plane (degrees).
    det_dist : float
        Sample-to-detector distance (mm).

    Real axes (``_real``)
    ---------------------
    ty
        Detector vertical stage; height above the beam (after offset).
    tz
        Tower in/out stage; radial distance from the sample (after offset).

    Other stages (Components, *not* real axes; available for detector-pose
    reduction and manual moves): ``ay`` (arm azimuth), ``tx`` (inboard/outboard
    centering), ``ax`` (pitch), ``az`` (roll), ``camay`` (camera rotation).

    Area detector & ``ay``
    ----------------------
    The TDMS detector is an *area* detector, so the E4CV ``tth`` here describes
    only the central ray (the nominal beam-center pixel) in the **vertical
    scattering plane** -- exactly the point-detector quantity ``hkl_soleil``
    solves.  ``ay`` does **not** enter this ``tth``: it is part of the
    *detector pose* (lab orientation of the detector face) and belongs in the
    downstream pixel -> Q reduction (pyFAI / xrayutilities / a Q-calibration),
    together with ``det_dist`` and the beam center.  Because ``ay`` lives in the
    pose layer rather than the E4CV solver, it is independent of the sample
    ``chi`` circle and the two never compete.  Use :meth:`detector_pose` to
    retrieve the pose metadata for reduction.

    """

    # Radial standoff added to the ``tz`` readback to get sample->detector radius
    # (mm).
    TDMS_RADIAL_OFFSET_MM = 0.0

    # Height offset added to the ``ty`` readback to get detector height above the
    # beam (mm).
    TDMS_HEIGHT_OFFSET_MM = 0.0

    # Pseudo axes.
    tth = Cpt(PseudoSingle, kind="hinted")
    det_dist = Cpt(PseudoSingle, kind="normal")

    # Only ty/tz participate in the (tth, det_dist) kinematics.
    _real = ["ty", "tz"]

    # In order of stacking from bottom to top

    # TODO replace with TDMSAxis when motions get commissioned
    # rotation with air-pads on floor (-5deg, 117deg)
    ay = FCpt(
        EpicsSignalRO,
        "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:AY}}MTR:RBV-RB0",
        kind="normal",
    )
    # Used by kinematics
    # tower translation in/out (500mm, 10,000 mm)
    tz = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:TZ}}", kind="hinted")
    # roll (-1deg, 1deg) to compensate for floor deviation, tied to feedback
    az = FCpt(
        EpicsSignalRO,
        "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AZ}}MTR:RBV-RB0",
        kind="normal",
    )
    # Used by kinematics
    # move camera up/down (-150mm, 1500mm)
    ty = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TY}}", kind="hinted")
    # shift camera inboard/outboard (-25mm, 25mm)
    tx = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TX}}", kind="normal")
    # TODO replace with TDMSAxis when motions get commissioned
    # coupled to feedback to account for floor deviation; pitch (-17deg, 75deg)
    ax = FCpt(
        EpicsSignalRO,
        "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AX}}MTR:RBV-RB0",
        kind="normal",
    )

    # rotation of camera platform
    camay = FCpt(
        TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:CAM_AY}}", kind="normal"
    )

    def __init__(self, *args, num, **kwargs):
        self._num = num
        super().__init__(*args, **kwargs)

    # ---- kinematics -------------------------------------------------------
    @classmethod
    def _stack_to_polar(cls, ty: float, tz: float) -> tuple[float, float]:
        """(ty, tz) stage positions -> (tth_deg, det_dist_mm).

        ``tth`` is the central-ray scattering angle in the vertical plane; it is
        deliberately independent of ``ay`` (see the class docstring).
        """
        h = ty + cls.TDMS_HEIGHT_OFFSET_MM
        r = tz + cls.TDMS_RADIAL_OFFSET_MM
        tth = np.rad2deg(np.arctan2(h, r))
        det_dist = float(np.hypot(h, r))
        return float(tth), det_dist

    @classmethod
    def _polar_to_stack(cls, tth: float, det_dist: float) -> tuple[float, float]:
        """(tth_deg, det_dist_mm) -> (ty, tz) stage positions."""
        h = det_dist * np.sin(np.deg2rad(tth))
        r = det_dist * np.cos(np.deg2rad(tth))
        ty = h - cls.TDMS_HEIGHT_OFFSET_MM
        tz = r - cls.TDMS_RADIAL_OFFSET_MM
        return float(ty), float(tz)

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        ty, tz = self._polar_to_stack(pseudo_pos.tth, pseudo_pos.det_dist)
        return self.RealPosition(ty=ty, tz=tz)

    @real_position_argument
    def inverse(self, real_pos):
        tth, det_dist = self._stack_to_polar(real_pos.ty, real_pos.tz)
        return self.PseudoPosition(tth=tth, det_dist=det_dist)


class Vscatter4C(DiffractometerBase):
    """Eulerian 4-circle *vertical*-scattering diffractometer for one TDMS arm.

    Real axes
    ---------
    mu, omega, chi, phi
        Bound to the shared goniometer sample motors (passed in via kwargs).

    Pseudo axes
    -----------
    h, k, l
        Reciprocal-space coordinates (solver: ``hkl_soleil``, geometry ``PETRA3 P09 EH2``).

    The ``mu``/``omega``/``chi``/``phi`` real axes are supplied by the
    :func:`make_vscatter4c` subclass factory (which wires each proxy to its
    target); this base class defines only the pseudo axes, beam, and solver
    configuration.
    """

    # Pseudo (reciprocal space) axes.
    h = Cpt(Hklpy2PseudoAxis, "", kind="hinted")
    k = Cpt(Hklpy2PseudoAxis, "", kind="hinted")
    l = Cpt(Hklpy2PseudoAxis, "", kind="hinted")  # noqa: E741

    # Beam: read photon energy/wavelength from the DCM (read-only).
    beam = Cpt(
        EpicsMonochromatorRO,
        "",
        # ENGINEERING: confirm the DCM energy/wavelength PVs.
        pv_energy="XF:09IDA-OP:1{Mono:HDCM}Energy-I",
        pv_wavelength="XF:09IDA-OP:1{Mono:HDCM}Wavelength-I",
        kind="normal",
    )

    # libhkl solver-expected ordering.
    # https://blueskyproject.io/hklpy2/diffractometers.html#solver-hkl-soleil-geometry-petra3-p09-eh2
    _pseudo = ["h", "k", "l"]
    _real = ["mu", "omega", "chi", "phi", "delta", "gamma"]

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            solver="hkl_soleil",
            geometry="PETRA3 P09 EH2",
            solver_kwargs={"engine": "hkl"},
            pseudos=["h", "k", "l"],
            reals=["mu", "omega", "chi", "phi", "delta", "gamma"],
            **kwargs,
        )
# To get to our coordinate system from the hkl PETRA3 P09 EH2 geometry,
# rotate 90 degrees down about y, and then 90 degrees up about z.
#
# https://people.debian.org/~picca/hkl/hkl.html#org9150360
# them us
#--------
# x -> z
# y -> x
# z -> y

# https://people.debian.org/~picca/hkl/hkl.html#org4a29c15
# mu [0,-1, 0] -> -rx
# rotation about -y becomes rotation about -x in our coordinates
# omega [ 0 0 1] -> ry
# rotation about z becomes rotation about y in our coordinates
# chi [1 0 0] -> rz
# rotation about x becomes rotation about z in our coordinates
# phi [0 0 1]
# locked at 0

def make_vscatter4c(name, *, mu_motor, omega_motor, chi_motor, phi_motor, **kwargs):
    """Construct a :class:`Hscatter4C` with its proxy real axes wired to targets.

    This will get simpler when we can move to ophyd async

    Parameters
    ----------
    name : str
        Device name.
    omega_motor, chi_motor, phi_motor : positioner
        Shared goniometer sample / alignment motors.
    """

    class _Wired(Vscatter4C):
        mu = Cpt(ProxyPositioner, target=mu_motor, kind="hinted")
        omega = Cpt(ProxyPositioner, target=omega_motor, kind="hinted")
        chi = Cpt(ProxyPositioner, target=chi_motor, kind="hinted")
        phi = Cpt(ProxyPositioner, target=phi_motor, kind="hinted")

    _Wired.__name__ = f"Vscatter4C_{name}"
    diffractometer = _Wired(name=name, labels=["diffractometer"], **kwargs)
    _resync_real_proxies(diffractometer)
    return diffractometer


gon = GON(prefix="XF:09IDC-OP:1{", name="gon", labels=["motors"])

T1_arm = TDMSArm(name="T1_arm", num=1, labels=["diffractometer"])
T2_arm = TDMSArm(name="T2_arm", num=2, labels=["diffractometer"])

_mu_motor = gon.align.rx
_omega_motor = gon.sam.ry
# _chi_motor = gon.sam.c_sm.lrz
_chi_motor = gon.align.rz
# _phi_motor = gon.sam.c_sm.lrx
_phi_motor = 0
_delta = ...
_gamma = ...

# Per-arm E4CV diffractometers
diff_T1 = make_vscatter4c(
    "diff_T1",
    mu_motor=_mu_motor,
    omega_motor=_omega_motor,
    chi_motor=_chi_motor,
    phi_motor=_phi_motor,
)
diff_T2 = make_vscatter4c(
    "diff_T2",
    mu_motor=_mu_motor,
    omega_motor=_omega_motor,
    chi_motor=_chi_motor,
    phi_motor=_phi_motor,
)
# PETRA3 P09 EH2 (target, but too many axis)
# SOLEIL MARS (alternate)
# SOLEIL NANOSCOPIUM ROBOT (alterate, but confusing modes)