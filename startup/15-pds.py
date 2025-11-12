from cditools.pds import DCMBase, Energy

dcm_base = DCMBase(prefix="XF:09IDA-OP:1{", name="dcm_base", labels=["motors", "dcm"])
energy = Energy(prefix="XF:09IDA-OP:1{", name="energy", labels=["dcm"])
