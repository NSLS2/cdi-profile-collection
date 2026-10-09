print(f"Loading {__file__!r} ...")

from ophyd.device import Component as Cpt
from ophyd.device import Device
from ophyd.device import FormattedComponent as FCpt
from ophyd.pv_positioner import PVPositioner
from ophyd.signal import EpicsSignal, EpicsSignalRO, DerivedSignal


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
    tx = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TX}}")
    ty = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:TY}}")
    tz = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:TZ}}")

    camay = FCpt(TDMSAxis, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:CAM_AY}}")

    # TODO replace with TDMSAxis when motions get comissioned
    ax = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AX}}MTR:RBV-RB0")
    ay = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:A{self._num}-Ax:AY}}MTR:RBV-RB0")
    az = FCpt(EpicsSignalRO, "XF:09IDC-ES:1{{TDMS:T{self._num}-Ax:AZ}}MTR:RBV-RB0")

    def __init__(self, *, num, **kwargs):
        self._num = num
        super().__init__(**kwargs)


T1 = TDMSTower(name="T1", num=1)
T2 = TDMSTower(name="T2", num=2)


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

tdms_arm1_ax = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T1-Ax:AX}', name='arm1_ax')
tdms_arm1_ax.user_val.offset = 0.
tdms_arm2_ax = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T1-Ax:AX}', name='arm2_ax')
tdms_arm2_ax.user_val.offset = -25.

tdms_arm1_tz = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A1-Ax:TZ}', name='arm1_tz')
tdms_arm1_tz.user_val.offset = -0. 
tdms_arm2_tz = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:A2-Ax:TZ}', name='arm2_tz')
tdms_arm2_tz.user_val.offset = 502.125 

tdms_arm1_ty = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T1-Ax:TY}', name='arm1_ty')
tdms_arm1_ty.user_val.offset = -0. 
tdms_arm2_ty = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T2-Ax:TY}', name='arm2_ty')
tdms_arm2_ty.user_val.offset = -165. 

tdms_arm1_tx = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T1-Ax:TX}', name='arm1_tx')
tdms_arm1_tx.user_val.offset = -0. 
tdms_arm2_tx = OffsetTDMSDevice('XF:09IDC-ES:1{TDMS:T2-Ax:TX}', name='arm2_tx')
tdms_arm2_tx.user_val.offset = -13.75 
