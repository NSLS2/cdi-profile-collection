import os

import nslsii
from bluesky.callbacks.tiled_writer import TiledWriter
from ophyd.signal import EpicsSignalBase
from tiled.client import from_uri

EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)

print("LOADING 00")

### Redis
with open("/etc/bluesky/redis.secret", "r") as f:
    redis_secret = f.read().strip()
    os.environ["REDIS_PASSWORD"] = redis_secret

### Configure Base
nslsii.configure_base(
    get_ipython().user_ns,  # noqa: F821
    publish_documents_with_kafka="cdi",
    redis_url="xf09id1-cdi-redis1.nsls2.bnl.gov",
    redis_port=6380,
    redis_ssl=True
)

### Tiled
tiled_writing_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    api_key=os.environ["TILED_BLUESKY_WRITING_API_KEY_CDI"],
)

c = tiled_reading_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    include_data_sources=True,
)

RE.md["tiled_access_tags"] = ["cdi_beamline"]  # noqa: F821

tw = TiledWriter(client=tiled_writing_client)

RE.subscribe(tw)  # noqa: F821
