"""Build a separate v025 visual candidate from the exact v024 source pipeline."""
from pathlib import Path
import argparse, subprocess, sys, json, shutil, hashlib, os, platform

R=Path(__file__).resolve().parents[1]
O=R/'V025_OUTPUT';OLD='orlandomx_2026_v024';NAME='orlandomx_2026_v025'
EXPECTED={
    'terrain.raw':'4befe79d6820865f4aba34649a5b54ed22472e7a3c1e7f8d3d56f53f3e340d91',
    'scenery.fbx':'98dc23a52fc9868a155d47368e10ff5645727033fc98b649cfb9d264cf9cdd90',
    'start.tcl':'b1dcaa07fe6e7a95eb1acfc40af00139ce00850e9df1133b894e3d0c3be2b0df',
    OLD+'.rdf':'522cc2a4f0ff142969b01c9fcfdd900dc908d12387fcc5b978fd5d78b85ec6f5'
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true')
    ap.add_argument('--reuse-baseline',action='store_true');args=ap.parse_args()
    if not args.reuse_baseline:
        subprocess.run([sys.executable,str(R/'TOOLS/build_v024.py'),'--source-only'],cwd=R,check=True)
    old=R/'V024_OUTPUT'
    O.mkdir(exist_ok=True)
    # Capture export evidence before enforcing the immutable-baseline gate.
    # This is diagnostic only: a mismatched FBX is still never compiled.
    exports={fn:dict(expected_sha256=h,actual_sha256=sha(old/fn),unchanged=sha(old/fn)==h) for fn,h in EXPECTED.items()}
    np=__import__('numpy')
    evidence=dict(checks_pass=all(x['unchanged'] for x in exports.values()),
        exports=exports,python=sys.version,platform=platform.platform(),
        numpy=np.__version__,numpy_cpu_features=np._core._multiarray_umath.__cpu_features__)
    (O/'baseline_export_validation.json').write_text(json.dumps(evidence,indent=2)+'\n')
    for fn,h in EXPECTED.items():
        assert sha(old/fn)==h,'v024 regenerated baseline differs: '+fn
    copyfiles=['terrain.raw','scenery.fbx','start.tcl','route.npz','jump_profiles.json','native_coordinate_probes.json','v024_pit_gravel.tga']
    for fn in copyfiles:shutil.copy2(old/fn,O/fn)
    for folder in ['facility_textures','masks']:
        shutil.copytree(old/folder,O/folder,dirs_exist_ok=True)
    dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    before={}
    for p in (R/'12_RELEASE'/OLD).iterdir():
        if not p.is_file() or p.suffix in ['.map','.trh']:continue
        target=dest/p.name.replace(OLD,NAME);shutil.copy2(p,target)
        if p.suffix=='.ini':
            target.write_text(target.read_text().replace('Orlando MX 2026 v024','Orlando MX 2026 v025').replace(OLD,NAME))
        else:assert sha(p)==sha(target),'Nonvisual release payload changed'
        before[p.name]=sha(p)
    subprocess.run([sys.executable,str(R/'TOOLS/v025_materials.py')],cwd=R,check=True)
    protected={}
    for fn in copyfiles:protected[fn]=dict(baseline_sha256=sha(old/fn),v025_sha256=sha(O/fn),unchanged=sha(old/fn)==sha(O/fn))
    for p in (old/'masks').glob('*.tga'):
        protected['masks/'+p.name]=dict(baseline_sha256=sha(p),v025_sha256=sha(O/'masks'/p.name),unchanged=sha(p)==sha(O/'masks'/p.name))
    for p in (old/'facility_textures').glob('*.tga'):
        assert sha(p)==sha(O/'facility_textures'/p.name),'Accepted object graphic changed'
    assert all(x['unchanged'] for x in protected.values())
    result=dict(version='v025',source_commit=os.environ.get('GITHUB_SHA','local'),
        baseline_commit='d70efa2d1da5cec4ed93182a4efb762028b991b6',
        source_checks_pass=True,protected=protected,baseline_release_hashes=before,
        geometry_unchanged=True,physics_unchanged=True,scenery_unchanged=True,
        native_compilation=False,in_game_riding_test=False,performance_test=False)
    (O/'source_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('v025 visual source ready; exact v024 terrain, start, scenery and physics protected',flush=True)
    if not args.source_only:
        subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v025.py')],cwd=R,check=True)
if __name__=='__main__':main()
