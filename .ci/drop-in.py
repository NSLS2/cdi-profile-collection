from pprint import pformat

# Motors are loaded into the IPython namespace by startup scripts
# ruff: noqa: F821
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

for motor in motors:
    motor.wait_for_connection()
    print(f"{motor.name}:\n{pformat(motor.read())}")
