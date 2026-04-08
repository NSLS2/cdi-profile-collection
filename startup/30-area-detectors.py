import numpy as np

from cditools.eiger_async import (
    EigerDriverIO,
    Eiger2DriverIO,
    EigerTriggerMode,
    EigerDataSource,
    EigerHDF5Format,
    logger,
)
from ophyd_async.core import (
    SignalDatatypeT,
    StreamResourceDataProvider,
    observe_value,
)
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import init_devices
from pathlib import Path
from typing import Sequence
from event_model import (
    StreamRange,
    ComposeStreamResource,
    ComposeStreamResourceBundle,
    StreamResource,
    StreamDatum,
)
import asyncio
from ophyd_async.core import (
    DetectorTriggerLogic,
    DetectorDataLogic,
    PathProvider,
    PathInfo,
    StreamableDataProvider,
    SignalR,
)
from ophyd_async.epics.adcore import (
    ADImageMode,
    AreaDetector,
    NDPluginBaseIO,
    trigger_info_from_num_images,
)
from collections.abc import AsyncGenerator, Iterator
from urllib.parse import urlunparse

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821


class EigerDocumentComposer:
    def __init__(
        self,
        full_file_name: Path,
        datasets: list[StreamResourceDataProvider],
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
        self._bundles: list[ComposeStreamResourceBundle] = [
            bundler_composer(
                mimetype="application/x-hdf5",
                uri=uri,
                data_key=ds.datakey_name,
                parameters={
                    "dataset": ds.dataset,
                    "chunk_shape": ds.chunk_shape,
                },
                uid=None,
                validate=True,
            )
            for ds in datasets
        ]

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
        self._file_info = self._path_provider(device_name="eiger2-1")
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
        driver = self.fileio

        shape, datatype = await asyncio.gather(
            asyncio.gather(
                *[sig.get_value() for sig in [driver.array_size_y, driver.array_size_x]]
            ),
            # TODO make sure this exists
            driver.data_type_signal.get_value(),
        )
        # Remove entries in shape that are zero
        shape = [x for x in shape if x > 0]

        mfp = await self._master_file_path
        # TODO sort out how to get from parent
        name = "eiger"
        exposures_per_event = 1
        return StreamResourceDataProvider(
            uri=f"file:///{mfp}",
            resource=[
                StreamResourceInfo(
                    data_key=f"{name}_image",
                    shape=(exposures_per_event, *shape),
                    # TODO sort out how to set this and mirror here
                    chunk_shape=(1, *shape),
                    dtype_numpy=np.dtype(datatype.value.lower()).str,
                    parameters={
                        "dataset": f"entry/data/data_{1:06d}",
                    },
                    # TODO this is not right, should be a PV
                    source="ADEiger FileWriter",
                )
            ],
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

    async def close(self) -> None:
        """Clean up file writing after acquisition and validate files exist."""

        # Check that the master files were written
        for master_file_path in self._master_file_path_cache:
            if not master_file_path.exists():
                logger.warning("Master file was not written: %s", master_file_path)

        self._file_info = None


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
        driver = EigerDriverIO(prefix + driver_suffix)
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

        super().__init__(
            prefix=prefix,
            driver=driver,
            trigger_logic=controller,
            writer_type=None,
            name=name,
            config_sigs=config_sigs,
            plugins=plugins,
        )
        # self.writer = None
        self.add_detector_logics(writer_logic)


with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", path_provider=pp
    )
