from ophyd import (PVPositioner, Component as Cpt, EpicsSignal, EpicsSignalRO,
        Signal, EpicsMotor)
from ophyd.device import Device

print("LOADING 10")

#device definitions
class IVUGap(PVPositioner):
   setpoint = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr-SP")
   readback = Cpt(EpicsSignalRO,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.RBV")
   actuate = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr-Go")
   done = Cpt(EpicsSignalRO, "SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.DMOV")
   stp = Cpt(EpicsSignal,"SR:C09-ID:G1{IVU18:1-CS2:Gap}-Mtr.STOP")

class InsertionDevice(Device):
    gap = Cpt(IVUGap, name='')

    def set(self, *args, **kwargs):
        return self.gap.set(*args, **kwargs)

    def stop(self, *, success=False):
        return self.gap.stp(success=success)

#device assignments
ivu = InsertionDevice('SR:C09-ID:G1{IVU18:1', name='ivu')
ring_current = EpicsSignalRO("SR:OPS-BI{DCCT:1}I:Real-I", name="ring_current")
