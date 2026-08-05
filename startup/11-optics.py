from nslsii.devices import TwoButtonShutter
from ophyd import DeviceStatus

class CDITwoButtonShutter(TwoButtonShutter):
    def stop(self, success = False):
        pass

    def close(self,success = False):
        self.set("Close")
        return True 

    def open(self,success = False):
        self.set("Open")
        return True

shut_fe = CDITwoButtonShutter("XF:09IDA-PPS{Sh:FE}", name = "shut_fe")
shut_a = CDITwoButtonShutter("XF:09IDA-PPS{L1-S1}", name = "shut_a")
shut_b = CDITwoButtonShutter("XF:09IDB-PPS{L1-S3}", name = "shut_b")

