"""v022 source finalizer: allow only R07, R10 and T09 geometry changes from validated v021."""
import json
from PIL import Image
from v022_common import *

def normalized(value):
    return json.dumps(value,sort_keys=True).replace('v022','v021').replace('V022','V021')

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    # v022 intentionally changes terrain. All non-terrain protected native inputs
    # (start/race/material masks/pit textures) must remain byte-identical to the
    # validated chain. Scenery FBX is regenerated from the unchanged v021 assets.
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx') or rel.endswith('terrain.raw') or rel.endswith('masks/visual_racing.tga'):
            continue
        new=rel.replace('V018','V022').replace('v018','v022');p=R/new
        assert p.is_file(),('required protected input missing',new)
        got=sha(p);checks.append(dict(file=new,expected_sha256=digest,sha256=got,unchanged=got==digest))
    failed=[c['file'] for c in checks if not c['unchanged']]
    assert not failed,('protected non-terrain input changed',failed)

    assert read(S/'facilities.json')==read(R/'V021_SOURCE/facilities.json')
    assert read(S/'start_layout.json')==read(R/'V021_SOURCE/start_layout.json')
    assert normalized(read(S/'vehicles.json'))==json.dumps(read(R/'V021_SOURCE/vehicles.json'),sort_keys=True)
    assert normalized(read(S/'pit_facilities.json'))==json.dumps(read(R/'V021_SOURCE/pit_facilities.json'),sort_keys=True)

    now=read(S/'v022_geometry_spec.json');old=read(R/'V021_SOURCE/v021_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};po={p['id']:p for p in old['profiles']}
    bn={b['id']:b for b in now['berms']};bo={b['id']:b for b in old['berms']}
    assert set(pn)==set(po) and set(bn)==set(bo)
    for rid in pn:
        if rid not in ['R07','R10']:
            assert pn[rid]==po[rid],('unauthorized obstacle change',rid)
    for tid in bn:
        if tid!='T09':
            assert bn[tid]==bo[tid],('unauthorized berm change',tid)

    r07=pn['R07'];r10=pn['R10'];t09=bn['T09']
    assert (r07['station_start_m'],r07['station_end_m'],r07['lip_s'])==(539.0,566.0,552.0)
    assert (r07['face_m'],r07['crest_height_m'],r07['landing_m'])==(13.0,5.10,14.0)
    assert r07.get('face_style')=='progressive_lip' and r07['lower_face_grade_ratio']==0.45
    assert (r10['station_start_m'],r10['station_end_m'],r10['lip_s'])==(743.2,813.2,756.7)
    assert (r10['face_m'],r10['crest_height_m'],r10['lip_transition_m'],r10['deck_m'])==(13.5,4.55,0.90,27.1)
    assert (t09['outer_rise_m'],t09['effective_width_m'],t09['rut_depth_m'],t09['pocket_depth_m'])==(2.15,7.10,0.16,0.40)

    mats=read(S/'vehicle_materials.json')
    expected={
        'premier_wrap','premier_wrap_right','premier_tail',
        'ford_badge','king_ranch','four_by_four','chevy_badge',
        'jordan_number','premier_number','sam_number','shane_number',
        'jordan_shroud','premier_shroud','sam_shroud','shane_shroud'
    }
    actual={k for k,v in mats.items() if v.get('native_u_preflipped')}
    assert actual==expected
    assert not mats['bithlo_photo'].get('native_u_preflipped',False)
    for name,m in mats.items():
        im=Image.open(S/m['file'])
        assert im.width&(im.width-1)==0 and im.height&(im.height-1)==0,(name,im.size)
        assert sha(S/m['file'])==m['sha256']

    logo=read(R/'DOCUMENTATION/v022_menu_logo_validation.json')
    qa=read(R/'DOCUMENTATION/v022_vehicle_validation.json')
    graphics=read(R/'DOCUMENTATION/v022_graphics_validation.json')
    custom=read(R/'DOCUMENTATION/v022_user_request_validation.json')
    race=read(R/'DOCUMENTATION/v022_race_validation.json')
    geo=read(R/'DOCUMENTATION/v022_geometry_validation.json')
    release=read(R/'DOCUMENTATION/v022_release_validation.json')
    scenery=read(R/'DOCUMENTATION/v022_scenery_validation.json')
    assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    assert all([qa['checks_pass'],graphics['checks_pass'],custom['all_checks_pass'],
                race['race_source_checks_pass'],geo['geometry_checks_pass'],
                release['release_source_checks_pass'],scenery['vehicle_uv_roundtrip_pass']])
    assert sha(O/'terrain.raw')!=inv['raw_sha256'],'v022 terrain unexpectedly identical to v021/v018'

    release.update(
        version='v022',compared_to='validated v021',
        race_layout_preserved=True,start_layout_preserved=True,pit_layout_preserved=True,
        vehicle_placements_preserved=True,graphics_fix_preserved=True,bithlo_sign_preserved=True,
        authorized_geometry_changes=['R07 turn-exit mound/jump profile','R10 booter tabletop takeoff','T09 deep tree-side left berm','terrain-derived visual_racing mask'],
        all_other_profiles_preserved=True,all_other_berms_preserved=True,
        menu_logo_preserved=True,power_of_two_vehicle_textures=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v022_pit_gravel.tga',
        *sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),
        *sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles if p.exists()}
    save(R/'DOCUMENTATION/v022_release_validation.json',release)
    save(R/'DOCUMENTATION/v022_invariants_validation.json',dict(
        checks_pass=True,protected_nonterrain_inputs=checks,
        compared_to='v021',authorized_geometry_changes=['R07','R10','T09'],
        terrain_changed_intentionally=True,terrain_sha256=sha(O/'terrain.raw'),
        source_specs_other_than_geometry_match_v021=True,vehicle_placements_match_v021=True,
        pit_layout_matches_v021=True,graphics_fix_preserved=True,bithlo_sign_texture_untouched=True,
        menu_logo_exact=True,power_of_two_vehicle_textures=True,in_game_riding=False))
    print('v022 protected v021 content and R07/R10/T09-only geometry scope verified')

if __name__=='__main__':
    main()
