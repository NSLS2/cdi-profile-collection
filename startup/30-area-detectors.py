from cditools.eiger_async import EigerDetector
from cditools.merlin_async import MerlinDetector
from nslsii.ophyd_async.providers import NSLS2PathProvider

from ophyd_async.core import init_devices
from ophyd_async.epics import adcore, advimba

print("LOADING 30")

pp = NSLS2PathProvider(RE.md)  # noqa: F821

with init_devices():
    eiger = EigerDetector(
        prefix="XF:09ID1-ES{Det:Eig1}", name="eiger2-1", path_provider=pp
    )
    merlin = MerlinDetector(
        "XF:09ID1-ES{Det:Merlin1}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="merlines-1",
    )

    cam1 = advimba.VimbaDetector(
        "XF:09IDA-BI{DM:1-Cam:1}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-1",
    )
    cam2 = advimba.VimbaDetector(
        "XF:09IDA-BI{WBStop-Cam:2}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-2",
    )
    cam3 = advimba.VimbaDetector(
        "XF:09IDA-BI{VPM-Cam:3}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-3",
    )
    cam4 = advimba.VimbaDetector(
        "XF:09IDA-BI{HPM-Cam:4}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-5",
    )
    cam5 = advimba.VimbaDetector(
        "XF:09IDA-BI{DM:2-Cam:5}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-5",
    )
    cam6 = advimba.VimbaDetector(
        "XF:09IDB-BI{DM:3-Cam:6}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-6",
    )
    cam7 = advimba.VimbaDetector(
        "XF:09IDC-BI{FS:KBv-Cam:7}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-7",
    )

    cam8 = advimba.VimbaDetector(
        "XF:09IDC-BI{FS:KBh-Cam:8}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-8",
    )
    cam9 = advimba.VimbaDetector(
        "XF:09IDC-BI{BCU-Cam:9}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-9",
    )
    cam10 = advimba.VimbaDetector(
        "XF:09IDC-BI{SMPL-Cam:10}",
        adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
        name="cam-10",
    )
    # cam15 = advimba.VimbaDetector(
    #     "XF:09IDC-BI{Cam:15}",
    #     adcore.ADWriterFactory.hdf(pp, writer_suffix="HDF1:"),
    #     name="cam-15",
    #     )
