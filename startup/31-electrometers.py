import time
from ophyd import (Component as Cpt, EpicsSignal, EpicsSignalRO,
        Signal)
from ophyd.device import Device

print("LOADING 31")

###############################################################################
# objects                                                                     #
###############################################################################

class TetrAMM(Device):
    channel1 = Cpt(EpicsSignalRO, 'Current1:MeanValue_RBV', kind="normal")
    channel2 = Cpt(EpicsSignalRO, 'Current2:MeanValue_RBV', kind="normal")
    channel3 = Cpt(EpicsSignalRO, 'Current3:MeanValue_RBV', kind="normal")
    channel4 = Cpt(EpicsSignalRO, 'Current4:MeanValue_RBV', kind="normal")
    posX = Cpt(EpicsSignalRO, 'PosX:MeanValue_RBV', kind="normal")
    posY = Cpt(EpicsSignalRO, 'PosY:MeanValue_RBV', kind="normal")
    sumI = Cpt(EpicsSignalRO, 'SumAll:MeanValue_RBV', kind="normal")
    int_time = Cpt(EpicsSignalRO, 'AveragingTime_RBV', kind="normal")
    amp_range = Cpt(EpicsSignalRO, 'XF:09IDC-BI{BPM:1}Range_RBV', kind="normal")


class I404(Device):
#This device's IOC doesn't provide a total current PV.  For our 4-diode
#quadrant BPM, that sum is not especially meaningful, so we can calculate
#it on-the-fly from the channels if we need it.
        channel1 = Cpt(EpicsSignalRO, 'I:R1-I', kind="normal")
        channel2 = Cpt(EpicsSignalRO, 'I:R2-I', kind="normal")
        channel3 = Cpt(EpicsSignalRO, 'I:R3-I', kind="normal")
        channel4 = Cpt(EpicsSignalRO, 'I:R4-I', kind="normal")
        posX = Cpt(EpicsSignalRO, 'Pos:X-I', kind="normal")
        posY = Cpt(EpicsSignalRO, 'Pos:Y-I', kind="normal")
        int_time = Cpt(EpicsSignalRO, 'Time:Intg-I', kind="normal")
        amp_range = Cpt(EpicsSignalRO, 'Val:Rng-I', kind="normal")

class I400(Device):
#CDI uses this as a single-channel read-out for the foil intensity monitor
        channel1 = Cpt(EpicsSignalRO, ':IC1_MON', kind="normal")
        channel2 = Cpt(EpicsSignalRO, ':IC2_MON', kind="normal")
        channel3 = Cpt(EpicsSignalRO, ':IC3_MON', kind="normal")
        channel4 = Cpt(EpicsSignalRO, ':IC4_MON', kind="normal")
        int_time = Cpt(EpicsSignalRO, ':ITIME_MON', kind="normal")
        amp_range = Cpt(EpicsSignalRO, ':RANGE_MON', kind="normal")

###############################################################################
# devices                                                                     #
###############################################################################

i400 = I400('XF:09IDA-BI{i400:1}', name = "fmon")

i404 = I404('XF:09IDB-BI{i404:1}', name = "qbpm")

#the name of tetra changed 18 June 2026 following the decision to use it
#for the diamond beam position monitor rather than the ion chambers.

tetra = TetrAMM('XF:09IDC-BI{BPM:1}', name = "dbpm")
