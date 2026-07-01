print(f"Loading {__file__!r} ...")

from cditools.attenuator import AttenuatorBank
from ophyd_async.core import init_devices


# attenuator format must be ("material", thickness_in_microns)
attenuators_config = [
    ("Al", 16.0),
    ("Al", 24.0),
    ("Al", 66.0),
    ("Al", 124.0)
]

with init_devices():
    bank = AttenuatorBank("XF:09ID1-ES{IOLOGIK1:E1212}", attenuators_config, energy)
