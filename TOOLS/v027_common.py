"""Shared v027 layout and source utilities, in game metres and +Z."""
from pathlib import Path
import json, hashlib, os, zipfile
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v025_materials import ease

R=Path(__file__).resolve().parents[1]
S=R/'V027_SOURCE'; O=R/'V027_OUTPUT'; M=O/'materials'
NAME='orlandomx_2026_v027'; SIZE=600.; N=2049; SCALE=18.
EXPECTED={'terrain.raw':'334f8042e4f2c3f2507e2ace1dea52e1dffa80f2900f89a3c701bdc39296d27f',
          'scenery.fbx':'98dc23a52fc9868a155d47368e10ff5645727033fc98b649cfb9d264cf9cdd90',
          'start.tcl':'b1dcaa07fe6e7a95eb1acfc40af00139ce00850e9df1133b894e3d0c3be2b0df'}
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_npz(p,**arrays):
    p=Path(p); temporary=p.with_suffix('.npz.tmp')
    with temporary.open('wb') as f:
        np.savez_compressed(f,**arrays); f.flush(); os.fsync(f.fileno())
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None,'Incomplete source array checkpoint'
        assert len(z.namelist())==len(arrays)
    temporary.replace(p)
def ground(h,xz):
    a=np.asarray(xz); return map_coordinates(h,[(SIZE-a[...,1])/SIZE*(len(h)-1),a[...,0]/SIZE*(len(h)-1)],order=1,mode='nearest')
def sample_polyline(points,spacing=.2):
    a=np.asarray(points,float); ds=np.linalg.norm(np.diff(a,axis=0),axis=1)
    keep=np.r_[True,ds>1e-8]; a=a[keep]
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(a,axis=0),axis=1))]
    u=np.linspace(0,s[-1],max(2,int(s[-1]/spacing)+1))
    x=np.interp(u,s,a[:,0]); z=np.interp(u,s,a[:,1])
    th=np.unwrap(np.arctan2(np.gradient(z),np.gradient(x)))
    return np.c_[x,z,th,u]
def access_layout(start,cfg):
    end=cfg['practice_merge_start_station_m']; ss=np.linspace(0,end,1+int(end/.2))
    x=np.interp(ss,start[:,3],start[:,0]); z=np.interp(ss,start[:,3],start[:,1]); th=np.interp(ss,start[:,3],start[:,2])
    knots=np.asarray(read(R/'V024_SOURCE/facilities.json')['start_width_knots'])
    half=np.interp(ss,knots[:,0],knots[:,1])/2
    taper=1-ease((ss-cfg['practice_offset_fade_start_station_m'])/(end-cfg['practice_offset_fade_start_station_m']))
    offset=(half+cfg['practice_start_outer_clearance_m'])*taper
    p=np.c_[x+np.sin(th)*offset,z-np.cos(th)*offset]
    # Exactly join the accepted start route with a matching terminal tangent.
    connector=np.asarray(cfg['connector_points_xz_m'])
    lane=sample_polyline(np.vstack([connector[-1],p]))
    join=np.array([x[-1],z[-1]])
    assert np.linalg.norm(lane[-1,:2]-join)<1e-8
    return dict(lane=lane,parallel=np.c_[p,ss],connector=sample_polyline(connector),join=join)
def route_projection(points,q,width=None,open_line=False):
    dist,i=cKDTree(q[:-1,:2]).query(points,workers=2)
    dv=points-q[i,:2]; along=dv[:,0]*np.cos(q[i,2])+dv[:,1]*np.sin(q[i,2])
    station=q[i,3]+along; lat=-dv[:,0]*np.sin(q[i,2])+dv[:,1]*np.cos(q[i,2])
    if open_line: valid=(station>=0)&(station<=q[-1,3])
    else: station%=q[-1,3]; valid=np.ones(len(points),bool)
    half=np.full(len(points),3.25) if width is None else np.interp(np.clip(station,0,q[-1,3]),q[:,3],width)/2
    return dist,lat,station,half,valid
