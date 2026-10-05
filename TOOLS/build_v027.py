"""Build v027 from a byte-verified v026 checkpoint, with isolated new output."""
import argparse, os, shutil, subprocess, sys
from v027_common import *
from v027_release import copy_release_inputs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');ap.add_argument('--reuse-baseline',action='store_true');a=ap.parse_args()
    base=R/'V026_OUTPUT'
    if not a.reuse_baseline:
        subprocess.run([sys.executable,str(R/'TOOLS/v027_restore_baseline.py')],cwd=R,check=True)
    baseline=read(base/'baseline_validation.json');assert baseline['checks_pass']
    for fn,digest in baseline['actual_source_sha256'].items():assert sha(base/fn)==digest,'Verified v026 checkpoint differs: '+fn
    for fn in ['terrain.raw','start.tcl']:assert sha(base/fn)==EXPECTED[fn]
    assert read(base/'source_validation.json')['source_checks_pass']
    # Native staging needs the old baseline's tool configuration and base maps;
    # restore those without regenerating its already accepted FBX geometry.
    if not (R/'BUILD/v009_work/BUILD/track.hmf').is_file():
        subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    if O.exists():shutil.rmtree(O)
    shutil.copytree(base,O);release=copy_release_inputs()
    protected=['route.npz','start.tcl','main.tcl','turns.json','geometry_spec.json','jump_profiles.json']
    before={fn:sha(base/fn) for fn in protected}
    for script in ['v027_scenery.py','v027_surfaces.py','v027_materials.py','v027_facilities.py','render_v027_previews.py']:
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    for fn,digest in before.items():assert sha(O/fn)==digest,'Protected route/profile changed: '+fn
    for p in (base/'facility_textures').iterdir():assert sha(O/'facility_textures'/p.name)==sha(p),'Existing facility texture changed'
    for fn in ['racing.tga','start.tga','shoulder.tga','worked.tga']:
        assert sha(base/'masks'/fn)==sha(O/'masks'/fn),'Existing main/start physical coverage changed: '+fn
    qa=dict(version='v027',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit='2275efa8e92a4958ea130acd71bc6ea74ed49591',
            source_checks_pass=True,accepted_baseline_sha256=EXPECTED,baseline_validation=baseline,protected_route_profile_sha256=before,
            terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
            scenery_fix=read(R/'DOCUMENTATION/v027_scenery_validation.json'),
            geometry=read(O/'surface_geometry_validation.json'),materials=read(O/'material_validation.json'),
            pit_access=read(O/'pit_access_validation.json'),physics_masks=read(O/'surface_physics_validation.json'),
            race=read(base/'source_validation.json')['race'],release=release,
            accepted_macro_layout_unchanged=True,existing_custom_assets_and_menu_logo_preserved=True,
            physical_material_declarations_unchanged=True,in_game_riding=False,in_game_visual_check=False,performance_test=False)
    save(O/'source_validation.json',qa); print('v027 full source validation passed',flush=True)
    if not a.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v027.py')],cwd=R,check=True)
if __name__=='__main__':main()
