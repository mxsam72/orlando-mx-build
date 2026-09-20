"""Stage only original generated native build inputs for the private CI repo."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    files=[ROOT/'02_HEIGHTMAP/terrain.raw',ROOT/'07_OBJECTS_SOURCE/scenery.fbx']
    for folder,pattern in [('03_MASKS','*.tga'),('04_TEXTURES','*.tga'),('05_NORMALS','*.tga'),('06_SHADERS','*.shd'),('09_TRACKED','*.tcl'),('BUILD','*.ini'),('BUILD','*.hmf'),('BUILD','*.tht')]:files+=sorted((ROOT/folder).glob(pattern))
    files += [ROOT/'BUILD/tool_versions.json',ROOT/'BUILD/native_coordinate_probes.json']
    files+=sorted((ROOT/'12_RELEASE/orlandomx_2026_v006').iterdir())
    files=[p for p in files if p.is_file() and p.suffix not in ['.map','.trh']]
    out=ROOT/'BUILD_INPUTS';out.mkdir(exist_ok=True);archive=ROOT/'BUILD/native_inputs.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    parts=[];chunk=1048576
    with archive.open('rb') as f:
        i=0
        while b:=f.read(chunk):
            p=out/f'native_inputs.zip.part{i:02d}';p.write_bytes(b)
            parts.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()));i+=1
    manifest=dict(archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),parts=parts,files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(files=len(files),archive_bytes=manifest['archive_bytes'],parts=len(parts),sha256=manifest['archive_sha256']),indent=2))
if __name__=='__main__':main()
