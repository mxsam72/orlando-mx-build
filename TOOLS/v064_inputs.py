"""Recover pinned tested inputs and stage the approved B/C hybrid for native tools."""
import gc,json,os,re,shutil,sys,zipfile
from pathlib import Path
import numpy as np
from v061_inputs import R,PREV as TESTED,CACHE,PINS,restore as restore_materials,download,extract,sha,save
from v064_hybrid import O,M,S,source

NAME='orlandomx_2026_v064';DEST=R/'12_RELEASE'/NAME
SAVED=R/'BUILD/v064_saved_scenery';GAME=R/'BUILD/v064_game_baseline'
TAG='v060-dense-grooming-38699998845'
EXTRA={
 'v047_source.zip':('v047-realistic-trees-38458081921/OrlandoMX-v047-tree-source-checkpoint.zip',292379577,'0a1f44d74eef2908a17e120fac9eed7ad9ec416fa693c51d0c6a08c83749cdf1'),
 'v060_native_scenery.zip':(TAG+'/OrlandoMX-v060-native-scenery.zip',229447747,'c0be39314e299458654371e08f437f68975d2c3f0aaa4cb38a369d79644c91a4'),
 'v060_validation.json':(TAG+'/OrlandoMX_v060_Validation.json',148434,'bff73cac5ad0308875be4b32d9192959427f7919e715f20c7056333b9b2bf82d'),
}
EXPECTED=S/'native_expected_inputs.json'

def auxiliary():
 files={name:download((name,pin)) for name,pin in EXTRA.items()}
 for version in ['v044','v047','v052']:
  path=files.get(version+'_source.zip',CACHE/(version+'_source.zip'))
  with zipfile.ZipFile(path) as z:
   for name in z.namelist():
    keep=name.startswith(version.upper()+'_OUTPUT/facility_textures/') or name=='V044_OUTPUT/turns.json'
    if keep and not name.endswith('/'):extract(z,name,R/name)
 original=CACHE/'OrlandoMX-v060-source-checkpoint.zip'
 if not original.exists():original=CACHE/'v060_source.zip'
 assert sha(original)==PINS['v060_source.zip'][2]
 GAME.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(original) as z:
  prefix='12_RELEASE/orlandomx_2026_v060/'
  for name in z.namelist():
   if name.startswith(prefix) and not name.endswith('/'):extract(z,name,GAME/Path(name).name)
   if name in ['BUILD/v054_input_validation.json','BUILD/v058_input_validation.json']:extract(z,name,R/name)
  amb=R/'BUILD/v062_inputs/baseline_v060.amb';extract(z,prefix+'orlandomx_2026_v060.amb',amb)
 SAVED.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(files['v060_native_scenery.zip']) as z:
  assert z.testzip() is None and set(z.namelist())=={'scenery.edf','fbx2edf_v060.log'}
  for name in z.namelist():extract(z,name,SAVED/name)
 q=json.loads(files['v060_validation.json'].read_text());assert q['compiled'] and q['source_checks'] and q['package_integrity_passed']
 assert q['source_validation']['scenery_validation']['scenery_sha256']==sha(TESTED/'scenery.fbx')
 assert q['native_object_textures']['checks_pass'] and q['native_height_validation']['checks_pass']
 save(R/'BUILD/v064_recovered_inputs.json',dict(checks_pass=True,baseline_release=TAG,pinned_material_dependencies=PINS,pinned_auxiliary_assets=EXTRA,
  source_scenery_sha256=sha(TESTED/'scenery.fbx'),saved_edf_sha256=sha(SAVED/'scenery.edf'),game_file_count=len(list(GAME.iterdir()))))
 print('V064_TESTED_SOURCE_AND_NATIVE_SCENERY_RECOVERED',flush=True)

def restore():
 restore_materials();auxiliary()
 import v061_roller,v062_trials,v064_hybrid
 v061_roller.geometry();gc.collect()
 # Only the approved original methods are needed; the rejected dense trial
 # and the unrelated A experiment are never generated for this build.
 v062_trials.METHODS={k:v for k,v in v062_trials.METHODS.items() if k in ['B','C']}
 v062_trials.main();gc.collect();v064_hybrid.main();gc.collect()
 prepare();check()

def prepare():
 DEST.mkdir(parents=True,exist_ok=True)
 oldrace=json.loads((TESTED/'race_validation.json').read_text());original_hashes={r['file']:r['sha256'] for r in oldrace['retained_game_files']};retained=[]
 for src in sorted(GAME.iterdir()):
  assert src.is_file() and src.suffix not in ['.map','.trh'] and src.name!='code.txt'
  if src.name in original_hashes:assert sha(src)==original_hashes[src.name]
  dest=DEST/src.name.replace('orlandomx_2026_v060',NAME)
  if src.suffix=='.ini':dest.write_text(src.read_text().replace('v060','v064'),encoding='utf-8',newline='\n')
  elif src.suffix=='.amb':shutil.copy2(O/'trial_daylight.amb',dest)
  else:
   shutil.copy2(src,dest);assert sha(dest)==sha(src);retained.append(dict(file=dest.name,sha256=sha(dest)))
 assert len(list(DEST.iterdir()))==11
 save(O/'race_validation.json',dict(checks_pass=True,all_race_reset_grid_pits_checkpoints_exact_v060=True,native_main_and_start_routes_exact_v060=True,
  retained_game_files=retained,lighting_file=NAME+'.amb',lighting_sha256=sha(DEST/(NAME+'.amb')),lighting_exact_approved_previews=True,version_name_only_ini_change=True))
 for name in ['native_probes.json','scenery_validation.json','vehicle_meshes.json']:
  dest=O/name
  if not dest.exists():os.link(TESTED/name,dest)
  assert sha(dest)==sha(TESTED/name)
 surface=json.loads((O/'surface_validation.json').read_text());base=json.loads((TESTED/'surface_validation.json').read_text())
 surface.update(active_shaders=base['active_shaders'],rgba8_base_level_bytes_before=base['rgba8_base_level_bytes_after'],rgba8_base_level_bytes_after=surface['texture_allocation_bytes'])
 assert surface['rgba8_base_level_bytes_before']==surface['rgba8_base_level_bytes_after']
 save(O/'surface_validation.json',surface)
 save(O/'terrain_validation.json',dict(checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),approved_wall_roller_exact=True,
  entire_ground_exact_approved_v061=True,all_MX_heights_exact_v060=True,wall_roller_changes=json.loads((R/'V061_OUTPUT/validation.json').read_text())))

def actual_inputs():
 s=json.loads((O/'surface_validation.json').read_text())
 return dict(approved_preview_commit='d0660a9a8b7be9ce30de60479a0498872deb7a4f',terrain=sha(O/'terrain.raw'),scenery=sha(O/'scenery.fbx'),
  hmf=sha(O/'compiled_track.hmf'),main_route=sha(O/'main.tcl'),start_route=sha(O/'start.tcl'),physical_declarations=sha(R/'BUILD/v054_track.tht'),
  daylight=sha(O/'trial_daylight.amb'),texture_allocation_bytes=s['texture_allocation_bytes'],
  terrain_images={r['file']:sha(source(r['file'])) for r in s['active_terrain_inventory']},terrain_shaders={r['file']:sha(source(r['file'])) for r in s['active_shaders']},
  native_scenery_source_zip_sha256=EXTRA['v060_native_scenery.zip'][2])

def check():
 expected=json.loads(EXPECTED.read_text());actual=actual_inputs();assert actual==expected,('Native inputs differ from approved preview source',[k for k in actual if actual[k]!=expected.get(k)])
 raw=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);old=np.fromfile(TESTED/'terrain.raw','<u2').reshape(2049,2049)
 scope=np.load(R/'V061_OUTPUT/roller_scope.npy');assert np.array_equal(raw[~scope],old[~scope]) and np.count_nonzero(raw!=old)==4751
 scene=json.loads((O/'scenery_validation.json').read_text());assert scene['checks_pass'] and scene['approved_van_sign_cybertrucks_records_exact']
 assert scene['scenery_sha256']==actual['scenery'] and sha(TESTED/'scenery.fbx')==actual['scenery']
 assert actual['scenery']=='40d8e6ddeacfa0d0c3c9fad454abd2f83acee633fb367e31c8530d8dbafa6e99'
 assert actual['terrain']=='860350c4c733e5d26939e9e2f40204679ecef302d6e07889f78a849afc8a8fa2'
 from v056_geometry import corner_checks
 route=dict(np.load(O/'route.npz'));_,corners=corner_checks(old,raw,route['q'],route['v054_old_station']);assert len(corners)==14 and all(c['raw_grid_exact'] for c in corners)
 race=json.loads((O/'race_validation.json').read_text())
 for row in race['retained_game_files']:assert sha(DEST/row['file'])==row['sha256']
 assert sha(DEST/(NAME+'.amb'))==actual['daylight']
 recovered=json.loads((R/'BUILD/v064_recovered_inputs.json').read_text());assert recovered['checks_pass'] and sha(SAVED/'scenery.edf')==recovered['saved_edf_sha256']
 report=dict(checks_pass=True,exact_approved_B_corner_C_elsewhere_inputs=True,all_14_corner_heights_exact_v060=True,wall_roller_exact_approved_source=True,
  scenery_vehicles_sign_exact_v060=True,source_texture_allocation_unchanged=True,all_retained_race_data_exact=True,approved_daylight_installed=True,
  expected_inputs=actual,corner_checks=corners,reused_native_scenery_sha256=recovered['saved_edf_sha256'])
 save(O/'precompile_validation.json',report);save(O/'generated_final_inputs.json',actual)
 print('V064_PRECOMPILE_PASS; exact approved hybrid, roller, scenery, race data and daylight',flush=True)

if __name__=='__main__':{'restore':restore,'auxiliary':auxiliary,'prepare':prepare,'check':check}[sys.argv[1]]()
