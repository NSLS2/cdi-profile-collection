from cditools.eiger_async import EigerDetector
from ophyd_async.core import init_devices
from ophyd_async.providers import NSLS2PathProvider

pp = NSLS2PathProvider(RE.md)  # noqa: F821

with init_devices(mock=True):
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}",
        name="eiger",
        path_provider=pp,
        md=RE.md,  # noqa: F821
    )
