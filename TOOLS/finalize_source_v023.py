"""v023 source finalizer: allow only T06, T09 and T13 corner changes from validated v022."""
import json
from PIL import Image
from v023_common import *

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    # Terrain and the terrain-derived visual racing mask are intentionally
    # regenerated. All other protected native inputs must remain unchanged.
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx') or rel.endswith('terrain.raw') or rel.endswith('masks/visual_racing.tga'):
            continue
        new=rel.replace('V018','V023').replace('v018','v023');p=R/new
        assert p.is_file(),('required protected input missing',new)
        got=sha(p);checks.append(dict(file=new,expected_sha256=digest,sha256=got,unchanged=got==digest))
    failed=[c['file'] for c in checks if not c['unchanged']]
    assert not failed,('protected non-terrain input changed',failed)

    assert read(S/'facilities.json')==read(R/'V022_SOURCE/facilities.json')
    assert read(S/'start_layout.json')==read(R/'V022_SOURCE/start_layout.json')
    assert read(S/'vehicles.json')==read(R/'V022_SOURCE/vehicles.json')
    assert read(S/'pit_facilities.json')==read(R/'V022_SOURCE/pit_facilities.json')

    now=read(S/'v023_geometry_spec.json');old=read(R/'V022_SOURCE/v022_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};po={p['id']:p for p in old['profiles']}
    bn={b['id']:b for b in now['berms']};bo={b['id']:b for b in old['berms']}
    assert set(pn)==set(po) and set(bn)==set(bo)
    for rid in pn:
        assert pn[rid]==po[rid],('jump changed unexpectedly',rid)
    for tid in bn:
        if tid not in ['T06','T09','T13']:
            assert bn[tid]==bo[tid],('unauthorized berm change',tid)

    # T09 must be an exact revert to the v021 shape.
    v21=read(R/'V021_SOURCE/v021_geometry_spec.json')
    b21={b['id']:b for b in v21['berms']}
    assert bn['T09']==b21['T09']

    t13=bn['T13'];t06=bn['T06']
    assert t13['effective_width_m']==9.6 and t13['rut_paths'][1]['exit_out_m']==2.35
    assert t13['entry_load']==0.78 and t13['exit_load']==0.72
    assert t06['outer_rise_m']==2.05 and t06['effective_width_m']==9.0
    assert t06['exit_load']==0.48 and t06['pocket_depth_m']==0.20

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

    logo=read(R/'DOCUMENTATION/v023_menu_logo_validation.json')
    qa=read(R/'DOCUMENTATION/v023_vehicle_validation.json')
    graphics=read(R/'DOCUMENTATION/v023_graphics_validation.json')
    custom=read(R/'DOCUMENTATION/v023_user_request_validation.json')
    race=read(R/'DOCUMENTATION/v023_race_validation.json')
    geo=read(R/'DOCUMENTATION/v023_geometry_validation.json')
    release=read(R/'DOCUMENTATION/v023_release_validation.json')
    scenery=read(R/'DOCUMENTATION/v023_scenery_validation.json')
    assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    assert all([qa['checks_pass'],graphics['checks_pass'],custom['all_checks_pass'],
                race['race_source_checks_pass'],geo['geometry_checks_pass'],
                release['release_source_checks_pass'],scenery['vehicle_uv_roundtrip_pass']])

    release.update(
        version='v023',compared_to='validated v022',
        race_layout_preserved=True,start_layout_preserved=True,pit_layout_preserved=True,
        vehicle_placements_preserved=True,graphics_fix_preserved=True,bithlo_sign_preserved=True,
        R07_preserved=True,R10_preserved=True,
        authorized_geometry_changes=['T09 exact revert to v021','T13 wider/softer left with farther-right exit line','T06 stronger uphill bank with earlier fade before R07','terrain-derived visual_racing mask'],
        all_jump_profiles_preserved=True,all_other_berms_preserved=True,
        menu_logo_preserved=True,power_of_two_vehicle_textures=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v023_pit_gravel.tga',
        *sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),
        *sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles if p.exists()}
    save(R/'DOCUMENTATION/v023_release_validation.json',release)
    save(R/'DOCUMENTATION/v023_invariants_validation.json',dict(
        checks_pass=True,protected_nonterrain_inputs=checks,compared_to='v022',
        authorized_geometry_changes=['T06','T09','T13'],all_jump_profiles_preserved=True,
        R07_preserved=True,R10_preserved=True,terrain_changed_intentionally=True,
        terrain_sha256=sha(O/'terrain.raw'),pit_layout_matches_v022=True,
        graphics_fix_preserved=True,bithlo_sign_texture_untouched=True,
        menu_logo_exact=True,power_of_two_vehicle_textures=True,in_game_riding=False))
    print('v023 protected v022 content and T06/T09/T13-only corner scope verified')

if __name__=='__main__':
    main()
