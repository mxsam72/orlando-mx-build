#!/usr/bin/env python3
"""Apply Orlando MX v008 visual overlay on top of restored v007 native inputs.
Does not modify v007 geometry or physics masks.
"""
from pathlib import Path
import hashlib, json, shutil, sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'V008_VISUAL_OVERLAY'
MANIFEST = ROOT / 'BUILD_V008' / 'manifest.json'
BASE = ROOT / '12_RELEASE' / 'orlandomx_2026_v007'
DEST = ROOT / '12_RELEASE' / 'orlandomx_2026_v008'
EXPECTED_V007_TERRAIN = '4a8a569a1cc37db2ed10a61d83b71f4821b005a5f188ed7b3f590be55017e57d'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def die(msg):
    raise RuntimeError(msg)

def main():
    if not MANIFEST.is_file():
        die('Missing BUILD_V008/manifest.json. Extract OrlandoMX_v008_Visual_Update_Source.zip into the repository root first.')
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    import io, zipfile
    chunks=[]
    for item in manifest['parts']:
        p=ROOT/item['path']
        if p.stat().st_size != item['bytes'] or sha(p) != item['sha256']: die('Visual archive part mismatch')
        chunks.append(p.read_bytes())
    data=b''.join(chunks)
    if len(data)!=manifest['archive_bytes'] or hashlib.sha256(data).hexdigest()!=manifest['archive_sha256']: die('Visual archive mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if set(z.namelist())!={f['path'] for f in manifest['files']}: die('Visual archive members mismatch')
        for name in z.namelist():
            target=(SOURCE/name).resolve()
            if not target.is_relative_to(SOURCE.resolve()): die('Unsafe visual archive path')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(name))
    if not SOURCE.is_dir():
        die('Missing V008_VISUAL_OVERLAY folder. Extract OrlandoMX_v008_Visual_Update_Source.zip into the repository root first.')
    if not BASE.is_dir():
        die('Missing restored v007 release inputs. Run TOOLS/unpack_inputs.py first.')
    terrain=ROOT/'02_HEIGHTMAP/terrain.raw'
    if not terrain.is_file() or sha(terrain) != EXPECTED_V007_TERRAIN:
        die('The restored terrain is not the exact playable v007 terrain. Aborting rather than risking the base build.')

    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('base_commit') != '72a1b67e3d6a89b71244ec27fbed68e149fdfc2a':
        die('BUILD_V008 manifest does not target the known stable v007 commit.')

    # Verify every direct overlay file against the generated manifest, then copy it
    # into the repository root. This overwrites visual assets/HMF only.
    copied=[]
    for item in manifest['files']:
        rel=Path(item['path'])
        src=SOURCE/rel
        if not src.is_file():
            die(f'Missing v008 overlay file: {src}')
        if src.stat().st_size != item['bytes'] or sha(src) != item['sha256']:
            die(f'v008 overlay integrity check failed: {rel.as_posix()}')
        dst=ROOT/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        copied.append(rel.as_posix())

    # Create a distinct v008 release support folder from the known-good v007 files.
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(BASE,DEST)

    # Never carry compiled v007 geometry/collision forward. Native tools must create
    # fresh v008 MAP/TRH files during this build.
    for p in DEST.glob('*.map'):
        p.unlink()
    for p in DEST.glob('*.trh'):
        p.unlink()

    old='orlandomx_2026_v007'
    new='orlandomx_2026_v008'
    for p in list(DEST.iterdir()):
        if p.is_file() and p.name.startswith(old):
            p.rename(DEST/(new+p.name[len(old):]))

    ini=DEST/(new+'.ini')
    if not ini.is_file():
        die('v008 .ini preparation failed')
    text=ini.read_text(encoding='utf-8')
    text=text.replace('name=Orlando MX 2026 v007','name=Orlando MX 2026 v008')
    text=text.replace('orlandomx_2026_v007.tga','orlandomx_2026_v008.tga')
    text=text.replace('orlandomx_2026_v007_map.tga','orlandomx_2026_v008_map.tga')
    ini.write_text(text,encoding='utf-8')

    # Safety check: the physics definition stays the v007 one. HMF may use visual masks.
    tht=(ROOT/'BUILD/track.tht').read_text(encoding='utf-8')
    if 'mask_visual_' in tht:
        die('track.tht references a visual-only mask. Physics masks must remain v007.')
    hmf=(ROOT/'BUILD/track.hmf').read_text(encoding='utf-8')
    for required in ['mask_visual_racing.tga','mask_visual_worked.tga','mask_visual_grass.tga']:
        if required not in hmf:
            die('v008 HMF is missing expected visual mask: '+required)

    print(f'Applied and verified {len(copied)} v008 visual-overlay files.')
    print('Prepared separate release folder:',DEST)
    print('v007 terrain and physics masks remain unchanged.')

if __name__=='__main__':
    main()
