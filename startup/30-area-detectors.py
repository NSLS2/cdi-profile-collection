from cditools.eiger import EigerFileHandler, EigerBase, EigerSingleTrigger

eiger = EigerSingleTrigger(prefix="XF:09ID1-ES{Det:Eig1}", name="eiger", labels=["det"])
