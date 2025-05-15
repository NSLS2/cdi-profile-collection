motors = [
    slt_wb1,
    fltr_dm1,
    fsvpm,
    fshpm,
    fsdm2,
    mono_dmm,
    mono_hdcm,
    slt_vpm,
    slt_hpm,
    mir_vpm,
    imdm2,
    mir_hpm,
    slt_dm3,
    bpm_dm3,
    fsdm3,
    mir_kbv,
    mir_kbh,
    bpm_dm4,
    wnd_exit,
    gon1,
    slt_bcuu,
    slt_bcud,
    qstar1,
]


for motor in motors:
    print(f"{motor.name}:\n{motor.read()}")
