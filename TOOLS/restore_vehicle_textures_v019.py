"""Restore hash-pinned PNGs from the repository asset archive, no external paths."""
import base64,zlib
from v019_common import *

def main():
    archive=read(S/'vehicle_textures_packed.json');materials=read(S/'vehicle_materials.json')
    for name,entry in archive.items():
        p=S/'vehicle_textures'/name;assert p.parent==S/'vehicle_textures' and p.suffix=='.png';p.parent.mkdir(exist_ok=True);p.write_bytes(zlib.decompress(base64.b64decode(entry['data'])));assert sha(p)==entry['sha256']
    for m in materials.values():assert sha(S/m['file'])==m['sha256']
    print('Restored',len(archive),'hash-pinned vehicle textures')
if __name__=='__main__':main()
