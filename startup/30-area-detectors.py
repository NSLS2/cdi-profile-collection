# from cditools.eiger_async import (
#     EigerDetector,
#     EigerDriverIO,
#     EigerTriggerMode,
#     logger,
#     EigerDataSource,
#     EigerHDF5Format,
# )
from ophyd_async.core import (
    SignalDatatypeT,
    StreamResourceDataProvider,
    StrictEnum,
    observe_value,
)
from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import init_devices
from pathlib import Path
from typing import Any, Sequence
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
    SubsetEnum,
)
from ophyd_async.epics.adcore import (
    ADImageMode,
    AreaDetector,
    NDPluginBaseIO,
    NDFileIO,
    ADBaseIO,
    trigger_info_from_num_images,
)
from collections.abc import AsyncIterator, AsyncGenerator, Iterator
from ophyd_async.epics.core import PvSuffix
from typing import Annotated as A
from urllib.parse import urlunparse
from logging import getLogger

pp = NSLS2PathProvider(RE.md)  # noqa: F821
logger = getLogger(__name__)


class EigerTriggerMode(SubsetEnum):
    """Trigger modes for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#implementation-of-standard-driver-parameters
    """

    INTERNAL_SERIES = "Internal Series"
    INTERNAL_ENABLE = "Internal Enable"
    EXTERNAL_SERIES = "External Series"
    EXTERNAL_ENABLE = "External Enable"
    CONTINUOUS = "Continuous"


class EigerROIMode(StrictEnum):
    """ROI modes for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#readout-setup
    """

    DISABLED = "Disable"
    _4M = "4M"


# TODO - add extra options in eiger2 and revert to StrictEnum
class EigerCompressionAlgo(SubsetEnum):
    """Compression algorithms for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#readout-setup
    """

    LZ4 = "LZ4"
    BSLZ4 = "BS LZ4"


class EigerDataSource(StrictEnum):
    """Data sources for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#readout-setup
    """

    NONE = "None"
    FILE_WRITER = "FileWriter"
    STREAM = "Stream"


class EigerStreamHdrDetail(StrictEnum):
    """Header detail levels for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#stream-interface
    """

    ALL = "All"
    BASIC = "Basic"
    NONE = "None"


class EigerHDF5Format(StrictEnum):
    """HDF5 formats for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#filewriter-interface
    """

    LEGACY = "Legacy"
    V2024_2 = "v2024.2"


class EigerStreamVersion(StrictEnum):
    """Stream versions for the Eiger detector.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#stream-interface
    """

    STREAM1 = "Stream1"
    STREAM2 = "Stream2"


class EigerDriverIO(ADBaseIO, NDFileIO):
    """Defines the full specifics of the Eiger driver.

    See https://areadetector.github.io/areaDetector/ADEiger/eiger.html#implementation-of-standard-driver-parameters
    """

    # Standard Driver Parameters
    trigger_mode: A[SignalRW[EigerTriggerMode], PvSuffix.rbv("TriggerMode")]
    num_images: A[SignalRW[int], PvSuffix.rbv("NumImages")]
    num_images_counter: A[SignalR[int], PvSuffix("NumImagesCounter_RBV")]
    num_exposures: A[SignalRW[int], PvSuffix.rbv("NumExposures")]
    acquire_time: A[SignalRW[float], PvSuffix.rbv("AcquireTime")]
    acquire_period: A[SignalRW[float], PvSuffix.rbv("AcquirePeriod")]
    temperature_actual: A[SignalR[float], PvSuffix("TemperatureActual")]
    max_size_x: A[SignalR[int], PvSuffix("MaxSizeX_RBV")]
    max_size_y: A[SignalR[int], PvSuffix("MaxSizeY_RBV")]
    array_size_x: A[SignalR[int], PvSuffix("ArraySizeX_RBV")]
    array_size_y: A[SignalR[int], PvSuffix("ArraySizeY_RBV")]
    manufacturer: A[SignalR[str], PvSuffix("Manufacturer_RBV")]
    model: A[SignalR[str], PvSuffix("Model_RBV")]
    serial_number: A[SignalR[str], PvSuffix("SerialNumber_RBV")]
    firmware_version: A[SignalR[str], PvSuffix("FirmwareVersion_RBV")]
    sdk_version: A[SignalR[str], PvSuffix("SDKVersion_RBV")]
    driver_version: A[SignalR[str], PvSuffix("DriverVersion_RBV")]

    # Detector Information
    description: A[SignalR[str], PvSuffix("Description_RBV")]
    x_pixel_size: A[SignalR[float], PvSuffix("XPixelSize_RBV")]
    y_pixel_size: A[SignalR[float], PvSuffix("YPixelSize_RBV")]
    sensor_material: A[SignalR[str], PvSuffix("SensorMaterial_RBV")]
    sensor_thickness: A[SignalR[float], PvSuffix("SensorThickness_RBV")]
    dead_time: A[SignalR[float], PvSuffix("DeadTime_RBV")]

    # Detector Status
    state: A[SignalR[str], PvSuffix("State_RBV")]
    error: A[SignalR[str], PvSuffix("Error_RBV")]
    temp0: A[SignalR[float], PvSuffix("Temp0_RBV")]
    humid0: A[SignalR[float], PvSuffix("Humid0_RBV")]

    # Acquisition Setup
    photon_energy: A[SignalRW[float], PvSuffix.rbv("PhotonEnergy")]

    # Trigger Setup
    trigger: A[SignalRW[float], PvSuffix("Trigger")]
    trigger_exposure: A[SignalRW[float], PvSuffix.rbv("TriggerExposure")]
    num_triggers: A[SignalRW[int], PvSuffix.rbv("NumTriggers")]
    manual_trigger: A[SignalRW[bool], PvSuffix.rbv("ManualTrigger")]

    # Readout Setup
    roi_mode: A[SignalRW[EigerROIMode], PvSuffix.rbv("ROIMode")]
    flatfield_applied: A[SignalRW[bool], PvSuffix.rbv("FlatfieldApplied")]
    countrate_corr_applied: A[SignalRW[bool], PvSuffix.rbv("CountrateCorrApplied")]
    pixel_mask_applied: A[SignalRW[bool], PvSuffix.rbv("PixelMaskApplied")]
    auto_summation: A[SignalRW[bool], PvSuffix.rbv("AutoSummation")]
    compression_algo: A[SignalRW[EigerCompressionAlgo], PvSuffix.rbv("CompressionAlgo")]
    data_source: A[SignalRW[EigerDataSource], PvSuffix.rbv("DataSource")]

    # Acquisition Status
    armed: A[SignalR[bool], PvSuffix("Armed")]
    bit_depth_image: A[SignalR[int], PvSuffix("BitDepthImage_RBV")]
    count_cutoff: A[SignalR[float], PvSuffix("CountCutoff_RBV")]

    # Stream Interface
    stream_enable: A[SignalRW[bool], PvSuffix.rbv("StreamEnable")]
    stream_state: A[SignalR[str], PvSuffix("StreamState_RBV")]
    stream_decompress: A[SignalRW[bool], PvSuffix.rbv("StreamDecompress")]
    stream_hdr_detail: A[
        SignalRW[EigerStreamHdrDetail], PvSuffix.rbv("StreamHdrDetail")
    ]
    stream_dropped: A[SignalR[int], PvSuffix("StreamDropped_RBV")]

    # Monitor Interface
    monitor_enable: A[SignalRW[bool], PvSuffix.rbv("MonitorEnable")]
    monitor_state: A[SignalR[str], PvSuffix("MonitorState_RBV")]
    monitor_timeout: A[SignalRW[float], PvSuffix.rbv("MonitorTimeout")]

    # Acquisition Metadata
    beam_x: A[SignalRW[float], PvSuffix.rbv("BeamX")]
    beam_y: A[SignalRW[float], PvSuffix.rbv("BeamY")]
    det_dist: A[SignalRW[float], PvSuffix.rbv("DetDist")]
    wavelength: A[SignalRW[float], PvSuffix.rbv("Wavelength")]

    # Detector Metadata
    chi_start: A[SignalRW[float], PvSuffix.rbv("ChiStart")]
    chi_incr: A[SignalRW[float], PvSuffix.rbv("ChiIncr")]
    kappa_start: A[SignalRW[float], PvSuffix.rbv("KappaStart")]
    kappa_incr: A[SignalRW[float], PvSuffix.rbv("KappaIncr")]
    omega_start: A[SignalRW[float], PvSuffix.rbv("OmegaStart")]
    omega_incr: A[SignalRW[float], PvSuffix.rbv("OmegaIncr")]
    phi_start: A[SignalRW[float], PvSuffix.rbv("PhiStart")]
    phi_incr: A[SignalRW[float], PvSuffix.rbv("PhiIncr")]
    two_theta_start: A[SignalRW[float], PvSuffix.rbv("TwoThetaStart")]
    two_theta_incr: A[SignalRW[float], PvSuffix.rbv("TwoThetaIncr")]

    # Minimum change allowed
    wavelength_eps: A[SignalRW[float], PvSuffix.rbv("WavelengthEps")]
    energy_eps: A[SignalRW[float], PvSuffix.rbv("EnergyEps")]

    # FileWriter Interface
    fw_enable: A[SignalRW[bool], PvSuffix.rbv("FWEnable")]
    fw_state: A[SignalR[str], PvSuffix("FWState_RBV")]
    fw_compression: A[SignalRW[bool], PvSuffix.rbv("FWCompression")]
    fw_name_pattern: A[SignalRW[str], PvSuffix.rbv("FWNamePattern")]
    sequence_id: A[SignalR[int], PvSuffix("SequenceId")]
    save_files: A[SignalRW[bool], PvSuffix.rbv("SaveFiles")]
    file_owner: A[SignalRW[str], PvSuffix.rbv("FileOwner")]
    file_owner_grp: A[SignalRW[str], PvSuffix.rbv("FileOwnerGrp")]
    file_perms: A[SignalRW[float], PvSuffix.rbv("FilePerms")]
    fw_free: A[SignalR[float], PvSuffix("FWFree_RBV")]
    fw_auto_remove: A[SignalRW[bool], PvSuffix.rbv("FWAutoRemove")]
    fw_nimgs_per_file: A[SignalRW[int], PvSuffix.rbv("FWNImagesPerFile")]


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
        self._file_info = self._path_provider(device_name='eiger2-1')
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

        return StreamResourceDataProvider(
            
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
                self._datasets,
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
