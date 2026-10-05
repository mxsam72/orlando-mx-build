"""Read-only visual/material audit of the generated, validated v024 baseline."""
from pathlib import Path
import json, hashlib, shutil, re
import numpy as np
from PIL import Image

R = Path(__file__).resolve().parents[1]
W = R/'BUILD/v009_work'
A = R/'V025_AUDIT'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    A.mkdir(exist_ok=True)
    report = {'baseline_commit': 'd70efa2d1da5cec4ed93182a4efb762028b991b6',
              'textures': [], 'shaders': {}, 'configurations': {}, 'protected': {},
              'in_game_visual_check': False}
    for p in sorted((W/'04_TEXTURES').glob('*.tga')):
        im = Image.open(p).convert('RGB')
        if p.stem not in ['basemap','soil','soil_wet','prepared','prepared_wet','worked','worked_wet','grass','sand','sand_wet']:
            continue
        ar = np.asarray(im, dtype=np.float32)
        report['textures'].append({'name': p.name, 'size': list(im.size), 'bytes': p.stat().st_size,
            'sha256': sha(p), 'mean_rgb': ar.mean(axis=(0,1)).tolist(),
            'std_rgb': ar.std(axis=(0,1)).tolist()})
        dst = A/'textures'/p.with_suffix('.png').name; dst.parent.mkdir(exist_ok=True)
        im.resize((1024,1024), Image.Resampling.LANCZOS).save(dst)
    for p in sorted((W/'06_SHADERS').glob('*.shd')):
        report['shaders'][p.name] = p.read_text()
        dst = A/'shaders'/p.name; dst.parent.mkdir(exist_ok=True); shutil.copy2(p,dst)
    for name in ['track.hmf','track.tht','map_params.ini','trh_params.ini']:
        p = W/'BUILD'/name; report['configurations'][name] = p.read_text()
        shutil.copy2(p, A/name)
    for p in sorted((R/'V024_OUTPUT/masks').glob('*.tga')):
        dst = A/'masks'/p.with_suffix('.png').name; dst.parent.mkdir(exist_ok=True)
        Image.open(p).getchannel('A').save(dst)
    for name in ['terrain.raw','route.npz','jump_profiles.json','start.tcl','orlandomx_2026_v024.rdf']:
        p = R/'V024_OUTPUT'/name
        report['protected'][name] = sha(p)
        shutil.copy2(p,A/name)
    report['protected']['scenery.fbx'] = sha(R/'V024_OUTPUT/scenery.fbx')
    report['protected']['main.tcl'] = sha(W/'09_TRACKED/main.tcl')
    shutil.copy2(W/'09_TRACKED/main.tcl',A/'main.tcl')
    report['pit_texture'] = {'name':'v024_pit_gravel.tga','sha256':sha(R/'V024_OUTPUT/v024_pit_gravel.tga')}
    Image.open(R/'V024_OUTPUT/v024_pit_gravel.tga').save(A/'textures/v024_pit_gravel.png')
    report['heightmap'] = {'samples':2049,'size_m':600,'vertical_scale_m':18,'bytes':(A/'terrain.raw').stat().st_size}
    report['visual_physics_coupling'] = 'HMF visual stack and THT physical stack use distinct masks after the v008 pass. Preserve THT and every physical mask exactly.'
    (A/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Read-only v024 material audit ready:',A)

if __name__ == '__main__': main()
