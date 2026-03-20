from pathlib import PosixPath, PurePath
import bluesky.plan_stubs as bps
from ophyd_async.core._detector import TriggerInfo
from ophyd_async.core import StaticFilenameProvider, StaticPathProvider
import uuid
from bluesky.utils import FailedStatus
import bluesky.preprocessors as bpp

from cditools.eiger_async import EigerDetector
from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider, init_devices

filename_provider = UUIDFilenameProvider()
path_provider = YMDPathProvider(filename_provider, PosixPath("/tmp"))
sfp = StaticFilenameProvider('eiger2-stress4')
img_path = '/nsls2/data3/cdi/proposals/commissioning/pass-319502/assets/eiger2-1/2026/02/11/'
write_path = PurePath(img_path)
pp = StaticPathProvider(sfp, write_path)

pv_prefix = 'XF:09ID1-ES{Det:Eig1}'
 
with init_devices():
    eiger = EigerDetector(pv_prefix, pp)

def stress(det, num_events=5, img_per_event=250, batch=None):

    
    @bpp.run_decorator(md={'stress_batch': batch,'num_events': num_events, 'img_per_event':img_per_event})
    def inner():
        yield from bps.stage(det)
    
        for n in range(num_events):
            yield from bps.mv(det.fileio.array_counter, 0)        
            yield from bps.prepare(det, TriggerInfo(exposures_per_event=img_per_event, number_of_events=1))
    
            yield from bps.trigger_and_read([det])
        yield from bps.unstage(det)

    yield from inner()
        


def double_stress(num=100, **kwargs):
    batch = str(uuid.uuid4())
    for m in range(num):
        try:    
            yield from stress(batch=batch, **kwargs)
        except FailedStatus:
            pass
        except GeneratorExit:
            raise