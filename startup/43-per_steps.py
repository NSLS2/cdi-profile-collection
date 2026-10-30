from bluesky.utils import FailedStatus


# basic retry implemented for a vimba IOC.  may need to be extended for others
def retry_per_step(detectors,motor,step):
    max_retry=5
    
    for attempt in range(1,max_retry+1):
        try:    
            yield from bps.mv(motor,step)
            yield from bps.one_1d_step(detectors,motor,step)
            break
        except (FailedStatus) as e:
            print(f"[W] acquisition failed on attempt {attempt}/{max_retry} at position {step:.4f}")
            if attempt == max_retry:
                print(f"[E] too many attempts;raising {e}")
                raise e
            for d in detectors:
                #I would like to do this, but the vimba camera implementation doesn't support it
                #yield from bps.stop(d)
                try:
                    if hasattr(d.driver,"acquire"):
                        yield from bps.abs_set(d.driver.acquire, False, wait=True)
                    yield from bps.unstage(d)
                    yield from bps.stage(d)
                except Exception as detexc:
                    print(f"Could not reset detector {d.name}: {detexc}")
            yield from bps.sleep(10)

