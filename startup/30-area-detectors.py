from pathlib import PosixPath

from cditools.eiger_async import EigerDetector
from ophyd_async.core import UUIDFilenameProvider, YMDPathProvider, init_devices

filename_provider = UUIDFilenameProvider()
path_provider = YMDPathProvider(
    filename_provider,
    PosixPath(
        f"/nsls2/data/cdi/proposals/{RE.md['cycle']}/{RE.md['data_session']}/assets/eiger2-1/%Y/%m/%d/"  # noqa: F821
    ),
)

with init_devices(mock=True):
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=path_provider
    )
