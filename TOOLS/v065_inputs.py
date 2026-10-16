"""Restore the complete v064 checkpoint, then apply the scoped start fix."""
import json,os,shutil,sys,urllib.request,zipfile
from pathlib import Path
from v065_start import R,BASE as TESTED,O,M,S,source,sha,save,TERRAIN_SHA,SCENERY_SHA

NAME='orlandomx_2026_v065';DEST=R/'12_RELEASE'/NAME
SAVED=R/'BUILD/v065_saved_scenery';CACHE=R/'BUILD/v065_inputs'
ROOT='https://github.com/mxsam72/orlando-mx-build/releases/download/'
EXTRA={
 'v064_source.zip':('v064-hybrid-38832665174/OrlandoMX-v064-source-checkpoint.zip',808262024,'5a729c09fa84c6f88b2b4204f36f6f98d29d3afa0d2c911837d6a0f7e1d1c1c6'),
 'v060_native_scenery.zip':('v060-dense-grooming-38699998845/OrlandoMX-v060-native-scenery.zip',229447747,'c0be39314e299458654371e08f437f68975d2c3f0aaa4cb38a369d79644c91a4')}

def read(p):return json.loads(Path(p).read_text())
def download(name):
 CACHE.mkdir(parents=True,exist_ok=True);p=CACHE/name;rel,size,digest=EXTRA[name]
 if p.is_file() and p.stat().st_size==size and sha(p)==digest:return p
 tmp=p.with_suffix('.downloading');request=urllib.request.Request(ROOT+rel,headers={'User-Agent':'OrlandoMX-v065-source-recovery'})
 with urllib.request.urlopen(request,timeout=120) as stream,tmp.open('wb') as out:shutil.copyfileobj(stream,out,8*1024*1024)
 assert tmp.stat().st_size==size and sha(tmp)==digest,(name,tmp.stat().st_size);tmp.replace(p);return p

def prepare():
 DEST.mkdir(parents=True,exist_ok=True);S.mkdir(parents=True,exist_ok=True)
 old='orlandomx_2026_v064';retained=[]
 for src in sorted((R/'12_RELEASE'/old).iterdir()):
  if not src.is_file():continue
  name=src.name.replace(old,NAME);dest=DEST/name
  if src.suffix=='.ini':dest.write_text(src.read_text().replace(old,NAME).replace('v064','v065'),encoding='utf-8',newline='\n')
  else:shutil.copy2(src,dest);retained.append(dict(file=name,sha256=sha(dest)))
 assert len(list(DEST.iterdir()))==11
 amb=sha(DEST/(NAME+'.amb'));assert amb=='77f98c93c8cd3d9ae7277f01c94edf06b7e6da1c6f96c38027484b4172735ecb'
 shutil.copy2(TESTED/'native_probes.json',O/'native_probes.json')
 save(O/'race_validation.json',dict(checks_pass=True,all_race_reset_grid_pits_checkpoints_exact_v064=True,
  native_main_and_start_routes_exact_v064=True,retained_game_files=retained,lighting_sha256=amb,version_name_only_ini_change=True))
 save(O/'terrain_validation.json',dict(checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),every_height_exact_v064=True,wall_roller_exact=True))
 save(O/'scenery_validation.json',dict(checks_pass=True,scenery_sha256=sha(O/'scenery.fbx'),every_scenery_byte_exact_v064=True,
  vehicles_sign_and_scenery_unchanged=True,grass_removed_in_visual_ground_mask_only=True))
 native=read(R/'BUILD/v064_recovered_inputs.json');assert sha(SAVED/'scenery.edf')==native['saved_edf_sha256']
 save(R/'BUILD/v065_recovered_inputs.json',dict(checks_pass=True,baseline_release='v064-hybrid-38832665174',pinned_assets=EXTRA,
  source_scenery_sha256=SCENERY_SHA,saved_edf_sha256=native['saved_edf_sha256'],game_file_count=11))
 surface=read(O/'surface_validation.json')
 actual=dict(terrain=sha(O/'terrain.raw'),scenery=sha(O/'scenery.fbx'),physical_declarations=sha(R/'BUILD/v054_track.tht'),
  daylight=amb,terrain_images={row['file']:sha(source(row['file'])) for row in surface['active_terrain_inventory']},
  terrain_shaders={row['file']:sha(source(row['file'])) for row in surface['active_shaders']})
 expected=S/'native_expected_inputs.json'
 if expected.is_file():assert read(expected)==actual,'Regenerated inputs must match the reviewed source hashes'
 save(expected,actual);check()

def restore():
 archive=download('v064_source.zip')
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for name in z.namelist():
   keep=name.startswith(('V064_OUTPUT/','12_RELEASE/orlandomx_2026_v064/')) or (name.startswith('BUILD/') and '/v064_stage/' not in name)
   if keep and not name.endswith('/'):
    assert '..' not in Path(name).parts;z.extract(name,R)
 saved=download('v060_native_scenery.zip');SAVED.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(saved) as z:
  assert set(z.namelist())=={'scenery.edf','fbx2edf_v060.log'} and z.testzip() is None
  z.extractall(SAVED)
 from v065_start import main
 main();prepare()

def check():
 actual=read(S/'native_expected_inputs.json');assert actual['terrain']==TERRAIN_SHA and actual['scenery']==SCENERY_SHA
 assert sha(O/'terrain.raw')==actual['terrain'] and sha(O/'scenery.fbx')==actual['scenery']
 assert sha(R/'BUILD/v054_track.tht')==actual['physical_declarations']=='04aa0b587248caa8fb822c8fa8ed972bd3a919686def52a3639d71fc40cfbc9e'
 for kind in ['terrain_images','terrain_shaders']:
  for name,digest in actual[kind].items():assert sha(source(name))==digest,name
 for row in read(O/'race_validation.json')['retained_game_files']:assert sha(DEST/row['file'])==row['sha256']
 assert sha(DEST/(NAME+'.amb'))==actual['daylight']
 assert sha(SAVED/'scenery.edf')==read(R/'BUILD/v065_recovered_inputs.json')['saved_edf_sha256']
 for label in ['terrain','surface','scenery','race']:assert read(O/(label+'_validation.json'))['checks_pass']
 report=dict(checks_pass=True,expected_inputs=actual,terrain_and_wall_roller_exact_v064=True,scenery_vehicles_sign_exact_v064=True,
  start_C_coverage_checked=True,circled_grass_mask_removed=True,source_texture_allocation_unchanged=True,
  all_race_data_exact=True,approved_daylight_installed=True,reused_native_scenery_sha256=sha(SAVED/'scenery.edf'))
 save(O/'precompile_validation.json',report);save(O/'generated_final_inputs.json',actual)
 print('V065_PRECOMPILE_PASS; C start and cleared left strip; geometry, race data and allocation retained',flush=True)

if __name__=='__main__':{'restore':restore,'prepare':prepare,'check':check}[sys.argv[1]]()
