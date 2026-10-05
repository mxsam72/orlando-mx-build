"""Separate v026 candidate; accepted baseline inputs never get edited."""
from pathlib import Path
import argparse, subprocess, sys, os, shutil, json, hashlib
R=Path(__file__).resolve().parents[1];O=R/'V026_OUTPUT';NAME='orlandomx_2026_v026'
EXPECTED={'terrain.raw':'4befe79d6820865f4aba34649a5b54ed22472e7a3c1e7f8d3d56f53f3e340d91','scenery.fbx':'98dc23a52fc9868a155d47368e10ff5645727033fc98b649cfb9d264cf9cdd90','start.tcl':'b1dcaa07fe6e7a95eb1acfc40af00139ce00850e9df1133b894e3d0c3be2b0df'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');ap.add_argument('--reuse-baseline',action='store_true');a=ap.parse_args();O.mkdir(exist_ok=True)
    if not a.reuse_baseline:
        # Same accepted v024 builder, omitting only informational render jobs.
        code=(R/'TOOLS/build_v024.py').read_text(encoding='utf-8')
        for script in ['render_facilities_v024.py','render_v024_layout.py','render_vehicles_v024.py']:
            code=code.replace("'"+script+"',",'')
        ns={'__name__':'v026_baseline','__file__':str(R/'TOOLS/build_v024.py')};exec(compile(code,str(R/'TOOLS/build_v024.py'),'exec'),ns,ns)
        argv=sys.argv;sys.argv=['build_v024.py','--source-only']
        try:ns['main']()
        finally:sys.argv=argv
    old=R/'V024_OUTPUT';protected={}
    for fn,h in EXPECTED.items():
        if a.reuse_baseline and not (old/fn).exists():continue
        assert sha(old/fn)==h,'Accepted baseline changed: '+fn
        protected[fn]=h
    for fn in ['scenery.fbx','start.tcl','native_coordinate_probes.json','v024_pit_gravel.tga']:
        if (old/fn).exists():shutil.copy2(old/fn,O/fn)
    for folder in ['masks','facility_textures']:
        if (old/folder).exists():shutil.copytree(old/folder,O/folder,dirs_exist_ok=True)
    for script in ['v026_geometry.py','v026_materials.py','v026_race.py']:
        print('RUN',script,flush=True);subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    for fn in ['scenery.fbx','start.tcl','v024_pit_gravel.tga']:
        if (O/fn).exists():assert sha(O/fn)==sha(old/fn),'Protected source changed: '+fn
    for p in (old/'facility_textures').glob('*.tga'):assert sha(p)==sha(O/'facility_textures'/p.name)
    complete=set(protected)==set(EXPECTED)
    qa=dict(version='v026',source_checks_pass=True,source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit='6cadfbb7fb9301b3a24ec5c8ce7b0ee545cd19ec',protected_baseline_sha256=protected,protected_baseline_checks_complete=complete,geometry=json.loads((O/'geometry_validation.json').read_text()),materials=json.loads((O/'material_validation.json').read_text()),race=json.loads((O/'race_validation.json').read_text()),scenery_source_exact=True if complete else None,traction_material_declarations_unchanged=True,in_game_riding=False,in_game_visual_check=False,performance_test=False)
    (O/'source_validation.json').write_text(json.dumps(qa,indent=2)+'\n');print('v026 source ready: localized geometry and new neutral materials',flush=True)
    if not a.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v026.py')],cwd=R,check=True)
if __name__=='__main__':main()
