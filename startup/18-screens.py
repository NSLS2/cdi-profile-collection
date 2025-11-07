from __future__ import annotations

from typing import Optional

from ophyd import (
    CamBase,
)
from ophyd import Component as Cpt
from ophyd import (
    EpicsMotor,
    EpicsSignal,
    ImagePlugin,
    ProsilicaDetector,
    ProsilicaDetectorCam,
    ROIPlugin,
)
from ophyd.areadetector.plugins import (
    PluginBase,
    ROIStatPlugin_V35,
    StatsPlugin,
    TransformPlugin,
)


class ProsilicaCamBase(ProsilicaDetector):
    wait_for_plugins = Cpt(EpicsSignal, "WaitForPlugins", string=True, kind="hinted")
    cam = Cpt(ProsilicaDetectorCam, "cam1:")
    image = Cpt(ImagePlugin, "image1:")
    stats1 = Cpt(StatsPlugin, "Stats1:")
    stats2 = Cpt(StatsPlugin, "Stats2:")
    stats3 = Cpt(StatsPlugin, "Stats3:")
    stats4 = Cpt(StatsPlugin, "Stats4:")
    stats5 = Cpt(StatsPlugin, "Stats5:")
    trans1 = Cpt(TransformPlugin, "Trans1:")
    roi1 = Cpt(ROIPlugin, "ROI1:")
    roi2 = Cpt(ROIPlugin, "ROI2:")
    roi3 = Cpt(ROIPlugin, "ROI3:")
    roi4 = Cpt(ROIPlugin, "ROI4:")
    roistat1 = Cpt(ROIStatPlugin_V35, "ROIStat1:")
    _default_plugin_graph: Optional[dict[PluginBase, CamBase | PluginBase]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.roistat1.kind = "hinted"
        self._use_default_plugin_graph: bool = True

    @property
    def default_plugin_graph(
        self,
    ) -> Optional[dict[PluginBase, CamBase | PluginBase]]:
        return self._default_plugin_graph

    def _stage_plugin_graph(self, plugin_graph: dict[PluginBase, CamBase | PluginBase]):
        for target, source in plugin_graph.items():
            self.stage_sigs[target.nd_array_port] = source.port_name.get()
            self.stage_sigs[target.enable] = True

    def stage(self):
        if self._use_default_plugin_graph and self.default_plugin_graph is not None:
            self._stage_plugin_graph(self.default_plugin_graph)

        return super().stage()


class StandardProsilicaCam(ProsilicaCamBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_plugin_graph = {
            self.image: self.cam,
            self.stats1: self.cam,
            self.stats2: self.cam,
            self.stats3: self.cam,
            self.stats4: self.cam,
            self.stats5: self.cam,
            self.trans1: self.cam,
            self.roi1: self.cam,
            self.roi2: self.cam,
            self.roi3: self.cam,
            self.roi4: self.cam,
            self.roistat1: self.cam,
        }

    def stage(self):
        return super().stage()


class StandardScreen(EpicsMotor):
    def __init__(self, *args, in_position=0.0, out_position=25.0, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_position = in_position
        self._out_position = out_position

    def in_position(self, value):
        self._in_position = value

    def out_position(self, value):
        self._out_position = value

    def insert(self):
        """Move screen into the beam"""
        return self.set(self._in_position)

    def remove(self):
        """Move screen out of the beam"""
        return self.set(self._out_position)


cam_A1 = StandardProsilicaCam("XF:09IDA-BI{DM:1-Cam:1}", name="cam_A1")
cam_A2 = StandardProsilicaCam("XF:09IDA-BI{WBStop-Cam:2}", name="cam_A2")
cam_A3 = StandardProsilicaCam("XF:09IDA-BI{VPM-Cam:3}", name="cam_A3")
cam_A4 = StandardProsilicaCam("XF:09IDA-BI{HPM-Cam:4}", name="cam_A4")
cam_A5 = StandardProsilicaCam("XF:09IDA-BI{DM:2-Cam:5}", name="cam_A5")

vpm_fs = StandardScreen("XF:09IDA-OP:1{FS:VPM-Ax:Y}Mtr", name="screen_vpm")
hpm_fs = StandardScreen("XF:09IDA-OP:1{FS:HPM-Ax:Y}Mtr", name="screen_hpm")
dm_fs = StandardScreen("XF:09IDA-OP:1{FS:DM2-Ax:Y}Mtr", name="screen_dm")
