from cditools.eiger_async import EigerDetector
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import init_devices

pp = NSLS2PathProvider(RE.md)  # noqa: F821

with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}",
        name="eiger",
        path_provider=pp,
        md=RE.md,  # noqa: F821
    )
