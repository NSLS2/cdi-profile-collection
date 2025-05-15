from ophyd import EpicsSignal, EpicsSignalRO

ring_current = EpicsSignalRO("SR:OPS-BI{DCCT:1}I:Real-I", name="ring_current")
