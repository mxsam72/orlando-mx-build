"""v038 uses the immutable native v037 source checkpoint."""
from v036_common import atomic, copy_exact, image_file, read, save, sha
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates

R = Path(__file__).resolve().parents[1]
S = R/'V038_SOURCE'
BASE = R/'V037_OUTPUT'
O = R/'V038_OUTPUT'
NAME = 'orlandomx_2026_v038'
SIZE = 600.

def height_field():
    return np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18

def ground(h,xz):
    p=np.atleast_2d(xz)
    return map_coordinates(h,[(SIZE-p[:,1])/SIZE*2048,p[:,0]/SIZE*2048],order=1,mode='nearest')
