from cditools.screens import StandardProsilicaCam, StandardScreen, set_roiN_kinds

cam_A1 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{DM:1-Cam:1}", name="cam_A1"))
cam_A2 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDA-BI{WBStop-Cam:2}", name="cam_A2")
)
cam_A3 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{VPM-Cam:3}", name="cam_A3"))
cam_A4 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{HPM-Cam:4}", name="cam_A4"))
cam_A5 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{DM:2-Cam:5}", name="cam_A5"))
cam_A6 = set_roiN_kinds(StandardProsilicaCam("XF:09IDB-BI{DM:3-Cam:6}", name="cam_A6"))
cam_A7 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDC-BI{FS:KBv-Cam:7}", name="cam_A7")
)
cam_A8 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDC-BI{FS:KBh-Cam:8}", name="cam_A8")
)
cam_A9 = set_roiN_kinds(StandardProsilicaCam("XF:09IDC-BI{SMPL-Cam:9}", name="cam_A9"))

vpm_fs = StandardScreen("XF:09IDA-OP:1{FS:VPM-Ax:Y}Mtr", name="screen_vpm")
hpm_fs = StandardScreen("XF:09IDA-OP:1{FS:HPM-Ax:Y}Mtr", name="screen_hpm")
dm_fs = StandardScreen("XF:09IDA-OP:1{FS:DM2-Ax:Y}Mtr", name="screen_dm")

kbvh_fs = StandardScreen("XF:09IDC-OP:1{Mir:KBh-Ax:FS}Mtr", name="screen_kbh")
kbvv_fs = StandardScreen("XF:09IDC-OP:1{Mir:KBv-Ax:FS}Mtr", name="screen_kbv")
