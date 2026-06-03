import asyncio
import functools
import os
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from pathlib import Path
from typing import Annotated as A
from urllib.parse import urlunparse

import numpy as np
from cditools.eiger_async import Eiger2DriverIO as _Eiger2DriverIO
from cditools.eiger_async import (
    EigerDriverIO,
    EigerHDF5Format,
    EigerTriggerMode,
    logger,
)
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import (
    AsyncStatus,
    DetectorArmLogic,
    DetectorDataLogic,
    DetectorTriggerLogic,
    PathInfo,
    PathProvider,
    SignalDatatypeT,
    StreamResourceDataProvider,
    StreamResourceInfo,
    StrictEnum,
    TriggerInfo,
    init_devices,
    observe_value,
    set_and_wait_for_other_value,
)
from ophyd_async.core._data_providers import (
    StreamableDataProvider,
)
from ophyd_async.core._signal import (
    SignalR,
    SignalRW,
)
from ophyd_async.core._status import WatchableAsyncStatus
from ophyd_async.core._utils import (
    DEFAULT_TIMEOUT,
    WatcherUpdate,
    error_if_none,
)
from ophyd_async.epics.adcore import (
    ADImageMode,
    AreaDetector,
    NDPluginBaseIO,
    trigger_info_from_num_images,
)
from ophyd_async.epics.core import stop_busy_record
from ophyd_async.epics.signal import PvSuffix

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821


class EigerStreamVersion(StrictEnum):
    """Stream versions for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#stream-interface
    """

    STREAM1 = "Stream"
    STREAM2 = "Stream2"


class Eiger2DriverIO(_Eiger2DriverIO):
    stream_version: A[SignalRW[EigerStreamVersion], PvSuffix.rbv("StreamVersion")]
    threshold: A[SignalRW[float], PvSuffix.rbv("ThresholdEnergy")]
    threshold2: A[SignalRW[float], PvSuffix.rbv("Threshold2Energy")]
    stream_hdr_appendix: None
    stream_img_appendix: None


class EigerController(DetectorTriggerLogic):
    """Controller for Eiger detector, handling trigger modes and acquisition setup."""

    def __init__(
        self,
        driver: EigerDriverIO,
    ) -> None:
        self.driver = driver

    def get_deadtime(self, exposure: float | None) -> float:
        """Get detector deadtime for the given exposure."""
        default_deadtime = 0.000001
        if exposure is not None:
            logger.warning(
                "Ignoring exposure to calculate deadtime: %s, defaulting to %s",
                exposure,
                default_deadtime,
            )
        return default_deadtime

    async def prepare_internal(self, num: int, livetime: float, deadtime: float):
        """Prepare the detector for acquisition."""

        if livetime > 0:
            await self.driver.acquire_time.set(livetime)

        await self.driver.trigger_mode.set(EigerTriggerMode.INTERNAL_SERIES)

        if num == 0:
            image_mode = ADImageMode.CONTINUOUS
        else:
            image_mode = ADImageMode.MULTIPLE

        # await self.driver.num_triggers.set(num)

        await asyncio.gather(
            self.driver.image_mode.set(image_mode),
        )

    async def prepare_edge(self, num: int, livetime: float):
        """Prepare the detector to take external edge triggered exposures.

        :param num: the number of exposures to take
        :param livetime: how long the exposure should be, 0 means what is currently set
        """

        await self.driver.acquire_time.set(livetime)
        await self.driver.num_triggers.set(num)
        if num == 0:
            image_mode = ADImageMode.CONTINUOUS
        else:
            image_mode = ADImageMode.MULTIPLE

        await self.driver.trigger_mode.set(EigerTriggerMode.EXTERNAL_SERIES)
        await asyncio.gather(
            self.driver.image_mode.set(image_mode),
        )

    async def default_trigger_info(self):
        return await trigger_info_from_num_images(self.driver)


class EigerDataLogic(DetectorDataLogic):
    """Eiger-specific file writer using the built-in FileWriter interface."""

    default_suffix: str = "cam1:"
    # Forced minimum number of images per file to force a single HDF5 file
    _min_num_images_per_file: int = 1_000_000_000

    def __init__(
        self,
        fileio: EigerDriverIO,
        path_provider: PathProvider,
        # dataset_describer: ADBaseDatasetDescriber,
        # plugins: dict[str, NDPluginBaseIO] | None = None,
    ):
        self.fileio = fileio
        self._path_provider = path_provider
        # self._dataset_describer = dataset_describer
        # self._plugins = plugins or {}

        self._file_info: PathInfo | None = None
        self._datasets: list[StreamResourceDataProvider] = []
        self._master_file_path_cache: list[Path] = []

    async def prepare_unbounded(self, datakey_name: str) -> StreamableDataProvider:
        """Provider can work for an unbounded number of collections."""
        # Get file path info from path provider
        # TODO: should probably just pass datakey_name
        self._file_info = self._path_provider("eiger2-1")
        self._master_file_path_cache.clear()

        # Set the name pattern with $id replacement similar to original
        name_pattern = f"{self._file_info.filename}_$id"

        # Configure the Eiger FileWriter
        await asyncio.gather(
            self.fileio.file_path.set(self._file_info.directory_path.as_posix()),
            self.fileio.create_directory.set(self._file_info.create_dir_depth),
            self.fileio.fw_name_pattern.set(name_pattern),
            self.fileio.fw_enable.set(True),
            self.fileio.save_files.set(True),
            # self.fileio.data_source.set(EigerDataSource.FILE_WRITER),
            self.fileio.num_capture.set(0),
            # Use array_counter to track the total number of images written
            self.fileio.array_counter.set(0),
            self.fileio.manual_trigger.set(True),
            # TODO sort out how to get this from the plan
            self.fileio.num_triggers.set(5000),
        )

        await set_and_wait_for_other_value(
            set_signal=self.fileio.acquire,
            set_value=True,
            match_signal=self.fileio.armed,
            match_value=True,
            wait_for_set_completion=False,
            timeout=DEFAULT_TIMEOUT,
        )

        if not await self.fileio.file_path_exists.get_value():
            msg = f"File path {self._file_info.directory_path} does not exist"
            raise FileNotFoundError(msg)

        if isinstance(self.fileio, Eiger2DriverIO):
            await self.fileio.fw_hdf5_format.set(EigerHDF5Format.LEGACY)

        # Force the number of images per file to a large number to simplify the logic
        # TODO: allow multiple files
        num_images_per_file = await self.fileio.fw_nimgs_per_file.get_value()
        if num_images_per_file < self._min_num_images_per_file:
            await self.fileio.fw_nimgs_per_file.set(self._min_num_images_per_file)
            logger.warning(
                "Setting fw_nimgs_per_file to %d to force writing to a single HDF5 file",
                self._min_num_images_per_file,
            )
        driver = self.fileio

        shape = await asyncio.gather(
            *[sig.get_value() for sig in [driver.array_size_y, driver.array_size_x]]
        )
        datatype = "uint32"
        # Remove entries in shape that are zero
        shape = [x for x in shape if x > 0]

        mfp = await self._master_file_path
        # TODO sort out how to get from parent
        name = "eiger"
        exposures_per_event = await self.fileio.num_images.get_value()

        # TODO sort out how to tell tiled about the additional data files.
        return StreamResourceDataProvider(
            uri=urlunparse(("file", "localhost", str(mfp), "", "", None)),
            resources=[
                StreamResourceInfo(
                    data_key=f"{name}_image",
                    shape=(exposures_per_event, *shape),
                    # TODO sort out how to set this and mirror here
                    chunk_shape=(1, *shape),
                    dtype_numpy=np.dtype(datatype.lower()).str,
                    parameters={
                        "dataset": f"entry/data/data_{1:06d}",
                    },
                    # TODO put in better value
                    source="EIGER2_FILE_WRITER",
                )
            ],
            mimetype="application/x-hdf5",
            collections_written_signal=self.fileio.array_counter,
        )

    @property
    async def _master_file_path(self) -> Path | None:
        if self._file_info is None:
            logger.warning(
                "No master file path found for file info %s",
                self._file_info,
            )
            return None
        sequence_id = await self.fileio.sequence_id.get_value()
        return Path(
            self._file_info.directory_path
            / f"{self._file_info.filename}_{sequence_id}_master.h5"
        )

    async def observe_indices_written(
        self, timeout: float
    ) -> AsyncGenerator[int, None]:
        async for num_captured in observe_value(self.fileio.array_counter, timeout):
            yield num_captured

    async def get_indices_written(self) -> int:
        return await self.fileio.array_counter.get_value()

    async def stop(self) -> None:
        """Clean up file writing after acquisition and validate files exist."""

        # Check that the master files were written
        # for master_file_path in self._master_file_path_cache:
        #     if not master_file_path.exists():
        #         ...

        self._file_info = None
        await self.fileio.fw_enable.set(False)


# TODO sort out if ths is the right name of things
class EigerArmLogic(DetectorArmLogic):
    def __init__(
        self, driver: Eiger2DriverIO, driver_armed_signal: SignalR[bool] | None = None
    ):
        self.driver = driver
        if driver_armed_signal is not None:
            self.driver_armed_signal = driver_armed_signal
        else:
            self.driver_armed_signal = driver.acquire
        self.acquire_status: AsyncStatus | None = None
        self._rolling_image_counter = 0

    async def arm(self):
        self._rolling_image_counter = await self.driver.num_images_counter.get_value()
        ret = await self.driver.trigger.set(1)
        return ret

    async def wait_for_idle(self):
        target_num_images, frame_acquire_period = await asyncio.gather(
            self.driver.num_images.get_value(), self.driver.acquire_period.get_value()
        )
        frame_timeout = frame_acquire_period + DEFAULT_TIMEOUT
        done_timeout = frame_timeout * target_num_images
        target_num_images += self._rolling_image_counter
        async for images_complete in observe_value(
            self.driver.num_images_counter,
            timeout=frame_timeout,
            done_timeout=done_timeout,
        ):
            if images_complete == target_num_images:
                break

    async def disarm(self):
        self._rolling_image_counter = 0
        await stop_busy_record(self.driver.acquire)

        await asyncio.gather(
            self.driver.manual_trigger.set(False),
            self.driver.num_triggers.set(1),
        )


class EigerDetector(AreaDetector):
    """Eiger detector implementation using the AreaDetector pattern."""

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider,
        driver_suffix: str = "cam1:",
        name: str = "",
        config_sigs: Sequence[SignalR[SignalDatatypeT]] = (),
        plugins: dict[str, NDPluginBaseIO] | None = None,
    ):
        driver = Eiger2DriverIO(prefix + driver_suffix)
        controller = EigerController(driver)
        # if issubclass(writer_cls, EigerDataLogic):
        #     dataset_describer = ADBaseDatasetDescriber(driver)
        #     # EigerWriter takes the driver as the fileio, since it relies on driver PVs
        #     writer = writer_cls(
        #         driver,
        #         path_provider,
        #         dataset_describer=dataset_describer,
        #         plugins=plugins,
        #     )
        # else:
        writer_logic = EigerDataLogic(fileio=driver, path_provider=path_provider)
        arm_logic = EigerArmLogic(driver)
        super().__init__(
            prefix=prefix,
            driver=driver,
            trigger_logic=controller,
            writer_type=None,
            name=name,
            config_sigs=config_sigs,
            plugins=plugins,
            arm_logic=arm_logic,
        )
        # self.writer = None
        self.add_detector_logics(writer_logic)

    # TODO remove this as it should be identical to upstream.
    @WatchableAsyncStatus.wrap
    async def trigger(self) -> AsyncIterator[WatcherUpdate[int]]:
        """Trigger a single exposure.

        If [`prepare()`](#StandardDetector.prepare) has not been called since
        the last [`stage()`](#StandardDetector.stage), an implicit prepare is
        performed. When [](#OPHYD_ASYNC_PRESERVE_DETECTOR_STATE) is `YES`
        [](#DetectorTriggerLogic.default_trigger_info) is called to read current
        hardware state; otherwise a bare [`TriggerInfo()`](#TriggerInfo) is
        used.
        """
        if self._prepare_ctx is None:
            # Opt-in: set OPHYD_ASYNC_PRESERVE_DETECTOR_STATE=YES to have
            # trigger() read back current hardware state (e.g. num_images) via
            # default_trigger_info() instead of always falling back to TriggerInfo().
            # See ADR 0013 for rationale.
            # TODO: flip default to YES and remove this guard in a future PR once
            # downstream code has had time to implement default_trigger_info().
            preserve_state = (
                os.environ.get("OPHYD_ASYNC_PRESERVE_DETECTOR_STATE", "NO").upper()
                == "YES"
            )
            if preserve_state and self._trigger_logic is not None:

                def _logic_supported(base_class, method) -> bool:
                    # If the function that is bound in a subclass is the same as the function
                    # attached to the superclass, then the subclass has not overridden it, so
                    # this method is not supported by the subclass.
                    return method.__func__ is not getattr(base_class, method.__name__)

                _trigger_logic_supported = functools.partial(
                    _logic_supported, DetectorTriggerLogic
                )
                if not _trigger_logic_supported(
                    self._trigger_logic.default_trigger_info
                ):
                    raise RuntimeError(
                        f"OPHYD_ASYNC_PRESERVE_DETECTOR_STATE=YES is set but "
                        f"'{self.name}' has no default_trigger_info() - implement "
                        "default_trigger_info() on your DetectorTriggerLogic subclass "
                        "or unset the environment variable."
                    )
                trigger_info = await self._trigger_logic.default_trigger_info()
            else:
                trigger_info = TriggerInfo()
            await self.prepare(trigger_info)
        else:
            # Check the one that was provided is suitable for triggering
            trigger_info = self._prepare_ctx.trigger_info
            if trigger_info.number_of_events != 1:
                msg = (
                    "trigger() is not supported for multiple events, the detector was "
                    f"prepared with number_of_events={trigger_info.number_of_events}."
                )
                raise ValueError(msg)
            # Ensure the data provider is still usable
            await self._update_prepare_context(trigger_info)
        ctx = error_if_none(self._prepare_ctx, "Prepare should have been run")
        # Arm the detector and wait for it to finish.
        if self._arm_logic:
            await self._arm_logic.arm()

        async for update in self._wait_for_index(
            data_providers=ctx.streamable_data_providers,
            trigger_info=ctx.trigger_info,
            initial_collections_written=ctx.collections_written,
            collections_requested=1,
            wait_for_idle=True,
        ):
            yield update


with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=pp
    )
