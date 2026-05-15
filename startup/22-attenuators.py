print(f"Loading {__file__!r} ...")

from cditools.attenuator import AttenuatorBank
from ophyd_async.core import init_devices

with init_devices():
    bank = AttenuatorBank(energy)
