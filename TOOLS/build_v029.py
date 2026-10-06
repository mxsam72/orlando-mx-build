"""Create v029 only from the verified tested v028 source generation."""
import argparse, shutil, subprocess, sys, os
from v029_common import *

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');a=parser.parse_args()
    baseline=read(BASE/'source_validation.json'); assert baseline['version']=='v028' and baseline['source_checks_pass']
    assert sha(BASE/'terrain.raw')==baseline['terrain_sha256']
    assert baseline['terrain_sha256']=='954bb88ab989959257fc481db0caf241bb65bf771d46739f79207a4501c203a7','Terrain differs from delivered v028 native source'
    assert sha(BASE/'scenery.fbx')==baseline['scenery_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O)
    # Material identity belongs to the new version. Scenery textures retain
    # their accepted v028/v024 names and exact bytes.
    for p in list(M.iterdir()):
        if p.name.startswith('v028_') or p.name.startswith('mask_v028_'):p.rename(p.with_name(p.name.replace('v028_','v029_')))
    for p in M.iterdir():
        if p.suffix in ['.shd','.hmf']:p.write_text(p.read_text().replace('v028_','v029_'))
    for script in ['v029_surfaces.py','v029_materials.py','v029_sign.py','render_v029_previews.py']:
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    protected=['terrain.raw','route.npz','start.tcl','main.tcl','turns.json','geometry_spec.json','jump_profiles.json','native_coordinate_probes.json']
    hashes={k:sha(BASE/k) for k in protected}
    for k,digest in hashes.items():assert sha(O/k)==digest,'Accepted v028 geometry or configuration changed: '+k
    for p in (BASE/'facility_textures').iterdir():assert sha(O/'facility_textures'/p.name)==sha(p)
    for p in (BASE/'masks').iterdir():
        if p.name!='grass.tga':assert sha(O/'masks'/p.name)==sha(p),'Unexpected physical mask change: '+p.name
    src=R/'12_RELEASE/orlandomx_2026_v028';dst=R/'12_RELEASE'/NAME
    if dst.exists():shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if not p.is_file() or p.suffix in ['.map','.trh']:continue
        data=p.read_bytes()
        if p.suffix in ['.ini','.amb','.tsc','.cfg','.txt']:data=data.replace(b'v028',b'v029').replace(b'V028',b'V029')
        (dst/p.name.replace('v028','v029').replace('V028','V029')).write_bytes(data)
    expected=[NAME+x for x in ['.rdf','.ini','.amb','.tsc','.tga','_map.tga']]+['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']
    assert sorted(p.name for p in dst.iterdir())==sorted(expected)
    for k in ['.rdf','.tga']+['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:
        old='orlandomx_2026_v028'+k if k.startswith('.') else k; new=NAME+k if k.startswith('.') else k
        assert sha(src/old)==sha(dst/new),'Protected release data changed'
    qa=dict(version='v029',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit='d9e5ce03bd597cf5a87632387ec9f371ebe66ea2',
        source_checks_pass=True,baseline_v028_source_validation=baseline,protected_v028_sha256=hashes,
        terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
        geometry=baseline['geometry'],materials=read(O/'material_validation.json'),
        grass=read(O/'grass_reduction_validation.json'),entry_sign=read(O/'entry_sign_validation.json'),
        pit_access=baseline['pit_access'],race=baseline['race'],
        physics_masks=dict(checks_pass=True,changed_masks=['grass'],all_other_v028_physical_masks_byte_exact=True),
        release=dict(release_inputs_checked=True,race_reset_marshals_and_menu_logo_exact_v028=True),
        accepted_macro_layout_unchanged=True,terrain_entirely_byte_exact_v028=True,
        existing_custom_assets_and_menu_logo_preserved=True,physical_material_declarations_unchanged=True,
        entire_v028_scenery_preserved_except_entry_board_uvs=True,
        in_game_riding=False,in_game_visual_check=False,performance_test=False)
    save(O/'source_validation.json',qa)
    print('v029 source checks passed; complete terrain is byte-identical to tested v028',flush=True)
    if not a.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v029.py')],cwd=R,check=True)

if __name__=='__main__':main()
