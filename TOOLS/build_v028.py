"""Build v028 from the byte-verified accepted source, never from stale output."""
import argparse,os,shutil,subprocess,sys
from v028_common import *
from v028_release import copy_release_inputs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');a=ap.parse_args()
    base=R/'V026_OUTPUT';tested=R/'V027_OUTPUT'
    assert sha(tested/'terrain.raw')=='8e492abfbae7a6c7ec8c48ff956d28027310c21275b4e3f256d366a60edc0c35','Checkpoint differs from tested v027 terrain'
    baseline=read(base/'baseline_validation.json');assert baseline['checks_pass']
    for fn,digest in baseline['actual_source_sha256'].items():assert sha(base/fn)==digest,'Baseline checkpoint changed: '+fn
    for fn in ['terrain.raw','start.tcl']:assert sha(base/fn)==EXPECTED[fn]
    if O.exists():shutil.rmtree(O)
    shutil.copytree(base,O);release=copy_release_inputs()
    # Apply the independently verified v026b/T09 removals to the exact base.
    import v027_scenery as prior
    prior.O=O;prior.main()
    protected=['route.npz','start.tcl','main.tcl','turns.json','geometry_spec.json','jump_profiles.json']
    for script in ['v028_surfaces.py','v028_scenery.py','v028_materials.py','v028_facilities.py','render_v028_previews.py']:
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    before={fn:sha(tested/fn) for fn in protected}
    for fn,digest in before.items():assert sha(O/fn)==digest,'Accepted route/profile changed: '+fn
    for p in (base/'facility_textures').iterdir():assert sha(O/'facility_textures'/p.name)==sha(p),'Accepted custom/facility texture changed'
    for fn in ['racing.tga','start.tga','shoulder.tga','worked.tga']:
        assert sha(base/'masks'/fn)==sha(O/'masks'/fn),'Accepted main/start physical coverage changed: '+fn
    import v028_scenery as access
    nodes,_=access.parse((O/'scenery.fbx').read_bytes());hits,audit=access.scan(nodes)
    assert not hits,'Complete retained + new low geometry intrudes on access: '+repr(hits)
    qa=dict(version='v028',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit='dfe6770649ce150356389cb2d78d55964d5358fe',source_checks_pass=True,
        tested_v027_terrain_sha256=sha(tested/'terrain.raw'),accepted_baseline_sha256=EXPECTED,baseline_validation=baseline,
        protected_route_profile_sha256=before,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
        carried_v026b_fix=read(R/'DOCUMENTATION/v027_scenery_validation.json'),retained_access_clearance=read(O/'retained_access_clearance_validation.json'),
        complete_access_audit=dict(models=len(audit),remaining_conflicts=hits,maximum_triangle_edge_m=.5,rider_headroom_m=3.2,lateral_margin_m=.65),
        geometry=read(O/'surface_geometry_validation.json'),materials=read(O/'material_validation.json'),pit_access=read(O/'pit_access_validation.json'),physics_masks=read(O/'surface_physics_validation.json'),
        race=read(base/'source_validation.json')['race'],release=release,accepted_macro_layout_unchanged=True,existing_custom_assets_and_menu_logo_preserved=True,
        physical_material_declarations_unchanged=True,in_game_riding=False,in_game_visual_check=False,performance_test=False)
    save(O/'source_validation.json',qa);print('v028 full source and complete access clearance validation passed',flush=True)
    if not a.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v028.py')],cwd=R,check=True)

if __name__=='__main__':main()
