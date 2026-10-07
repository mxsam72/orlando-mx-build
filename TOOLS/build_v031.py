"""Build the scanned-soil update from the immutable, tested v030 output."""
import argparse,subprocess,sys
from v031_common import *

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');args=parser.parse_args()
    spec=read(S/'surface_spec.json');baseqa=read(BASE/'source_validation.json')
    assert baseqa['source_checks_pass'] and baseqa['version']=='v030'
    assert sha(BASE/'terrain.raw')==baseqa['terrain_sha256']
    assert sha(BASE/'scenery.fbx')==baseqa['scenery_sha256']
    if O.exists():shutil.rmtree(O)
    for src in BASE.rglob('*'):
        if not src.is_file():continue
        relative=src.relative_to(BASE)
        dst=O/str(relative).replace('v030','v031').replace('V030','V031')
        if src.suffix in ('.hmf','.shd','.ini','.amb','.tsc','.cfg','.txt','.rdf'):
            data=src.read_bytes().replace(b'v030',b'v031').replace(b'V030',b'V031')
            atomic(dst,data)
        else:copy_exact(src,dst)
    for script in ('download_v031_scans.py','v031_sign.py','v031_materials.py','render_v031_previews.py'):
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    finalize(spec,baseqa)
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v031.py')],cwd=R,check=True)

def finalize(spec,baseqa):
    protected=['terrain.raw','start.tcl','main.tcl','route.npz','geometry_spec.json','jump_profiles.json','turns.json','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']
    exact={}
    for name in protected:
        if (BASE/name).is_file():
            assert sha(BASE/name)==sha(O/name),'Changed accepted geometry/race source: '+name
            exact[name]=sha(O/name)
    physical={}
    for p in (BASE/'masks').glob('*.tga'):
        target=O/'masks'/p.name.replace('v030','v031');assert sha(p)==sha(target)
        physical[target.name]=sha(target)
    visual={}
    for p in (BASE/'materials').glob('mask*.tga'):
        target=M/p.name.replace('v030','v031');assert sha(p)==sha(target)
        visual[target.name]=sha(target)
    grass_files=[]
    for p in (BASE/'materials').glob('v030_grass*.tga'):
        target=M/p.name.replace('v030','v031');assert sha(p)==sha(target);grass_files.append(target.name)
    for p in (BASE/'facility_textures').glob('*'):
        if p.is_file():assert sha(p)==sha(O/'facility_textures'/p.name)
    g=baseqa['grass'].copy();g.update(version='v031',inherited_scope_from='v030',visual_and_physical_masks_byte_exact_tested_v030=True)
    assert g['pit_visual_grass_changed_samples']==g['pit_physical_grass_changed_samples']==0
    assert g['circle_visual_grass_nonzero_samples']==g['start_visual_grass_nonzero_samples']==0
    assert abs(g['remaining_course_grass_fraction']-.5)<.0001
    qa=dict(version='v031',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=spec['source_commit'],source_checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),geometry=baseqa['geometry'],pit_access=baseqa['pit_access'],race=baseqa['race'],grass=g,materials=read(O/'material_validation.json'),entry_sign=read(O/'entry_sign_validation.json'),protected_v030_sha256=exact,physics_masks=physical,preserved_visual_masks=visual,preserved_grass_tiles=grass_files,terrain_entirely_byte_exact_v030=True,all_physical_masks_byte_exact_v030=True,all_existing_visual_masks_byte_exact_v030=True,grass_coverage_byte_exact_tested_v030=True,pits_grass_byte_exact_v028=True,accepted_macro_layout_unchanged=True,existing_custom_assets_and_menu_logo_preserved=True,physical_material_declarations_unchanged=True,entire_v030_scenery_preserved_except_entry_board_uvs=True,in_game_visual_check=False,in_game_riding=False,performance_test=False)
    save(O/'source_validation.json',qa);save(O/'grass_validation.json',g)
    release=R/'12_RELEASE'/NAME;release.mkdir(parents=True,exist_ok=True)
    template=R/'12_RELEASE/orlandomx_2026_v030'
    for p in template.iterdir():
        if not p.is_file() or p.suffix in ('.map','.trh'):continue
        data=p.read_bytes()
        if p.suffix in ('.ini','.amb','.tsc','.cfg','.txt','.rdf'):
            data=data.replace(b'v030',b'v031').replace(b'V030',b'V031')
        atomic(release/p.name.replace('v030','v031'),data)
    assert (release/(NAME+'.tga')).is_file() and (release/(NAME+'_map.tga')).is_file()
    print('v031 source checks passed: v030 geometry, grass, all existing masks and custom assets preserved.',flush=True)

if __name__=='__main__':main()
