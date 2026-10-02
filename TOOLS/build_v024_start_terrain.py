"""v024 free-ride terrain policy.

The user explicitly deferred race-start correctness for this version. Therefore
the start lane is not allowed to grade or modify the riding terrain at all.
The authored start TCL/RDF can remain as placeholder race data, but terrain.raw
is an exact copy of the validated v024 main track terrain.
"""
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
from v024_common import *

def fields(H,shape=(N,N)):
    """Mask-only start fields for downstream release assembly.

    Racing is deferred, so these fields DO NOT grade terrain. They only provide
    the start/retirement/main-lane masks expected by the established packaging
    scripts, allowing the playable free-ride PKZ to be assembled normally.
    """
    cfg=read(O/'facility_layout.json');q,w=route();sa=np.load(O/'route.npz')['start']
    old=np.load(R/'V009_SOURCE/baseline_route.npz')['start']
    stree=cKDTree(sa[:,:2]);mtree=cKDTree(q[:,:2]);otree=cKDTree(old[:,:2])
    rows,cols=shape;xx,zz=np.meshgrid(np.linspace(0,SIZE,cols),np.linspace(SIZE,0,rows));pts=np.c_[xx.ravel(),zz.ravel()]
    sd,si=stree.query(pts,workers=2);md,mi=mtree.query(pts,workers=2);od,oi=otree.query(pts,workers=2)
    st=sa[si,3];widths=np.interp(st,*np.array(cfg['start_width_knots']).T)
    start=(1-ease((sd-widths/2+.4)/1.2))*ease((pts[:,1]-cfg['start_origin_xz'][1]+2)/2)
    old_width=10.5+25.5*(1-ease((old[oi,3]-12)/43))
    retire=(1-ease((od-old_width/2)/2))*(1-ease((236-pts[:,0])/2))
    dv=pts-q[mi,:2];th=q[mi,2]
    main_station=q[mi,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th)
    zero=np.zeros(len(pts),dtype=float)
    vals=dict(weight=zero,start=start,retire=retire,main_distance=md,main_width=w[mi],
              start_station=st,start_distance=sd,merge_opening=zero,main_station=main_station)
    return {k:v.reshape(shape) for k,v in vals.items()}

def main():
    source=O/'main_terrain.raw'
    base=np.fromfile(source,'<u2').reshape(N,N)
    base.tofile(O/'terrain.raw')
    Image.fromarray(base).save(O/'terrain_16bit.png')
    H=base.astype(np.float32)/65535*SCALE
    np.save(O/'height_metres.npy',H)

    # Keep a structurally valid fields file for downstream render/packaging code,
    # but every start-terrain influence is zero because racing is deferred.
    z=np.zeros((N,N),dtype=np.float32)
    np.savez_compressed(
        O/'facility_fields.npz',
        weight=z,start=z,retire=z,merge_opening=z,
        main_distance=np.full((N,N),999,dtype=np.float32),
        main_width=z,start_station=z,start_distance=np.full((N,N),999,dtype=np.float32),
        main_station=z
    )

    qa=dict(
        raw_sha256=sha(O/'terrain.raw'),
        main_terrain_sha256=sha(O/'main_terrain.raw'),
        terrain_exactly_preserved=sha(O/'terrain.raw')==sha(O/'main_terrain.raw'),
        start_terrain_modification_disabled=True,
        racing_deferred_by_user=True,
        race_start_runtime_check_pending=True,
        native_compilation=False,
        in_game_riding=False,
        start_terrain_checks_pass=True,
        note='v024 free-ride build: start route does not alter terrain; race-start behavior intentionally deferred.'
    )
    assert qa['terrain_exactly_preserved']
    save(R/'DOCUMENTATION/v024_start_validation.json',qa)
    print(qa)

if __name__=='__main__':
    main()
