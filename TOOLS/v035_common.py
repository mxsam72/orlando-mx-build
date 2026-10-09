"""Shared helpers for the tested-v030-preserving visual update."""
from pathlib import Path
import hashlib, io, json, os, shutil
import numpy as np
from PIL import Image

R = Path(__file__).resolve().parents[1]
S = R/'V035_SOURCE'
BASE = R/'V033_OUTPUT'
O = R/'V035_OUTPUT'
M = O/'materials'
NAME = 'orlandomx_2026_v035'
SIZE = 600.0
N = 2048
SCANS = Path(os.environ.get('V032_SCANS', str(R/'BUILD/v032_scans')))

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        while b := f.read(1024*1024): h.update(b)
    return h.hexdigest()

def atomic(p, data):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_name(p.name+'.write-tmp')
    # Windows defaults to text mode unless O_BINARY is explicit; source FBX
    # and texture bytes must never undergo CR/LF translation.
    fd = os.open(t, os.O_WRONLY|os.O_CREAT|os.O_TRUNC|getattr(os, 'O_BINARY', 0), 0o600)
    try:
        view = memoryview(data); done = 0
        while done < len(view):
            n = os.write(fd, view[done:done+262144])
            if n <= 0: raise IOError('Incomplete write: '+p.name)
            done += n
        os.fsync(fd)
    finally: os.close(fd)
    assert t.stat().st_size == len(data), f'Incomplete binary write: {p.name}'
    os.replace(t, p)

def save(p, value):
    atomic(p, (json.dumps(value, indent=2)+'\n').encode())

def image_file(im, p):
    b = io.BytesIO(); im.save(b, format='PNG' if str(p).endswith('.png') else 'TGA')
    atomic(p, b.getvalue())
    with Image.open(p) as check: check.load(); assert check.size == im.size

def save_png(im,p): image_file(im,p)

def copy_exact(src,dst):
    atomic(dst, Path(src).read_bytes())
    assert sha(src) == sha(dst)

def layer_blocks(text):
    import re
    blocks=[]
    for match in re.finditer(r'(?m)^layer(\d+)\s*\n?\{',text):
        end=match.end(); depth=1
        while depth:
            if text[end]=='{': depth+=1
            elif text[end]=='}': depth-=1
            end+=1
        blocks.append((int(match[1]), match.start(), text[match.start():end]))
    return blocks

EXPECTED = {'start.tcl': 'b1dcaa07fe6e7a95eb1acfc40af00139ce00850e9df1133b894e3d0c3be2b0df'}
