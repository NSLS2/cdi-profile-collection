import nslsii
from bluesky.run_engine import RunEngine, autoawait_in_bluesky_event_loop

nslsii.configure_base(
    get_ipython().user_ns,
    broker_name="temp",
    publish_documents_with_kafka=True,
    redis_url="info.cdi.nsls2.bnl.gov",
)

RE = RunEngine()
autoawait_in_bluesky_event_loop()

