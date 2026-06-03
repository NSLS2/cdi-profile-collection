from cditools.eiger_async import EigerDetector
from cditools.merlin_async import MerlinDetector
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import init_devices

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821

with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger2-1", path_provider=pp
    )
    # merlin = MerlinDetector(
    #     prefix="XF:09ID1-ES{Det:Merlin1}", name="merlin", path_provider=pp
    # )
