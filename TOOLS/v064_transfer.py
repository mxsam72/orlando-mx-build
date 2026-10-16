"""Save complete approved source and publish only the validated v064 native build."""
import json,os,sys,zipfile
from pathlib import Path
from v052_transfer import api,identity,upload
from v064_inputs import R,O,S,NAME,DEST,source,sha,save

def read(path):return json.loads(Path(path).read_text())
def release():
 rel=api('/releases/'+os.environ['V064_RELEASE_ID']);assert rel['draft'] and rel['tag_name'].startswith('v064-hybrid-');return rel

def checkpoint():
 identity()
 for name in ['terrain_validation','surface_validation','scenery_validation','race_validation','precompile_validation','native_staging_validation']:
  assert read(O/(name+'.json'))['checks_pass']
 archive=R/'BUILD/OrlandoMX-v064-source-checkpoint.zip';tmp=archive.with_suffix('.zip.writing');written=set()
 with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  def add(p,name=None):
   p=Path(p);name=name or p.relative_to(R).as_posix()
   if name not in written:z.write(p,name);written.add(name)
  for folder in [O,S,DEST]:
   for p in sorted(folder.rglob('*')):
    if p.is_file():add(p)
  # Every active terrain image and shader is saved under the new output,
  # avoiding another chain of older photographic/mask overlay dependencies.
  surface=read(O/'surface_validation.json')
  for row in surface['active_terrain_inventory']+surface['active_shaders']:add(source(row['file']),'V064_OUTPUT/materials/'+row['file'])
  staging=read(O/'native_staging_validation.json');pdir=R/'BUILD/v064_stage'
  for name in staging['object_texture_files']:
   add(pdir/name,'V064_OUTPUT/facility_textures/'+name)
   for ext in ['.shd','.flg']:
    f=(pdir/name).with_suffix(ext)
    if f.is_file():add(f,'V064_OUTPUT/facility_textures/'+f.name)
  for version in ['v061','v062','v064']:
   for p in sorted((R/'TOOLS').glob('*'+version+'*.py')):add(p)
  for name in ['v054_track.tht','edf_params.ini','trh_params.ini','map_params.ini','tool_versions.json','v064_recovered_inputs.json']:add(R/'BUILD'/name)
  for name in ['roller.json','geometry_validation.json']:add(R/'V061_SOURCE'/name)
  for name in ['designs.json','trial_validation.json']:add(R/'V062_SOURCE'/name)
  for name in ['track.tht','map_params.ini']:add(pdir/name)
 with tmp.open('r+b') as f:os.fsync(f.fileno())
 with zipfile.ZipFile(tmp) as z:assert z.testzip() is None
 tmp.replace(archive);descriptor=R/'BUILD/v064_checkpoint_descriptor.json'
 save(descriptor,dict(version='v064',source_commit=os.environ['GITHUB_SHA'],source_run=int(os.environ['GITHUB_RUN_ID']),file=archive.name,
  bytes=archive.stat().st_size,sha256=sha(archive),terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
  approved_preview_commit='d0660a9a8b7be9ce30de60479a0498872deb7a4f',expected_inputs_sha256=sha(S/'native_expected_inputs.json'),checked_source=True,
  all_active_terrain_bitmaps_and_shaders_included=True,reused_native_scenery=read(R/'BUILD/v064_recovered_inputs.json')))
 rel=api('/releases',dict(tag_name='v064-hybrid-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],
  name='Orlando MX v064 — B corners / C loam; native build pending',draft=True,prerelease=True,make_latest='false',
  body='User-approved original B through all corners, original C elsewhere, with blended transitions and proposed daylight. Preserves the low wall-entry roller, Express van/sign and alternating black/silver Cybertrucks. Exact approved source checks passed; native terrain/collision compilation pending.'))
 for p in [archive,descriptor,S/'native_expected_inputs.json',O/'precompile_validation.json',O/'native_staging_validation.json']:upload(rel,p)
 with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as f:f.write('V064_RELEASE_ID='+str(rel['id'])+'\n')
 print('V064_SOURCE_CHECKPOINT_SAVED',rel['id'],rel['tag_name'],flush=True)

def preserve_native():
 rel=release()
 for p in [R/'12_RELEASE/OrlandoMX_2026_v064.pkz',R/'12_RELEASE/OrlandoMX_2026_v064.pkz.sha256',O/'native_compile_results.json']:upload(rel,p)

def deliver():
 identity();q=read(R/'12_RELEASE/OrlandoMX_v064_Validation.json')
 assert all(q[k] for k in ['compiled','source_checks','centerline_merged','native_collision_exact_accepted_source','wall_roller_visual_collision_exact',
  'all_14_corner_heights_exact_v060','scenery_vehicles_sign_exact_v060','approved_daylight_exact','package_integrity_passed','package_size_budget_passed'])
 assert q['native_object_textures']['checks_pass'] and all(v['checks_pass'] for v in q['source_validation'].values())
 assert q['native_height_validation']['checks_pass'] and q['native_height_validation']['wall_roller_visual_and_collision_exact']
 p=R/'12_RELEASE/OrlandoMX_2026_v064.pkz';assert sha(p)==q['pkz_sha256'] and p.stat().st_size<=964987509
 rel=release();assert rel['target_commitish']==q['source_commit']
 for name in ['OrlandoMX_v064_Validation.json','Install_v064.txt']:upload(rel,R/'12_RELEASE'/name)
 for name in ['native_height_validation.json','native_staging_validation.json']:upload(rel,O/name)
 body=f'''Approved original style B flowing cultivation throughout all 14 corners, with original style C ridden loam on straights, jump faces, landings and start lane. Five metre entry/exit blends join the methods. Includes the approved photographic contrast and clear-day ambient/fog settings. Texture dimensions, source allocation and 14 layers are unchanged.

Includes the low, rounded wall-entry roller before the large speedway double, landing on the original asphalt. Every other terrain sample is exact to v060. Scenery is byte-exact to v060 and its authenticated native EDF is reused: Chevrolet Express, readable cardboard sign, alternating black/silver trucks, roads and all other scenery remain intact.

Official TerrainEd collision and visual compilation and TrackEd route merge passed. All 4,198,401 visual and collision height samples match the approved roller source. Native terrain/object bitmap payloads, scenery coordinate probes, matte foliage, retained race data, approved lighting hash and 13-entry archive CRC passed. Package: {q['pkz_bytes']:,} bytes. Actual MX Bikes appearance, riding, roller clearance, RAM/VRAM and FPS still require the user's game test. All players need the same PKZ.'''
 rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v064 — B corners, C loam and wall roller',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
 asset=next(a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name);assert asset['size']==q['pkz_bytes'] and asset['digest']=='sha256:'+q['pkz_sha256']
 save(R/'BUILD/v064_delivery.json',dict(release_url=rel['html_url'],download_url=asset['browser_download_url'],release_id=rel['id'],
  pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes'],source_commit=q['source_commit']))
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write('[Download validated v064 PKZ]('+asset['browser_download_url']+')\n\n[Validation and install notes]('+rel['html_url']+')\n')
 print('V064_DOWNLOAD',asset['browser_download_url'],flush=True)

def diagnostics():
 if not os.environ.get('V064_RELEASE_ID'):return
 p=R/'BUILD'/('v064-diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for f in [*sorted((R/'DOCUMENTATION').glob('*v064*')),*sorted(O.glob('*validation.json'))]:
   if f.is_file():z.write(f,f.relative_to(R).as_posix())
 upload(release(),p)

if __name__=='__main__':{'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
