from dataclasses import dataclass
from typing import Annotated as A
from typing import Sequence

from bluesky.protocols import Reading
from cditools.eiger_async import EigerDetector
from cditools.merlin_async import MerlinDetector
from event_model import DataKey
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import (
    DetectorDataLogic,
    ReadableDataProvider,
    SignalR,
    SignalRW,
    StandardReadable,
    StandardReadableFormat,
    init_devices,
)
from ophyd_async.epics import adcore, advimba
from ophyd_async.epics.adcore import (
    NDROIIO,
    ADAcquireLogic,
    ADBaseIO,
    ADState,
    ADWriterFactory,
    AreaDetector,
    NDPluginBaseIO,
    NDStatsIO,
    PluginSignalDataLogic,
)
from ophyd_async.epics.core import EpicsDevice, EpicsOptions, PvSuffix, stop_busy_record

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821


class CustomVimbaDriverIO(advimba.VimbaDriverIO):
    """FIXME: turn off put_completion for `acquire` PV"""

    acquire: A[SignalRW[bool], PvSuffix.rbv("Acquire"), EpicsOptions(wait=False)]


class NDCentroid(StandardReadable, EpicsDevice):
    X: A[
        SignalR[float], PvSuffix("CentroidX_RBV"), StandardReadableFormat.HINTED_SIGNAL
    ]
    Y: A[
        SignalR[float], PvSuffix("CentroidY_RBV"), StandardReadableFormat.HINTED_SIGNAL
    ]
    SigmaX: A[SignalR[float], PvSuffix("SigmaX_RBV"), StandardReadableFormat.CHILD]
    SigmaY: A[SignalR[float], PvSuffix("SigmaY_RBV"), StandardReadableFormat.CHILD]

    SkewX: A[SignalR[float], PvSuffix("SkewX_RBV"), StandardReadableFormat.CHILD]
    SkewY: A[SignalR[float], PvSuffix("SkewY_RBV"), StandardReadableFormat.CHILD]

    KurtosisX: A[
        SignalR[float], PvSuffix("KurtosisX_RBV"), StandardReadableFormat.CHILD
    ]
    KurtosisY: A[
        SignalR[float], PvSuffix("KurtosisY_RBV"), StandardReadableFormat.CHILD
    ]

    SigmaXY: A[SignalR[float], PvSuffix("SigmaXY_RBV"), StandardReadableFormat.CHILD]
    Eccentricity: A[
        SignalR[float], PvSuffix("Eccentricity_RBV"), StandardReadableFormat.CHILD
    ]
    Orientation: A[
        SignalR[float], PvSuffix("Orientation_RBV"), StandardReadableFormat.CHILD
    ]


class EnrichedStats(NDStatsIO, StandardReadable):
    total: A[
        SignalR[float],
        PvSuffix("Total_RBV"),
        StandardReadableFormat.HINTED_UNCACHED_SIGNAL,
    ]
    centroid: A[NDCentroid, PvSuffix(""), StandardReadableFormat.CHILD]


@dataclass
class StandardReadableDataProvider(ReadableDataProvider):
    """Provide the readings of a StandardReadable device."""

    device: StandardReadable

    async def make_datakeys(self) -> dict[str, DataKey]:
        return await self.device.describe()

    async def make_readings(self) -> dict[str, Reading]:
        return await self.device.read()


@dataclass
class PluginReadableDataLogic(DetectorDataLogic):
    """Add a plugin's readables to each event, like PluginSignalDataLogic.

    Plugin PVs only hold values for the latest image, so ophyd-async refuses to
    prepare a detector using this logic for more than one image per event.
    """

    driver: ADBaseIO
    plugin: StandardReadable

    async def prepare_single(self, datakey_name: str) -> StandardReadableDataProvider:
        # Acquisition must wait for the plugins so reads see the latest image
        await self.driver.wait_for_plugins.set(True)
        return StandardReadableDataProvider(self.plugin)

    def get_hinted_fields(self, datakey_name: str) -> Sequence[str]:
        return self.plugin.hints.get("fields", [])


class VimbaAcquireLogic(ADAcquireLogic):
    driver: CustomVimbaDriverIO

    async def ensure_ready(self):
        detector_state = await self.driver.detector_state.get_value()
        self._cached_acquire_state = detector_state != ADState.IDLE
        self._cached_trigger_mode = await self.driver.trigger_mode.get_value()
        self._cached_image_mode = await self.driver.image_mode.get_value()

        await stop_busy_record(self.driver.acquire)

    async def ensure_stopped(self):
        await stop_busy_record(self.driver.acquire)

        if self._cached_trigger_mode is not None:
            await self.driver.trigger_mode.set(self._cached_trigger_mode)
        if self._cached_image_mode is not None:
            await self.driver.image_mode.set(self._cached_image_mode)
        self._cached_trigger_mode = None
        self._cached_image_mode = None

        if self._cached_acquire_state is not None:
            await self.driver.acquire.set(self._cached_acquire_state)
        self._cached_acquire_state = None


# TODO - move to ophyd-async
class TmpAdvimba(AreaDetector[CustomVimbaDriverIO]):
    """ADVimba detector with Stats1 and ROI1 plugins.

    :param prefix: EPICS PV prefix for the detector
    :param writer_factories: Factories for file writer plugins and their data logics
    :param driver_suffix: Suffix for the driver PV, defaults to "cam1:"
    :param override_deadtime:
        If provided, this value is used for deadtime instead of looking up
        based on camera model.
    :param plugins: Additional areaDetector plugins to include
    :param config_sigs: Additional signals to include in configuration
    :param name: Name for the detector device
    """

    stats1: EnrichedStats
    roi1: NDROIIO

    def __init__(
        self,
        prefix: str,
        *writer_factories: ADWriterFactory,
        driver_suffix="cam1:",
        override_deadtime: float | None = None,
        plugins: dict[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ):
        plugins = plugins or {}

        driver = CustomVimbaDriverIO(prefix + driver_suffix)
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=VimbaAcquireLogic(driver),
            trigger_logic=advimba.VimbaTriggerLogic(driver, override_deadtime),
            plugins={
                "stats1": EnrichedStats(f"{prefix}Stats1:"),
                "roi1": NDROIIO(f"{prefix}ROI1:"),
                **plugins,
            },
            config_sigs=config_sigs,
            name=name,
        )

    # TODO need to add read_configuration and describe_configruation to read ROI plugins




with init_devices(mock = RUNNING_IN_NSLS2_CI):
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger2-1", path_provider=pp
    )
    eiger_stats1=NDStatsIO("XF:09ID1-ES{Det:Eig1}Stats1:")
    merlin = MerlinDetector(
        "XF:09ID1-ES{Det:Merlin1}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="merlines-1",
    )
    cam1 = TmpAdvimba(
        "XF:09IDA-BI{DM:1-Cam:1}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-1",
    )
    cam2 = TmpAdvimba(
        "XF:09IDA-BI{WBStop-Cam:2}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-2",
    )
    cam3 = TmpAdvimba(
        "XF:09IDA-BI{VPM-Cam:3}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-3",
    )
    cam4 = TmpAdvimba(
        "XF:09IDA-BI{HPM-Cam:4}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-4",
    )
    cam5 = TmpAdvimba(
        "XF:09IDA-BI{DM:2-Cam:5}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-5",
    )
    cam6 = TmpAdvimba(
        "XF:09IDB-BI{DM:3-Cam:6}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-6",
    )
    cam7 = TmpAdvimba(
        "XF:09IDC-BI{FS:KBv-Cam:7}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-7",
    )

    cam8 = TmpAdvimba(
        "XF:09IDC-BI{FS:KBh-Cam:8}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-8",
    )
    cam9 = TmpAdvimba(
        "XF:09IDC-BI{BCU-Cam:9}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-9",
    )
    cam10 = TmpAdvimba(
        "XF:09IDC-BI{SMPL-Cam:10}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-10",
    )
    # cam15 = TmpAdvimba(
    #     "XF:09IDC-BI{Cam:15}",
    #     adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
    #     name="cam-15",
    #     )

eiger.add_detector_logics(PluginSignalDataLogic(eiger.driver,eiger_stats1.total))
cam1.add_detector_logics(PluginReadableDataLogic(cam1.driver, cam1.stats1))
cam2.add_detector_logics(PluginReadableDataLogic(cam2.driver, cam2.stats1))
cam3.add_detector_logics(PluginReadableDataLogic(cam3.driver, cam3.stats1))
cam4.add_detector_logics(PluginReadableDataLogic(cam4.driver, cam4.stats1))
cam5.add_detector_logics(PluginReadableDataLogic(cam5.driver, cam5.stats1))
# No Stats1 readings on cam6: they only support one image per point
cam7.add_detector_logics(PluginReadableDataLogic(cam7.driver, cam7.stats1))
cam8.add_detector_logics(PluginReadableDataLogic(cam8.driver, cam8.stats1))
cam9.add_detector_logics(PluginReadableDataLogic(cam9.driver, cam9.stats1))
cam10.add_detector_logics(PluginReadableDataLogic(cam10.driver, cam10.stats1))

