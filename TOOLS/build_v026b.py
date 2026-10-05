"""Separate v026b hotfix candidate built from the completed v026 source.

v026b changes scenery only: route-intruding tree/marker objects in the localized
R10/T09/R11 sector are removed. Geometry, masks, materials, race/reset data,
pits, start and unrelated scenery are protected.
"""
from pathlib import Path
import argparse, subprocess, sys, os, shutil, json, hashlib

R=Path(__file__).resolve().parents[1]
BASE=R/'V026_OUTPUT'
O=R/'V026B_OUTPUT'
NAME='orlandomx_2026_v026b'
BASE_NAME='orlandomx_2026_v026'
BASE_COMMIT='2275efa8e92a4958ea130acd71bc6ea74ed49591'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def same_tree(a,b):
    af={str(p.relative_to(a)):sha(p) for p in Path(a).rglob('*') if p.is_file()}
    bf={str(p.relative_to(b)):sha(p) for p in Path(b).rglob('*') if p.is_file()}
    return af==bf,af,bf

def copy_release_inputs():
    src=R/'12_RELEASE'/BASE_NAME
    dst=R/'12_RELEASE'/NAME
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    text_suffixes={'.rdf','.ini','.amb','.tsc','.cfg','.txt'}
    for p in src.iterdir():
        if not p.is_file():
            continue
        newname=p.name.replace(BASE_NAME,NAME).replace('v026','v026b').replace('V026','V026B')
        target=dst/newname
        if p.suffix.lower() in text_suffixes:
            try:
                text=p.read_text(encoding='utf-8')
                text=text.replace(BASE_NAME,NAME).replace('Orlando MX 2026 v026','Orlando MX 2026 v026b').replace('v026','v026b').replace('V026','V026B')
                target.write_text(text,encoding='utf-8')
                continue
            except UnicodeDecodeError:
                pass
        shutil.copy2(p,target)
    required=[NAME+'.rdf',NAME+'.ini',NAME+'.amb',NAME+'.tsc',NAME+'.tga',NAME+'_map.tga',
              'minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']
    missing=[x for x in required if not (dst/x).is_file()]
    if missing:
        raise RuntimeError('Missing v026b release source files: '+repr(missing))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-only',action='store_true')
    args=ap.parse_args()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')

    # Regenerate the exact accepted v026 source first.
    subprocess.run([sys.executable,str(R/'TOOLS/build_v026.py'),'--source-only'],cwd=R,env=env,check=True)

    if O.exists():
        shutil.rmtree(O)
    shutil.copytree(BASE,O)
    copy_release_inputs()

    # Snapshot hashes before the scenery-only edit.
    protected_files=['terrain.raw','start.tcl','main.tcl','route.npz','geometry_spec.json','turns.json','jump_profiles.json']
    before={fn:sha(BASE/fn) for fn in protected_files}
    mask_ok,base_masks,_=same_tree(BASE/'masks',O/'masks')
    mat_ok,base_materials,_=same_tree(BASE/'materials',O/'materials')
    fac_ok,base_facilities,_=same_tree(BASE/'facility_textures',O/'facility_textures')
    if not (mask_ok and mat_ok and fac_ok):
        raise RuntimeError('v026b copy did not preserve v026 visual inputs before scenery hotfix')

    subprocess.run([sys.executable,str(R/'TOOLS/v026b_scenery.py')],cwd=R,env=env,check=True)

    for fn,h in before.items():
        if sha(O/fn)!=h:
            raise RuntimeError('Protected v026 source changed in v026b: '+fn)
    mask_ok,_,after_masks=same_tree(BASE/'masks',O/'masks')
    mat_ok,_,after_materials=same_tree(BASE/'materials',O/'materials')
    fac_ok,_,after_facilities=same_tree(BASE/'facility_textures',O/'facility_textures')
    if not (mask_ok and mat_ok and fac_ok):
        raise RuntimeError('v026b changed masks/materials/facility textures unexpectedly')

    baseqa=read(BASE/'source_validation.json')
    scenery=read(R/'DOCUMENTATION/v026b_scenery_validation.json')
    qa=dict(
        version='v026b',
        source_checks_pass=True,
        source_commit=os.environ.get('GITHUB_SHA','local'),
        baseline_commit=BASE_COMMIT,
        baseline_version='v026',
        geometry=baseqa['geometry'],
        materials=baseqa['materials'],
        race=baseqa['race'],
        scenery=scenery,
        terrain_sha256=sha(O/'terrain.raw'),
        v026_terrain_sha256=sha(BASE/'terrain.raw'),
        route_sha256=sha(O/'route.npz'),
        v026_route_sha256=sha(BASE/'route.npz'),
        masks_exact_v026=mask_ok,
        materials_exact_v026=mat_ok,
        facility_textures_exact_v026=fac_ok,
        start_exact_v026=sha(O/'start.tcl')==sha(BASE/'start.tcl'),
        main_centerline_exact_v026=sha(O/'main.tcl')==sha(BASE/'main.tcl'),
        scenery_changed_only=True,
        traction_material_declarations_unchanged=True,
        in_game_riding=False,
        in_game_visual_check=False,
        performance_test=False,
    )
    (O/'source_validation.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
    print('v026b source ready: v026 geometry/materials protected; localized scenery obstructions removed.',flush=True)

    if not args.source_only:
        subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v026b.py')],cwd=R,env=env,check=True)

if __name__=='__main__':
    main()
