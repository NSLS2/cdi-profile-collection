motors = [
    dm1,
    vpm,
    hpm,
    dm2,
    dmm,
    dcm,
    dm3,
    kb,
    dm4,
    gon,
    bcu,
]
from pprint import pformat

for motor in motors:
    print(f"{motor.name}:\n{pformat(motor.read())}")
