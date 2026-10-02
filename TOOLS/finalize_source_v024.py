"""v024 source finalizer: only T05/T06/T13 and local route/elevation shaping may differ from validated v023."""
import json
from PIL import Image
from v024_common import *

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    # v024 changes terrain, race centerline around T13, and route-derived track masks.
    # Protect the start plus non-track pit/facility inputs that should remain exact.
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx') or rel.endswith('terrain.raw') or rel.endswith('.rdf') or rel.endswith('start.tcl') or '/masks/' in rel.replace('\\','/'):
            continue
        new=rel.replace('V018','V024').replace('v018','v024');p=R/new
        assert p.is_file(),('required protected input missing',new)
        got=sha(p);checks.append(dict(file=new,expected_sha256=digest,sha256=got,unchanged=got==digest))
    failed=[c['file'] for c in checks if not c['unchanged']]
    assert not failed,('protected input changed',failed)

    f24=read(S/'facilities.json');f23=read(R/'V023_SOURCE/facilities.json')
    allowed_facility={'merge_station_m','merge_blend_length_m','start_checkpoint_stations_m','status'}
    assert all(f24[k]==f23[k] for k in f23 if k not in allowed_facility)
    assert f24['merge_station_m']==410.0 and f24['merge_blend_length_m']==24.0 and f24['start_checkpoint_stations_m']==[20,80,130]
    sl=read(S/'start_layout.json')
    assert sl['merge_station_m']==410.0 and sl['right_corner']=='T05' and sl['first_lap_turns'][0]=='T05'
    assert 20<sl['merge_before_corner_m']<40
    assert read(S/'vehicles.json')==read(R/'V023_SOURCE/vehicles.json')
    assert read(S/'pit_facilities.json')==read(R/'V023_SOURCE/pit_facilities.json')

    now=read(S/'v024_geometry_spec.json');old=read(R/'V023_SOURCE/v023_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};po={p['id']:p for p in old['profiles']}
    bn={b['id']:b for b in now['berms']};bo={b['id']:b for b in old['berms']}
    assert set(pn)==set(po) and set(bn)==set(bo)
    for rid in pn:assert pn[rid]==po[rid],('jump changed unexpectedly',rid)
    for tid in bn:
        if tid not in ['T05','T06','T13']:assert bn[tid]==bo[tid],('unauthorized berm change',tid)
    assert bn['T09']==bo['T09'], 'post-R10 corner must stay at accepted v023/v021 shape'

    hills=now.get('longitudinal_hills',[]);adj=now.get('route_adjustments',[])
    assert len(hills)==1 and hills[0]['id']=='T05_sweeping_hill'
    assert (hills[0]['station_start_m'],hills[0]['station_peak_m'],hills[0]['station_end_m'],hills[0]['height_m'])==(432.0,459.5,488.0,1.20)
    assert len(adj)==1 and adj[0]['id']=='T13_right_fade'
    assert (adj[0]['station_start_m'],adj[0]['station_peak_m'],adj[0]['station_end_m'],adj[0]['max_right_offset_m'])==(1217.0,1244.0,1292.0,3.6)

    # Preserve v021-v023 graphics corrections and approved Bithlo sign.
    mats=read(S/'vehicle_materials.json')
    expected={'premier_wrap','premier_wrap_right','premier_tail','ford_badge','king_ranch','four_by_four','chevy_badge',
              'jordan_number','premier_number','sam_number','shane_number','jordan_shroud','premier_shroud','sam_shroud','shane_shroud'}
    actual={k for k,v in mats.items() if v.get('native_u_preflipped')}
    assert actual==expected and not mats['bithlo_photo'].get('native_u_preflipped',False)
    for name,m in mats.items():
        im=Image.open(S/m['file']);assert im.width&(im.width-1)==0 and im.height&(im.height-1)==0
        assert sha(S/m['file'])==m['sha256']

    logo=read(R/'DOCUMENTATION/v024_menu_logo_validation.json')
    qa=read(R/'DOCUMENTATION/v024_vehicle_validation.json')
    graphics=read(R/'DOCUMENTATION/v024_graphics_validation.json')
    custom=read(R/'DOCUMENTATION/v024_user_request_validation.json')
    race=read(R/'DOCUMENTATION/v024_race_validation.json')
    geo=read(R/'DOCUMENTATION/v024_geometry_validation.json')
    release=read(R/'DOCUMENTATION/v024_release_validation.json')
    scenery=read(R/'DOCUMENTATION/v024_scenery_validation.json')
    assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    assert all([qa['checks_pass'],graphics['checks_pass'],custom['all_checks_pass'],race['race_source_checks_pass'],
                geo['geometry_checks_pass'],release['release_source_checks_pass'],scenery['vehicle_uv_roundtrip_pass']])

    release.update(version='v024',compared_to='validated v023',
        start_layout_relocated=True,start_merge_station_m=410.0,start_first_turn='T05',racing_deferred=True,pit_layout_preserved=True,vehicle_placements_preserved=True,
        graphics_fix_preserved=True,bithlo_sign_preserved=True,R07_preserved=True,R10_preserved=True,T09_preserved=True,
        authorized_geometry_changes=['T05 sweeping longitudinal hill and wider left','T06 lower/wider smoother right','T13 local rightward approach fade plus gradual left','route-derived race centerline and masks','start route merge relocated to clean straight before T05'],
        all_jump_profiles_preserved=True,all_other_berms_preserved=True,menu_logo_preserved=True,power_of_two_vehicle_textures=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v024_pit_gravel.tga',
        *sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),
        *sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles if p.exists()}
    save(R/'DOCUMENTATION/v024_release_validation.json',release)
    save(R/'DOCUMENTATION/v024_invariants_validation.json',dict(
        checks_pass=True,protected_inputs=checks,compared_to='v023',
        authorized_geometry_changes=['T05','T06','T13 route/berm','start merge before T05'],
        all_jump_profiles_preserved=True,R07_preserved=True,R10_preserved=True,T09_preserved=True,
        local_route_adjustment=adj[0],longitudinal_hill=hills[0],terrain_sha256=sha(O/'terrain.raw'),
        pit_layout_matches_v023=True,graphics_fix_preserved=True,bithlo_sign_texture_untouched=True,
        menu_logo_exact=True,power_of_two_vehicle_textures=True,in_game_riding=False))
    print('v024 protected v023 content and T05/T06/T13-only scope verified')

if __name__=='__main__':main()
