from typing import Annotated as A
from typing import Sequence

from cditools.eiger_async import EigerDetector
from cditools.merlin_async import MerlinDetector
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import SignalR, SignalRW, init_devices
from ophyd_async.epics import adcore, advimba
from ophyd_async.epics.adcore import ADAcquireLogic, ADState, AreaDetector
from ophyd_async.epics.core import EpicsOptions, PvSuffix, stop_busy_record

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821


class CustomVimbaDriverIO(advimba.VimbaDriverIO):
    """FIXME: turn off put_completion for `acquire` PV"""

    acquire: A[SignalRW[bool], PvSuffix.rbv("Acquire"), EpicsOptions(wait=False)]


class VimbaAcquireLogic(ADAcquireLogic):
    async def ensure_ready(self):
        detector_state = await self.driver.detector_state.get_value()
        self._cached_acquire_state = detector_state != ADState.IDLE
        self._cached_trigger_mode = await self.driver.trigger_mode.get_value()
        self._cached_image_mode = await self.driver.image_mode.get_value()

        await stop_busy_record(self.driver.acquire)

    async def ensure_stopped(self):
        print()
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
    def __init__(
        self,
        prefix: str,
        *writer_factories: advimba.ADWriterFactory,
        driver_suffix="cam1:",
        override_deadtime: float | None = None,
        plugins: dict[str, advimba.NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ):
        driver = CustomVimbaDriverIO(prefix + driver_suffix)
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=VimbaAcquireLogic(driver),
            trigger_logic=advimba.VimbaTriggerLogic(driver, override_deadtime),
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )


with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger2-1", path_provider=pp
    )
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
