"""Immutable v036 baseline and shared v037 output helpers."""
from v036_common import atomic, copy_exact, image_file, read, save, sha
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.interpolate import LinearNDInterpolator
R = Path(__file__).resolve().parents[1]
S = R/'V037_SOURCE'
BASE = R/'V036_OUTPUT'
O = R/'V037_OUTPUT'
NAME = 'orlandomx_2026_v037'
SIZE = 600.0
ROAD_SAMPLER = None
def bind_road_mesh(vertices):
    global ROAD_SAMPLER
    v=np.asarray(vertices)
    ROAD_SAMPLER=LinearNDInterpolator(v[:,[0,2]],v[:,1],fill_value=np.nan)
def height_field():
    return np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
def ground(h,xz):
    p=np.atleast_2d(xz)
    return map_coordinates(h,[(SIZE-p[:,1])/SIZE*2048,p[:,0]/SIZE*2048],order=1,mode='nearest')
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def road_height(h,xz,cfg):
    p=np.atleast_2d(xz);v=p-np.asarray(cfg['centre_xz_m'])
    radial=np.hypot(v[:,0],np.maximum(np.abs(v[:,1])-cfg['half_straight_m'],0))
    camber=cfg['maximum_curve_camber_m']*smooth((radial-34)/21)*smooth((np.abs(v[:,1])-26)/15)
    apron=smooth((v[:,0]+69)/14)
    y=ground(h,p)+cfg['surface_above_heightmap_m']*apron+camber
    if ROAD_SAMPLER is not None:
        sampled=ROAD_SAMPLER(p);good=np.isfinite(sampled);y[good]=sampled[good]
    return y
