#!/usr/bin/env python3
"""Package the small verified v007 overlay, reusing immutable v006 assets."""
from pathlib import Path
import hashlib,json,zipfile,re
import numpy as np
from scipy.ndimage import map_coordinates

ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    old=np.fromfile(ROOT/'BUILD/v006_terrain.raw',dtype='<u2').reshape(2049,2049)/65535*18
    new=np.fromfile(ROOT/'02_HEIGHTMAP/terrain.raw',dtype='<u2').reshape(2049,2049)/65535*18
    def change(x,z):return float(map_coordinates(new-old,[[(600-z)/600*2048],[x/600*2048]],order=1)[0])
    out=ROOT/'12_RELEASE/orlandomx_2026_v007'
    base=ROOT/'12_RELEASE/orlandomx_2026_v006'
    text=(base/'marshals.cfg').read_text()
    def pos(m):
        x,y,z=map(float,m.group(1,2,3))
        return f'x = {x:.6f}\n y = {y+change(x,z):.6f}\n z = {z:.6f}'
    text=re.sub(r'x\s*=\s*([\d.]+)\s+y\s*=\s*([\d.]+)\s+z\s*=\s*([\d.]+)',pos,text)
    (out/'marshals.cfg').write_text(text)
    text=(base/'orlandomx_2026_v006.tsc').read_text()
    def cam(m):
        x,y,z=map(float,m.group(1,2,3))
        return f'pos = {x:.6f},{y+change(x,z):.6f},{z:.6f}'
    text=re.sub(r'pos\s*=\s*([\d.]+),([\d.]+),([\d.]+)',cam,text)
    (out/'orlandomx_2026_v007.tsc').write_text(text)
    files=[ROOT/'02_HEIGHTMAP/terrain.raw',ROOT/'BUILD/native_coordinate_probes.json',ROOT/'V007_SOURCE/scenery_patch.json']
    files += [p for p in sorted(out.iterdir()) if p.is_file() and p.suffix not in ('.map','.trh')]
    archive=ROOT/'BUILD/v007_overlay.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in files:
            info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),(2026,9,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes(),compresslevel=7)
    destination=ROOT/'BUILD_V007';destination.mkdir(exist_ok=True)
    parts=[]
    with archive.open('rb') as f:
        i=0
        while data:=f.read(262144):
            p=destination/f'overlay.zip.part{i:02d}';p.write_bytes(data)
            parts.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=len(data),sha256=sha(data),git_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()));i+=1
    manifest=dict(base_commit='74d00718cf466d8a30cd30a088ef839b80a63303',base_input_manifest_unchanged=True,
                  archive_bytes=archive.stat().st_size,archive_sha256=sha(archive.read_bytes()),parts=parts,
                  files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files])
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(overlay_bytes=manifest['archive_bytes'],parts=len(parts),files=len(files)),indent=2))

if __name__=='__main__':main()
