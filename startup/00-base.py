print(f"Loading {__file__!r} ...")

import os

import nslsii
from bluesky_tiled_plugins import BufferingWrapper, TiledWriter
from ophyd.signal import EpicsSignalBase
from tiled.client import from_uri
import bluesky.utils as bsu

# Have ophyd-async keep detector state constant when not explicitly overridden
os.environ["OPHYD_ASYNC_PRESERVE_DETECTOR_STATE"] = "YES"
RUNNING_IN_NSLS2_CI = os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES"

EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)

### Configure Base
nslsii.configure_base(
    get_ipython().user_ns,  # noqa: F821
    publish_documents_with_kafka="cdi",
    redis_url="xf09id1-cdi-redis1.nsls2.bnl.gov",
    redis_port=6380,
    redis_ssl=True,
)

### Tiled
tiled_writing_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    api_key=os.environ["TILED_BLUESKY_WRITING_API_KEY_CDI"],
)
tiled_writing_client.context.http_client.headers["tiled-qos"] = "acquisition"

c = tiled_reading_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    include_data_sources=True,
)
c.context.http_client.headers["tiled-qos"] = "acquisition"

TILED_BACKUP_ROOT = "/nsls2/data/cdi/shared/config/bluesky/tiled_backup"

tw = TiledWriter(client=tiled_writing_client,
                 backup_directory=f"{TILED_BACKUP_ROOT}/sql")

# Thread-safe wrapper for TiledWriter: documents are buffered in an
# in-process queue, so the RunEngine never blocks on Tiled.
tw = BufferingWrapper(tw)

RE.subscribe(tw)  # noqa: F821
# RE.msg_hook = bsu.ts_msg_hook
