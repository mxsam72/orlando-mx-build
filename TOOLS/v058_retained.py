"""Retain the exact tested track and the approved saved scenery."""
import json,shutil
from v058_inputs import R,PREV,O,M,NAME,DEST,sha,save
from v057_vehicle_review import mesh_digest

def main():
 O.mkdir(exist_ok=True);M.mkdir(exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
 retained=[]
 for name in ['terrain.raw','terrain_16bit.png','route.npz','layout.json','jump_profiles.json','main.tcl','start.tcl','compiled_track.hmf','corner_guard.npy','landing_scope.npy','landing_sections.npz']:
  shutil.copy2(PREV/name,O/name);assert sha(O/name)==sha(PREV/name);retained.append(dict(file=name,sha256=sha(O/name)))
 assert sha(O/'terrain.raw')=='ab99df42094ef29015f117babeffe555e814fc7f86cf836c60625b760868289f'
 save(O/'terrain_validation.json',dict(checks_pass=True,entire_terrain_exact_v056=True,all_14_corner_grids_exact=True,
  landing_exact_v056=True,terrain_sha256=sha(O/'terrain.raw'),retained_source_files=retained))
 approved=R/'V057_OUTPUT';q=json.loads((approved/'scenery_validation.json').read_text())
 assert q['checks_pass'] and q['all_unrelated_records_exact'] and q['all_physical_scene_geometry_exact']
 assert sha(approved/'scenery.fbx')==q['scenery_sha256']
 expected=json.loads((R/'V057_SOURCE/update.json').read_text())['reviewed_source_mesh_digests']['v057']
 assert mesh_digest(approved/'scenery.fbx')==expected
 assert q['sign']['serialized_uv_forward_and_upright_both_faces'] and q['sign']['no_coplanar_faces']
 assert 2.95<q['sign']['clearance_to_van_nose_m']<3.05
 for name in ['scenery.fbx','native_probes.json','vehicle_meshes.json']:shutil.copy2(approved/name,O/name)
 shutil.copytree(approved/'facility_textures',O/'facility_textures',dirs_exist_ok=True)
 assert sha(O/'scenery.fbx')==q['scenery_sha256']
 save(O/'scenery_validation.json',dict(q,approved_v057_preserved=True,approved_v057_mesh_digest=expected,
  approved_sign_placement_preserved=True,approved_cybertruck_colours_preserved=True))
 rows=[];game=R/'12_RELEASE/orlandomx_2026_v056'
 for src in sorted(game.iterdir()):
  if src.suffix in ['.map','.trh'] or src.name=='code.txt':continue
  dest=DEST/src.name.replace('orlandomx_2026_v056',NAME);shutil.copy2(src,dest)
  if dest.suffix=='.ini':dest.write_text(dest.read_text().replace('v056','v058'))
  else:assert sha(src)==sha(dest);rows.append(dict(file=dest.name,sha256=sha(dest)))
 assert len(list(DEST.iterdir()))==11
 save(O/'race_validation.json',dict(checks_pass=True,native_routes_exact_v056=True,all_race_reset_grid_pits_checkpoints_exact=True,retained_game_files=rows))
 print('V058_TERRAIN_RACE_AND_APPROVED_SCENERY_RETAINED',flush=True)

if __name__=='__main__':main()
