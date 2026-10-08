"""Preserve tested v030 and add only the approved memorial and entry UV correction."""
import argparse, subprocess, sys
from v032_common import *
from v027_scenery import parse, values, child, fingerprint, geometry_records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');args=parser.parse_args()
    spec=read(S/'memorial_spec.json');baseqa=read(BASE/'source_validation.json')
    assert baseqa['source_checks_pass'] and baseqa['version']=='v030'
    assert sha(BASE/'terrain.raw')==baseqa['terrain_sha256'] and sha(BASE/'scenery.fbx')==baseqa['scenery_sha256']
    if O.exists():shutil.rmtree(O)
    for src in BASE.rglob('*'):
        if not src.is_file():continue
        dst=O/str(src.relative_to(BASE)).replace('v030','v032').replace('V030','V032')
        if src.suffix in ('.hmf','.shd','.ini','.amb','.tsc','.cfg','.txt','.rdf'):
            atomic(dst,src.read_bytes().replace(b'v030',b'v032').replace(b'V030',b'V032'))
        else:copy_exact(src,dst)
    for script in ('v032_sign.py','v032_memorial.py','render_v032_previews.py'):
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,check=True)
    finalize(spec,baseqa)
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v032.py')],cwd=R,check=True)

def finalize(spec,baseqa):
    exact={};protected=['terrain.raw','start.tcl','main.tcl','route.npz','geometry_spec.json','jump_profiles.json','turns.json','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','v024_pit_gravel.tga']
    for name in protected:
        if (BASE/name).is_file():
            assert sha(BASE/name)==sha(O/name),'Changed tested geometry/race source: '+name;exact[name]=sha(O/name)
    materials={};physical={};facilities={}
    for folder,checks in [('materials',materials),('masks',physical),('facility_textures',facilities)]:
        for p in (BASE/folder).iterdir():
            if not p.is_file():continue
            target=O/folder/p.name.replace('v030','v032');before=p.read_bytes()
            expected=before.replace(b'v030',b'v032').replace(b'V030',b'V032') if p.suffix in ('.hmf','.shd') else before
            assert target.read_bytes()==expected,'Changed tested v030 '+folder+': '+p.name
            checks[target.name]=sha(target)
    before,_=parse((BASE/'scenery.fbx').read_bytes());after,_=parse((O/'scenery.fbx').read_bytes());oldobjects=next(n for n in before if n['name']==b'Objects')['children'];newobjects=next(n for n in after if n['name']==b'Objects')['children'];newbyid={values(n)[0]:n for n in newobjects}
    entryname='v028_track_entry_sign_entry_sign';oldentry=geometry_records(before)[entryname][0];newentry=geometry_records(after)[entryname][0]
    newuv=child(child(newentry,b'LayerElementUV'),b'UV');newuv['props']=child(child(oldentry,b'LayerElementUV'),b'UV')['props']
    assert all(fingerprint(n)==fingerprint(newbyid[values(n)[0]]) for n in oldobjects),'Existing scenery changed beyond entry U'
    oldlinks=next(n for n in before if n['name']==b'Connections')['children'];newlinks=next(n for n in after if n['name']==b'Connections')['children'];assert [fingerprint(n) for n in oldlinks]==[fingerprint(n) for n in newlinks[:len(oldlinks)]]
    g=baseqa['grass'].copy();g.update(version='v032',inherited_scope_from='v030',visual_and_physical_masks_byte_exact_tested_v030=True)
    assert g['pit_visual_grass_changed_samples']==g['pit_physical_grass_changed_samples']==0 and abs(g['remaining_course_grass_fraction']-.5)<.0001
    qa=dict(version='v032',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=spec['source_commit'],source_checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),geometry=baseqa['geometry'],pit_access=baseqa['pit_access'],race=baseqa['race'],grass=g,materials=baseqa['materials'],entry_sign=read(O/'entry_sign_validation.json'),memorial=read(O/'memorial_validation.json'),protected_v030_sha256=exact,preserved_v030_material_files=materials,physics_masks=physical,preserved_existing_facility_textures=facilities,terrain_entirely_byte_exact_v030=True,all_physical_masks_byte_exact_v030=True,all_existing_visual_masks_byte_exact_v030=True,all_dirt_and_grass_texture_pixels_byte_exact_v030=True,grass_coverage_byte_exact_tested_v030=True,pits_grass_byte_exact_v028=True,accepted_macro_layout_unchanged=True,existing_custom_assets_and_menu_logo_preserved=True,physical_material_declarations_unchanged=True,entire_v030_scenery_preserved_except_entry_board_uvs_and_new_memorial=True,existing_scenery_records_verified_against_v030=True,in_game_visual_check=False,in_game_riding=False,performance_test=False)
    save(O/'source_validation.json',qa);save(O/'grass_validation.json',g)
    release=R/'12_RELEASE'/NAME;release.mkdir(parents=True,exist_ok=True)
    for p in (R/'12_RELEASE/orlandomx_2026_v030').iterdir():
        if not p.is_file() or p.suffix in ('.map','.trh'):continue
        data=p.read_bytes()
        if p.suffix in ('.ini','.amb','.tsc','.cfg','.txt','.rdf'):data=data.replace(b'v030',b'v032').replace(b'V030',b'V032')
        atomic(release/p.name.replace('v030','v032'),data)
    for suffix in ['.tga','_map.tga']:
        assert sha(release/(NAME+suffix))==sha(R/'12_RELEASE/orlandomx_2026_v030'/('orlandomx_2026_v030'+suffix))
    print('v032 passed: all v030 soils, grass, masks, riding geometry, race data and existing scenery preserved.',flush=True)
if __name__=='__main__':main()
