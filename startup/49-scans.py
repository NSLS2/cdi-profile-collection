print(f'LOADING {__file__}...')

import bluesky.plans as bp
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from ophyd.sim import det, motor, signal 

#might or might not need these, try to keep supporting stuff in 40-scanutils
#import numpy as np
#import scipy as sp

#these are the helper scan plans that help to ensure that users can rountinely
#collect data at CDI.

#list of devices that comprise an import snapshot of the state that the
#instrument was in when the scan was launched
default_devices_v1=[gon.align.x,gon.align.y,gon.align.z,gon.align.rx,gon.align.rz,
    gon.sam.t_sm.lx,gon.sam.t_sm.lz,gon.sam.t_lg.lx,gon.sam.t_lg.lz,
    gon.sam.c_sm.lrx,gon.sam.c_sm.lrz,gon.sam.c_lg.lrx,gon.sam.c_lg.lrz,
    gon.sam.ly,dm4.bpm.x,dm4.bpm.y,
    tetra.posX, tetra.posY, ring_current, energy.energy,
    T1.tz,T1.ay,T1.ty,T1.ax,T2.tz,T2.ay,T2.ty,T2.ax]

#the two primary data collection modes are to rock \mu or scan the energy

def scan_abs_mu(start,stop,num,*,mot=gon.sam.ry,det=[eiger],
        state_devices=default_devices_v1,md=None):
    """
    This scans rocks the angle about the vertical in the Lab frame and collects
    2D diffraction patterns at each point on the curve.  It wraps a standard 
    plan and includes start and end state information.

    This scan requires start and stop positions in absolute readback values.

    To trigger the default detector against the default axis 
    from -1 to 1 in 3 steps:  
    
    RE(scan_mu(-1,1,3))
    
    det == dict of detctors, default: eiger
    mot == axis to scan, default: mu
    state_devices == import devices for defining initial and final state

    """
    #make a dict or copy the metadata for new metadata
    if md is None:
        _md = {}
    else:
        _md = dict(md)
    
    #record the starting values of the scanned motor and the transmision
    mot_val = yield from bps.rd(mot)
    T = yield from bps.rd(bank)
    _md.update({
        'plan_name':'CDI_rock_mu_v1',
        'instr_state':{'start_pos':trunc(mot_val),
            'transmission': trunc(T)
            }
    })
    #record standard motor positions
    for i in state_devices:
        mname = i.name
        mval = yield from bps.rd(i)
        _md['instr_state'].update({mname:trunc(mval)})


    return (yield from bp.scan(det,mot,start,stop,num,md=_md))


def scan_E():
    return True
