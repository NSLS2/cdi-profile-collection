from ophyd import EpicsSignalRO

print("LOADING 10")

ring_current = EpicsSignalRO("SR:OPS-BI{DCCT:1}I:Real-I", name="ring_current")
