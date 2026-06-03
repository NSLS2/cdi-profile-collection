from cditools.screens import StandardProsilicaCam, StandardScreen, set_roiN_kinds

print("LOADING 18")

try:
    from cditools.screens import setup_centroids
except ImportError:
    from ophyd.areadetector.plugins import StatsPlugin

    def setup_centroids(stats: StatsPlugin, hinted: str | tuple[str] = ("x",)):
        """
        Docstring for setup_centroids

        stats : StatsPlugin
            The StatsPlugin instance for which to set up centroids.
        hinted : str or tuple of str, optional
            The attributes of the StatsPlugin to set as 'hinted'. Default is ('x',).
        """
        stats.kind = "normal"
        stats.centroid.kind = "normal"
        if isinstance(hinted, str):
            hinted = (hinted,)
        for attr in hinted:
            getattr(stats.centroid, attr).kind = "hinted"


class MaskedCam(StandardProsilicaCam):
    image = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_plugin_graph = {
            self.stats1: self.roi1,
            self.stats2: self.roi2,
            self.stats3: self.roi3,
            self.stats4: self.roi4,
            self.stats5: self.cam,
            self.trans1: self.cam,
            self.roi1: self.cam,
            self.roi2: self.cam,
            self.roi3: self.cam,
            self.roi4: self.cam,
            self.roistat1: self.cam,
        }


cam_A1 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{DM:1-Cam:1}", name="cam_A1"))
cam_A2 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDA-BI{WBStop-Cam:2}", name="cam_A2")
)
cam_A3 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{VPM-Cam:3}", name="cam_A3"))
cam_A4 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{HPM-Cam:4}", name="cam_A4"))
cam_A5 = set_roiN_kinds(StandardProsilicaCam("XF:09IDA-BI{DM:2-Cam:5}", name="cam_A5"))
cam_B6 = set_roiN_kinds(StandardProsilicaCam("XF:09IDB-BI{DM:3-Cam:6}", name="cam_B6"))
setup_centroids(cam_B6.stats1)
cam_C7 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDC-BI{FS:KBv-Cam:7}", name="cam_C7")
)
cam_C8 = set_roiN_kinds(
    StandardProsilicaCam("XF:09IDC-BI{FS:KBh-Cam:8}", name="cam_C8")
)
cam_C9 = set_roiN_kinds(MaskedCam("XF:09IDC-BI{BCU-Cam:9}", name="cam_C9"))
cam_C10 = set_roiN_kinds(MaskedCam("XF:09IDC-BI{SMPL-Cam:10}", name="cam_C10"))
cam_C15 = set_roiN_kinds(MaskedCam("XF:09IDC-BI{Cam:15}", name="cam_C15"))

for _c in [cam_C9, cam_C10, cam_C15]:
    _c.stats5.total.kind = "hinted"
    _c.stats5.kind = "normal"

vpm_fs = StandardScreen("XF:09IDA-OP:1{FS:VPM-Ax:Y}Mtr", name="screen_vpm")
hpm_fs = StandardScreen("XF:09IDA-OP:1{FS:HPM-Ax:Y}Mtr", name="screen_hpm")
dm_fs = StandardScreen("XF:09IDA-OP:1{FS:DM2-Ax:Y}Mtr", name="screen_dm")

kbvh_fs = StandardScreen("XF:09IDC-OP:1{Mir:KBh-Ax:FS}Mtr", name="screen_kbh")
kbvv_fs = StandardScreen("XF:09IDC-OP:1{Mir:KBv-Ax:FS}Mtr", name="screen_kbv")
