from cditools.eiger_async import (
    EigerDetector,
    EigerDriverIO,
    EigerTriggerMode,
    logger,
    EigerDataSource,
    EigerHDF5Format,
)
from ophyd_async.core import StrictEnum, observe_value
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import init_devices
from pathlib import Path
from typing import Any
from event_model import (
    DataKey,
    StreamRange,
    ComposeStreamResource,
    ComposeStreamResourceBundle,
    StreamResource,
    StreamDatum,
)
import asyncio
from bluesky.protocols import StreamAsset
from ophyd_async.core import (
    DetectorTriggerLogic,
    DetectorDataLogic,
    PathProvider,
    PathInfo,
    StreamableDataProvider,
    SignalR,
    SignalRW,
)
from ophyd_async.epics.adcore import ADImageMode
from collections.abc import AsyncIterator, AsyncGenerator, Iterator
from ophyd_async.epics.core import PvSuffix
from typing import Annotated as A
from urllib.parse import urlunparse

pp = NSLS2PathProvider(RE.md)  # noqa: F821


class EigerDocumentComposer:
    def __init__(
        self,
        full_file_name: Path,
        last_emitted_index: int = 0,
        hostname: str = "localhost",
    ) -> None:
        self._last_emitted = last_emitted_index
        self._hostname = hostname
        uri = urlunparse(
            (
                "file",
                self._hostname,
                str(full_file_name.absolute()),
                "",
                "",
                None,
            )
        )
        bundler_composer = ComposeStreamResource()
        # self._bundles: list[ComposeStreamResourceBundle] = [
        #     bundler_composer(
        #         mimetype="application/x-hdf5",
        #         uri=uri,
        #         data_key=ds.data_key,
        #         parameters={
        #             "dataset": ds.dataset,
        #             "chunk_shape": ds.chunk_shape,
        #         },
        #         uid=None,
        #         validate=True,
        #     )
        #     for ds in datasets
        # ]

    def stream_resources(self) -> Iterator[StreamResource]:
        for bundle in self._bundles:
            yield bundle.stream_resource_doc

    def stream_data(self, indices_written: int) -> Iterator[StreamDatum]:
        if indices_written > self._last_emitted:
            indices: StreamRange = {
                "start": self._last_emitted,
                "stop": indices_written,
            }
            self._last_emitted = indices_written
            for bundle in self._bundles:
                yield bundle.compose_stream_datum(indices)


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

        await self.driver.acquire_time.set(livetime)

        await self.driver.trigger_mode.set(EigerTriggerMode.INTERNAL_SERIES)

        if num == 0:
            image_mode = ADImageMode.CONTINUOUS
        else:
            image_mode = ADImageMode.MULTIPLE

        await self.driver.num_triggers.set(num)

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


class EigerStreamVersion(StrictEnum):
    """Stream versions for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#stream-interface
    """

    STREAM1 = "Stream1"
    STREAM2 = "Stream2"


class Eiger2DriverIO(EigerDriverIO):
    """Eiger2 driver interface."""

    # Detector Status
    hv_reset_time: A[SignalRW[float], PvSuffix.rbv("HVResetTime")]
    hv_reset: A[SignalRW[bool], PvSuffix("HVReset", "HVReset")]
    hv_state: A[SignalR[str], PvSuffix("HVState_RBV")]

    # Acquisition Setup
    threshold: A[SignalRW[float], PvSuffix.rbv("Threshold")]
    threshold1_enable: A[SignalRW[bool], PvSuffix.rbv("Threshold1Enable")]
    threshold2: A[SignalRW[float], PvSuffix.rbv("Threshold2")]
    threshold2_enable: A[SignalRW[bool], PvSuffix.rbv("Threshold2Enable")]
    threshold_diff_enable: A[SignalRW[bool], PvSuffix.rbv("ThresholdDiffEnable")]
    counting_mode: A[SignalRW[str], PvSuffix.rbv("CountingMode")]

    # Trigger Setup
    ext_gate_mode: A[SignalRW[str], PvSuffix.rbv("ExtGateMode")]
    trigger_start_delay: A[SignalRW[float], PvSuffix.rbv("TriggerStartDelay")]

    # Readout Setup
    signed_data: A[SignalRW[bool], PvSuffix.rbv("SignedData")]

    # Stream Interface
    stream_version: A[SignalRW[EigerStreamVersion], PvSuffix.rbv("StreamVersion")]
    stream_hdr_appendix: A[SignalRW[str], PvSuffix.rbv("StreamHdrAppendix")]
    stream_img_appendix: A[SignalRW[str], PvSuffix.rbv("StreamImgAppendix")]

    # FileWriter Interface
    fw_hdf5_format: A[SignalRW[EigerHDF5Format], PvSuffix.rbv("FWHDF5Format")]


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
        # self._datasets: list[HDFDatasetDescription] = []
        self._master_file_path_cache: list[Path] = []

    async def prepare_unbounded(self, datakey_name: str) -> StreamableDataProvider:
        """Provider can work for an unbounded number of collections."""
        # Get file path info from path provider
        self._file_info = self._path_provider()
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
            self.fileio.data_source.set(EigerDataSource.FILE_WRITER),
            self.fileio.num_capture.set(0),
            # Use array_counter to track the total number of images written
            self.fileio.array_counter.set(0),
        )

        if not await self.fileio.file_path_exists.get_value():
            msg = f"File path {self._file_info.directory_path} does not exist"
            raise FileNotFoundError(msg)

        if isinstance(self.fileio, Eiger2DriverIO):
            await self.fileio.fw_hdf5_format.set(EigerHDF5Format.LEGACY)

        # Force the number of images per file to a large number to simplify the logic
        num_images_per_file = await self.fileio.fw_nimgs_per_file.get_value()
        if num_images_per_file < self._min_num_images_per_file:
            await self.fileio.fw_nimgs_per_file.set(self._min_num_images_per_file)
            logger.warning(
                "Setting fw_nimgs_per_file to %d to force writing to a single HDF5 file",
                self._min_num_images_per_file,
            )

        raise NotImplementedError(self)

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

    async def collect_stream_docs(
        self, name: str, indices_written: int
    ) -> AsyncIterator[StreamAsset]:
        """Generate stream documents for the written HDF5 files."""
        if indices_written:
            master_file_path = await self._master_file_path
            if master_file_path is None:
                msg = f"Master file path is not set for {name}: {self._file_info}"
                raise ValueError(msg)

            # Eiger generates a new master file for each trigger
            # so we need to create a new composer with a new
            # master file path
            composer = EigerDocumentComposer(
                master_file_path,
                last_emitted_index=indices_written - 1,
            )

            # For later validation
            self._master_file_path_cache.append(master_file_path)

            for doc in composer.stream_resources():
                yield "stream_resource", doc

            for doc in composer.stream_data(indices_written):
                yield "stream_datum", doc

    async def observe_indices_written(
        self, timeout: float
    ) -> AsyncGenerator[int, None]:
        async for num_captured in observe_value(self.fileio.array_counter, timeout):
            yield num_captured

    async def get_indices_written(self) -> int:
        return await self.fileio.array_counter.get_value()

    async def close(self) -> None:
        """Clean up file writing after acquisition and validate files exist."""

        # Check that the master files were written
        for master_file_path in self._master_file_path_cache:
            if not master_file_path.exists():
                logger.warning("Master file was not written: %s", master_file_path)

        self._file_info = None


with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}",
        name="eiger",
        path_provider=pp,
        md=RE.md,  # noqa: F821
    )
