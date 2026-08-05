print(f'LOADING {__file__}...')
from bluesky.suspenders import (SuspendFloor, SuspendCeil, SuspendBoolHigh,
                                SuspendBoolLow)
import bluesky.plans as bp
import bluesky.plan_stubs as bps

def shuttergenerator(shutter, value):
    return (yield from bpp.rewindable_wrapper(bps.mv(shutter, value), False))

#ring current suspender, which is usually faster than FE shutter
#when the ring dumps
susp_rc = SuspendFloor(ring_current, 200, resume_thresh = 400, sleep=60,
        pre_plan=list(shuttergenerator(shut_b, 'Close')),
        post_plan=list(shuttergenerator(shut_b, 'Open')))

#suspenders for anomolous shutter events, which are rarely used
susp_shut_fe = SuspendBoolHigh(EpicsSignalRO(shut_fe.status.pvname, 
        name="FE shutter"), sleep=10)
susp_shut_a = SuspendBoolHigh(EpicsSignalRO(shut_a.status.pvname, 
        name="A shutter"), sleep=10)
susp_shut_b = SuspendBoolHigh(EpicsSignalRO(shut_b.status.pvname, 
        name="B shutter"), sleep=10)


# install
#RE.install_suspender(susp_rc)
#RE.install_suspender(susp_shut_fe)
#RE.install_suspender(susp_shut_a)
#RE.install_suspender(susp_shut_b)
