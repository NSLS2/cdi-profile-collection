from pathlib import PosixPath

import os
os.environ["OPHYD_ASYNC_PRESERVE_DETECTOR_STATE"] = "YES"

#from cditools.eiger_async import EigerDetector
from cditools.merlin_async import MerlinDetector
# from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider, 
from ophyd_async.core import init_devices
from nslsii.ophyd_async import NSLS2PathProvider

pp = NSLS2PathProvider(RE.md)

# filename_provider = UUIDFilenameProvider()
# path_provider = YMDPathProvider(filename_provider, PosixPath("/tmp"))

with init_devices(mock=False):
    merlin = MerlinDetector(prefix="XF:09ID1-ES{Det:Merlin1}", name="merlines-1", path_provider=pp)
#     eiger = EigerDetector(
#         prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=path_provider
#     )
