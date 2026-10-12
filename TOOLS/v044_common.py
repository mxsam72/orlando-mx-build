"""New standard-weather visuals on the authenticated delivered v043 source."""
from pathlib import Path
import hashlib, json, os
import numpy as np
R=Path(__file__).resolve().parents[1]
S=R/'V044_SOURCE'; BASE=R/'V043_OUTPUT'; O=R/'V044_OUTPUT'
M=O/'materials'; F=O/'facility_textures'; NAME='orlandomx_2026_v044'
SIZE=600.; N=2049; SCALE=18.
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    atomic(p,(json.dumps(value,indent=2)+'\n').encode())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    return h.hexdigest()
def atomic(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    tmp.replace(p)
def image_file(im,p):
    import io
    b=io.BytesIO();im.save(b,format='TGA');atomic(p,b.getvalue())
