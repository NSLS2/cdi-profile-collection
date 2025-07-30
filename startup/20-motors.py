from cditools.motors import (
    BCU,
    DCM,
    DM1,
    DM2,
    DM3,
    DM4,
    DMM,
    GON,
    HPM,
    KB,
    VPM,
)

dm1 = DM1(prefix="XF:09IDA-OP:1{", name="dm1", labels=["motors"])
vpm = VPM(prefix="XF:09IDA-OP:1{", name="vpm", labels=["motors"])
hpm = HPM(prefix="XF:09IDA-OP:1{", name="hpm", labels=["motors"])
dm2 = DM2(prefix="XF:09IDA-OP:1{", name="dm2", labels=["motors"])
dmm = DMM(prefix="XF:09IDA-OP:1{", name="dmm", labels=["motors"])
dcm = DCM(prefix="XF:09IDA-OP:1{", name="dcm", labels=["motors"])
dm3 = DM3(prefix="XF:09IDB-OP:1{", name="dm3", labels=["motors"])
kb = KB(prefix="XF:09IDC-OP:1{", name="kb", labels=["motors"])
dm4 = DM4(prefix="XF:09IDC-OP:1{", name="dm4", labels=["motors"])
gon = GON(prefix="XF:09IDC-OP:1{", name="gon", labels=["motors"])
bcu = BCU(prefix="XF:09IDC-OP:1{", name="bcu", labels=["motors"])
