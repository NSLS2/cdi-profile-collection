import os

import nslsii
from bluesky.callbacks.tiled_writer import TiledWriter
from bluesky.plans import count
from ophyd.signal import EpicsSignalBase
from ophyd.sim import det1, det2
from tiled.client import from_profile, from_uri

EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)

print("LOADING 00")

nslsii.configure_base(
    get_ipython().user_ns,
    publish_documents_with_kafka="cdi",
)

tiled_writing_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    api_key=os.environ["TILED_BLUESKY_WRITING_API_KEY_CDI"],
)

c = tiled_reading_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/cdi/raw",
    include_data_sources=True,
)

RE.md["tiled_access_tags"] = ["cdi_beamline"]

tw = TiledWriter(client=tiled_writing_client)

RE.subscribe(tw)
