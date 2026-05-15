print(f"Loading {__file__!r} ...")

from cditools.attenuator import AttenuatorBank
from ophyd_async.core import init_devices


prefix = "XF:09ID1-ES{IOLOGIK1:E1212}"

with init_devices():
    bank = AttenuatorBank(prefix, energy)
