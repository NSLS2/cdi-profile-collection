from ophyd.device import Component as Cpt
from ophyd.device import Device
from ophyd.device import FormattedComponent as FCpt
from ophyd.pv_positioner import PVPositioner
from ophyd.signal import EpicsSignal, EpicsSignalRO

print("LOADING 21")


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


class TDMSTower(Device):
    # TODO replace with TDMSAxis when motions get commissioned
    # rotation with air-pads on floor (-5deg, 117deg)
    ay = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:AY}}MTR:RBV-RB0")

    # tower translation in/out (500mm, 10,000 mm)
    tz = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:TZ}}")

    # roll (-1deg, 1deg) to compensate for floor deviation, tied to feedback may never control directly
    az = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AZ}}MTR:RBV-RB0")

    # move camera up/down (-150mm, 1500mm)
    ty = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TY}}")

    # shift camera inboard/outboard (-25mm, 25mm)
    tx = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TX}}")

    # TODO replace with TDMSAxis when motions get commissioned
    # coupled to feedback to account for floor deviation
    # pitch (-17deg, 75deg),
    ax = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AX}}MTR:RBV-RB0")

    # rotation of camera platform
    camay = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:CAM_AY}}")

    def __init__(self, *, num, **kwargs):
        self._num = num
        super().__init__(**kwargs)


T1 = TDMSTower(name="T1", num=1)
T2 = TDMSTower(name="T2", num=2)
