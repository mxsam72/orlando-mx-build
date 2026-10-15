"""Independent density, texel scope and retained source checks before compilation."""
import json
import numpy as np
from PIL import Image
from v060_surface import R,PREV,O,S,sha,save,source,previous,Circuit

def main():
 c=Circuit();report=json.loads((O/'surface_validation.json').read_text())
 assert report['checks_pass'] and len(report['spacing_checks'])==16 and len(report['full_width_face_checks'])==2
 for row in report['spacing_checks']+report['full_width_face_checks']:
  assert row['maximum_3d_spacing_m']<=.3 and row['new_line_count']>row['old_line_count']
 assert {r['section'] for r in report['spacing_checks']}=={f'T{i:02d}' for i in range(1,15)}|{'R04','R14_FACE'}
 old=Image.open(previous('v044_route_detail_n.tga'));new=Image.open(source('v044_route_detail_n.tga'));count=0;n=old.width
 assert old.size==new.size==(8192,8192)
 for row in range(0,n,96):
  end=min(n,row+96);a=np.asarray(old.crop((0,row,n,end)));b=np.asarray(new.crop((0,row,n,end)))
  assert np.array_equal(a[:,:,3],b[:,:,3]);yy,xx=np.where(np.any(a!=b,axis=2));count+=len(xx)
  if len(xx):assert np.all(c.edit_weight((xx+.5)*600/n,600-(yy+row+.5)*600/n)>0)
 assert count==report['changed_macro_pixels'] and count>0
 for item in report['retained_source_files']:assert sha(O/item['file'])==sha(PREV/item['file'])==item['sha256']
 for item in report['active_terrain_inventory']:assert sha(source(item['file']))==item['sha256']
 assert report['rgba8_base_level_bytes_before']==report['rgba8_base_level_bytes_after']
 assert report['added_layers']==report['added_images']==0
 scene=json.loads((O/'scenery_validation.json').read_text())
 assert scene['checks_pass'] and scene['approved_van_sign_cybertrucks_records_exact'] and scene['all_unrelated_records_exact']
 assert sha(O/'scenery.fbx')==scene['scenery_sha256'] and scene['requires_new_native_scenery_compile']
 pins=R/'V060_SOURCE/expected_inputs.json'
 actual=dict(terrain=sha(O/'terrain.raw'),scenery=sha(O/'scenery.fbx'),hmf=sha(O/'compiled_track.hmf'),
  main_route=sha(O/'main.tcl'),start_route=sha(O/'start.tcl'),
  terrain_textures={r['file']:r['sha256'] for r in report['active_terrain_inventory']})
 if pins.exists():assert actual==json.loads(pins.read_text()),'Generated source differs from reviewed final inputs'
 result=dict(checks_pass=True,version='v060',density_regions=18,perpendicular_regions=16,full_width_faces=2,
  maximum_spacing_m=max(r['maximum_3d_spacing_m'] for r in report['spacing_checks']+report['full_width_face_checks']),
  every_added_pass_denser=True,changed_macro_pixels=count,changes_outside_existing_grooming_envelopes=0,
  all_colour_maps_fine_normals_masks_and_alpha_exact=True,terrain_geometry_scenery_and_routes_exact_v059=True,
  source_allocation_before_bytes=report['rgba8_base_level_bytes_before'],source_allocation_after_bytes=report['rgba8_base_level_bytes_after'],
  approved_vehicles_sign_exact=True,final_compilation_authorized=True,in_game_verified=False)
 save(O/'precompile_validation.json',result);save(S/'precompile_validation.json',result)
 print('V060_PRECOMPILE_CHECKS_PASS',count,'changed texels; 18 areas denser; max spacing',result['maximum_spacing_m'],flush=True)

if __name__=='__main__':main()
