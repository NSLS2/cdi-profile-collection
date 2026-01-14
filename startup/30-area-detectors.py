from cditools.eiger_async import EigerDetector
from ophyd_async.core import init_devices, UUIDFilenameProvider, YMDPathProvider
from pathlib import PosixPath

filename_provider = UUIDFilenameProvider()
path_provider = YMDPathProvider(filename_provider, PosixPath("/tmp"))

with init_devices(mock=True):
	eiger = EigerDetector(prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=path_provider)
