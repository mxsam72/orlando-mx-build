"""Fail closed if a scenery-only update changes protected v018 track inputs."""
import json,hashlib,os
from v019_common import *

def main():
    inv=read(S/'v018_invariants.json');checks=[]
    for rel,digest in inv['input_sha256'].items():
        if rel.endswith('scenery.fbx'):continue
        new=rel.replace('V018','V019').replace('v018','v019');p=R/new;got=sha(p);checks.append(dict(file=new,expected_v018_sha256=digest,sha256=got,unchanged=got==digest))
    for name in ['facilities.json','pit_facilities.json','start_layout.json','v019_geometry_spec.json']:
        a=read(S/name);b=read(R/'V018_SOURCE'/name.replace('v019','v018'));assert json.dumps(a,sort_keys=True).replace('v019','v018').replace('V019','V018')==json.dumps(b,sort_keys=True),(name,'source geometry changed')
    scene=read(O/'facility_meshes.json');digest=hashlib.sha256(json.dumps(scene,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert digest==read(S/'v018_facility_mesh_fingerprint.json')['canonical_sha256'],'Existing facility geometry changed'
    failed=[c['file'] for c in checks if not c['unchanged']];assert not failed,('v018 invariant change',failed)
    logo=read(R/'DOCUMENTATION/v019_menu_logo_validation.json');assert logo['checks_pass'] and logo['logo_sha256']==inv['menu_preview_tga_sha256']
    qa=read(R/'DOCUMENTATION/v019_vehicle_validation.json');custom=read(R/'DOCUMENTATION/v019_user_request_validation.json');race=read(R/'DOCUMENTATION/v019_race_validation.json');geo=read(R/'DOCUMENTATION/v019_geometry_validation.json');release=read(R/'DOCUMENTATION/v019_release_validation.json');scenery=read(R/'DOCUMENTATION/v019_scenery_validation.json')
    assert all([qa['checks_pass'],custom['all_checks_pass'],race['race_source_checks_pass'],geo['geometry_checks_pass'],release['release_source_checks_pass'],scenery['vehicle_uv_roundtrip_pass'],scenery['preexisting_objects_unchanged']])
    qa.update(v018_invariants=checks,existing_facility_geometry_unchanged=True,existing_facility_mesh_canonical_sha256=digest,race_layout_valid=True,race_layout_matches_v018=True,gravel_road_connected=custom['checks']['gravel_network_connected'],orlando_mx_menu_logo_preserved=True,logo_sha256=logo['logo_sha256']);save(R/'DOCUMENTATION/v019_vehicle_validation.json',qa)
    release.update(version='v019',compared_to='validated v018',physics_materials_unchanged=True,physics_surface_masks_changed=False,race_rdf_unchanged=True,main_centerline_alignment_unchanged=True,start_centerline_replaced=False,vehicle_checks_pass=True,menu_logo_preserved=True,existing_facilities_unchanged=True)
    inputfiles=[O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v019_pit_gravel.tga',*sorted((O/'masks').glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga')),*sorted((R/'12_RELEASE'/NAME).glob('*.tga'))]
    release['input_sha256']={str(p.relative_to(R)):sha(p) for p in inputfiles};save(R/'DOCUMENTATION/v019_release_validation.json',release)
    save(R/'DOCUMENTATION/v019_invariants_validation.json',dict(checks_pass=True,checks=checks,existing_facility_geometry_sha256=digest,protected_source_configs_unchanged=True,menu_logo_exact=True))
    print('Protected v018 terrain/start/race/masks/facilities and corrected logo verified')
if __name__=='__main__':main()
