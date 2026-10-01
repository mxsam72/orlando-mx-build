"""v020 source finalizer: fail closed on any change outside the authorized pit/asset corrections."""
import json,hashlib,os
from PIL import Image
from v020_common import *

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    # Track physics / terrain / start / race files remain byte-identical to validated v018/v019.
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx'):continue
        new=rel.replace('V018','V020').replace('v018','v020');p=R/new
        if not p.exists():continue
        got=sha(p);checks.append(dict(file=new,expected_sha256=digest,sha256=got,unchanged=got==digest))
    failed=[c['file'] for c in checks if not c['unchanged']]
    assert not failed,('protected track input changed',failed)

    # Core source configs must match v019 except version naming and the two authorized pit edits.
    for name in ['facilities.json','start_layout.json']:
        assert read(S/name)==read(R/'V019_SOURCE'/name),(name,'changed')
    a=read(S/'v020_geometry_spec.json');b=read(R/'V019_SOURCE/v019_geometry_spec.json')
    assert json.dumps(a,sort_keys=True).replace('v020','v019').replace('V020','V019')==json.dumps(b,sort_keys=True)

    p20=read(S/'pit_facilities.json');p19=read(R/'V019_SOURCE/pit_facilities.json')
    assert p20['roads']==p19['roads'] and p20['grass_patches']==p19['grass_patches']
    old={x['id']:x for x in p19['assets']};new={x['id']:x for x in p20['assets']}
    assert set(new)==set(old)-{'pickup_03'}
    for k in set(new)-{'bithlo_sticker_stop'}:assert new[k]==old[k],('unauthorized facility change',k)
    assert new['bithlo_sticker_stop']['xz']==[242.0,143.0] and new['bithlo_sticker_stop']['heading']==180

    # Vehicle placements are preserved; only meshes/textures are intentionally revised.
    v20=read(S/'vehicles.json');v19=read(R/'V019_SOURCE/vehicles.json')
    assert json.dumps(v20,sort_keys=True).replace('v020','v019')==json.dumps(v19,sort_keys=True)

    mats=read(S/'vehicle_materials.json')
    for name,m in mats.items():
        im=Image.open(S/m['file'])
        assert im.width&(im.width-1)==0 and im.height&(im.height-1)==0,(name,im.size)
        assert sha(S/m['file'])==m['sha256']

    logo=read(R/'DOCUMENTATION/v020_menu_logo_validation.json')
    assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    qa=read(R/'DOCUMENTATION/v020_vehicle_validation.json')
    custom=read(R/'DOCUMENTATION/v020_user_request_validation.json')
    race=read(R/'DOCUMENTATION/v020_race_validation.json')
    geo=read(R/'DOCUMENTATION/v020_geometry_validation.json')
    release=read(R/'DOCUMENTATION/v020_release_validation.json')
    scenery=read(R/'DOCUMENTATION/v020_scenery_validation.json')
    assert all([qa['checks_pass'],custom['all_checks_pass'],race['race_source_checks_pass'],
                geo['geometry_checks_pass'],release['release_source_checks_pass'],
                scenery['vehicle_uv_roundtrip_pass']])
    assert qa['generic_pickup_03_removed'] and qa['bithlo_sign_relocated'] and qa['power_of_two_textures']

    release.update(version='v020',compared_to='validated v019',
        physics_materials_unchanged=True,race_layout_preserved=True,
        authorized_pit_asset_changes=['remove pickup_03','relocate/rebuild bithlo_sticker_stop'],
        vehicle_checks_pass=True,menu_logo_preserved=True,power_of_two_vehicle_textures=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v020_pit_gravel.tga',
        *sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),
        *sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles if p.exists()}
    save(R/'DOCUMENTATION/v020_release_validation.json',release)
    save(R/'DOCUMENTATION/v020_invariants_validation.json',dict(
        checks_pass=True,protected_track_inputs=checks,pit_changes_authorized_only=True,
        generic_pickup_03_removed=True,bithlo_sign_relocated=True,menu_logo_exact=True,
        power_of_two_vehicle_textures=True,in_game_riding=False))
    print('v020 protected track inputs and authorized asset-only changes verified')
if __name__=='__main__':main()
