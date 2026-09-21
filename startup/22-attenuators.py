print(f"Loading {__file__!r} ...")

from cditools.attenuator import AttenuatorBank
from ophyd_async.core import init_devices


# attenuator format must be ("material", thickness_in_microns)
attenuators_config = [
    ("Si", 525.0),
    ("Si", 525.0),
    ("Si", 0.),
    ("Si", 0.),
    ("Si", 50.),
    ("Si", 100.),
    ("Si", 200.),
    ("Al2O3", 100.)
]

with init_devices():
    bank = AttenuatorBank("XF:09ID1-ES{IOLOGIK1:E1212}", attenuators_config, energy)
