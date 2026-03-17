from pathlib import PosixPath

from cditools.eiger_async import EigerDetector
from cditools.merlin import CDIMerlinDetector
from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider, init_devices

md = RE.md  # noqa: F821
merlin = CDIMerlinDetector("XF:09ID1-ES{Det:Merlin1}", md, name="merlin")

filename_provider = UUIDFilenameProvider()
path_provider = YMDPathProvider(filename_provider, PosixPath("/tmp"))

with init_devices(mock=True):
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=path_provider
    )
