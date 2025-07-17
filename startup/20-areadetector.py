from pathlib import Path

from cditools.eiger import EigerSingleTrigger
from cditools.eiger_async import EigerDetector
from ophyd_async.core import YMDPathProvider, UUIDFilenameProvider, init_devices


eiger = EigerSingleTrigger(prefix="XF:31ID-ES{Eig-Det:1}", name="eiger")

path_provider = YMDPathProvider(
    filename_provider=UUIDFilenameProvider(),
    base_directory_path=Path("/nsls2/data/tst/legacy/mock-proposals/2025-2/pass-56789/assets/eiger/")
)
with init_devices():
    eiger_async = EigerDetector(prefix="XF:31ID-ES{Eig-Det:1}", path_provider=path_provider)
