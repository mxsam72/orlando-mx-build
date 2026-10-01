"""v021 source finalizer: only readable decal handedness may differ from validated v020."""
import json
from PIL import Image
from v021_common import *

def normalized(value):
    return json.dumps(value,sort_keys=True).replace('v021','v020').replace('V021','V020')

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    # Terrain/start/race/physics inputs remain protected by the established v018 hashes.
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx'):continue
        new=rel.replace('V018','V021').replace('v018','v021');p=R/new
        assert p.is_file(),('required protected input missing',new)
        got=sha(p);checks.append(dict(file=new,expected_sha256=digest,sha256=got,unchanged=got==digest))
    failed=[c['file'] for c in checks if not c['unchanged']]
    assert not failed,('protected track input changed',failed)

    # v021 is an orientation-only graphics correction. All authored source
    # placement/geometry/facility specifications must otherwise match v020.
    assert read(S/'facilities.json')==read(R/'V020_SOURCE/facilities.json')
    assert read(S/'start_layout.json')==read(R/'V020_SOURCE/start_layout.json')
    assert normalized(read(S/'v021_geometry_spec.json'))==json.dumps(read(R/'V020_SOURCE/v020_geometry_spec.json'),sort_keys=True)
    assert normalized(read(S/'vehicles.json'))==json.dumps(read(R/'V020_SOURCE/vehicles.json'),sort_keys=True)
    assert normalized(read(S/'pit_facilities.json'))==json.dumps(read(R/'V020_SOURCE/pit_facilities.json'),sort_keys=True)

    mats=read(S/'vehicle_materials.json')
    expected={
        'premier_wrap','premier_wrap_right','premier_tail',
        'ford_badge','king_ranch','four_by_four','chevy_badge',
        'jordan_number','premier_number','sam_number','shane_number',
        'jordan_shroud','premier_shroud','sam_shroud','shane_shroud'
    }
    actual={k for k,v in mats.items() if v.get('native_u_preflipped')}
    assert actual==expected,(sorted(actual),sorted(expected))
    assert not mats['bithlo_photo'].get('native_u_preflipped',False)
    for name,m in mats.items():
        im=Image.open(S/m['file'])
        assert im.width&(im.width-1)==0 and im.height&(im.height-1)==0,(name,im.size)
        assert sha(S/m['file'])==m['sha256']

    logo=read(R/'DOCUMENTATION/v021_menu_logo_validation.json')
    qa=read(R/'DOCUMENTATION/v021_vehicle_validation.json')
    graphics=read(R/'DOCUMENTATION/v021_graphics_validation.json')
    custom=read(R/'DOCUMENTATION/v021_user_request_validation.json')
    race=read(R/'DOCUMENTATION/v021_race_validation.json')
    geo=read(R/'DOCUMENTATION/v021_geometry_validation.json')
    release=read(R/'DOCUMENTATION/v021_release_validation.json')
    scenery=read(R/'DOCUMENTATION/v021_scenery_validation.json')
    assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    assert all([qa['checks_pass'],graphics['checks_pass'],custom['all_checks_pass'],
                race['race_source_checks_pass'],geo['geometry_checks_pass'],
                release['release_source_checks_pass'],scenery['vehicle_uv_roundtrip_pass']])
    assert qa['generic_pickup_03_removed'] and qa['bithlo_sign_relocated'] and qa['power_of_two_textures']

    release.update(
        version='v021',compared_to='validated v020',
        physics_materials_unchanged=True,race_layout_preserved=True,
        pit_layout_preserved=True,vehicle_placements_preserved=True,
        authorized_asset_changes=['native horizontal orientation compensation for readable truck/bike decals only'],
        premier_wrap_orientation_fix=True,ford_badge_orientation_fix=True,ford_4x4_orientation_fix=True,
        bike_number_orientation_fix=True,bike_shroud_orientation_fix=True,
        bithlo_sign_preserved=True,menu_logo_preserved=True,power_of_two_vehicle_textures=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v021_pit_gravel.tga',
        *sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),
        *sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles if p.exists()}
    save(R/'DOCUMENTATION/v021_release_validation.json',release)
    save(R/'DOCUMENTATION/v021_invariants_validation.json',dict(
        checks_pass=True,protected_track_inputs=checks,
        source_specs_match_v020=True,vehicle_placements_match_v020=True,pit_layout_matches_v020=True,
        readable_graphics_native_preflip=sorted(actual),bithlo_sign_texture_untouched=True,
        menu_logo_exact=True,power_of_two_vehicle_textures=True,in_game_riding=False))
    print('v021 protected v020 source and graphics-only correction verified')
if __name__=='__main__':main()
