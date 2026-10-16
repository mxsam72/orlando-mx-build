"""Checkpoint the complete corrected source and publish a validated native v065."""
import json,os,sys,zipfile
from pathlib import Path
from v052_transfer import api,identity,upload
from v065_inputs import R,O,S,NAME,DEST,source,sha,save

def read(p):return json.loads(Path(p).read_text())
def release():
 rel=api('/releases/'+os.environ['V065_RELEASE_ID'])
 assert rel['draft'] and rel['tag_name'].startswith('v065-start-C-');return rel

def checkpoint():
 identity()
 for label in ['terrain','surface','scenery','race','precompile','native_staging']:assert read(O/(label+'_validation.json'))['checks_pass']
 archive=R/'BUILD/OrlandoMX-v065-source-checkpoint.zip';tmp=archive.with_suffix('.writing.zip');written=set()
 with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  def add(p,name=None):
   p=Path(p);name=name or p.relative_to(R).as_posix()
   if name not in written:z.write(p,name);written.add(name)
  for folder in [O,S,DEST]:
   for p in sorted(folder.rglob('*')):
    if p.is_file():add(p)
  surface=read(O/'surface_validation.json')
  for row in surface['active_terrain_inventory']+surface['active_shaders']:add(source(row['file']),'V065_OUTPUT/materials/'+row['file'])
  staging=read(O/'native_staging_validation.json');pdir=R/'BUILD/v065_stage'
  for name in staging['object_texture_files']:
   add(pdir/name,'V065_OUTPUT/facility_textures/'+name)
   for ext in ['.shd','.flg']:
    p=(pdir/name).with_suffix(ext)
    if p.is_file():add(p,'V065_OUTPUT/facility_textures/'+p.name)
  for p in sorted((R/'TOOLS').glob('*v065*.py')):add(p)
  for name in ['v054_track.tht','edf_params.ini','trh_params.ini','map_params.ini','tool_versions.json','v065_recovered_inputs.json']:add(R/'BUILD'/name)
  for name in ['track.tht','map_params.ini']:add(pdir/name)
 with zipfile.ZipFile(tmp) as z:assert z.testzip() is None
 tmp.replace(archive);descriptor=R/'BUILD/v065_checkpoint_descriptor.json'
 save(descriptor,dict(version='v065',source_commit=os.environ['GITHUB_SHA'],source_run=int(os.environ['GITHUB_RUN_ID']),file=archive.name,
  bytes=archive.stat().st_size,sha256=sha(archive),terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
  all_active_terrain_bitmaps_and_shaders_included=True,checked_source=True,reused_native_scenery=read(R/'BUILD/v065_recovered_inputs.json')))
 rel=api('/releases',dict(tag_name='v065-start-C-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],
  name='Orlando MX v065 — C start dirt and cleared left strip; native build pending',draft=True,prerelease=True,make_latest='false',
  body='Corrects missing C texture coverage over the opening start straight and clears the circled grass ground strip on its left. Retains the approved B corners, C course, low wall roller and every scenery byte. Existing image sizes, slots and 14 layers remain unchanged. Native compilation pending.'))
 for p in [archive,descriptor,S/'native_expected_inputs.json',O/'precompile_validation.json',O/'native_staging_validation.json']:upload(rel,p)
 with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as f:f.write('V065_RELEASE_ID='+str(rel['id'])+'\n')
 print('V065_SOURCE_CHECKPOINT_SAVED',rel['id'],flush=True)

def preserve_native():
 rel=release()
 for p in [R/'12_RELEASE/OrlandoMX_2026_v065.pkz',R/'12_RELEASE/OrlandoMX_2026_v065.pkz.sha256',O/'native_compile_results.json']:upload(rel,p)

def deliver():
 identity();q=read(R/'12_RELEASE/OrlandoMX_v065_Validation.json')
 assert all(q[k] for k in ['compiled','source_checks','centerline_merged','native_collision_exact_accepted_source','wall_roller_visual_collision_exact',
  'scenery_vehicles_sign_exact_v060','approved_daylight_exact','package_integrity_passed','package_size_budget_passed'])
 assert q['native_object_textures']['checks_pass'] and q['native_height_validation']['checks_pass']
 assert all(v['checks_pass'] for v in q['source_validation'].values())
 surface=q['source_validation']['surface_validation'];assert surface['start_C_full_opening_coverage'] and surface['circled_visual_grass_strip_removed']
 p=R/'12_RELEASE/OrlandoMX_2026_v065.pkz';assert sha(p)==q['pkz_sha256'];rel=release();assert rel['target_commitish']==q['source_commit']
 for name in ['OrlandoMX_v065_Validation.json','Install_v065.txt']:upload(rel,R/'12_RELEASE'/name)
 for name in ['native_height_validation.json','native_staging_validation.json','surface_validation.json']:upload(rel,O/name)
 body=f'''Style C photographic dirt now covers the previously missing opening start straight. The circled grass ground strip on its left is cleared, with a blended shoulder and pit grass outside the scoped area retained. Original B corners and the rest of the C course remain intact.

All terrain heights and every scenery byte are exact to v064, preserving the low wall-entry roller, large speedway double, Chevrolet Express and sign, and black/silver Cybertrucks. Race data and approved game lighting are retained. Existing texture dimensions, slots and 14 layers are unchanged, with no increase in source texture allocation.

Official TerrainEd compilation and TrackEd route merge passed. All 4,198,401 visual and collision samples match the approved source; native bitmap payloads, scenery probes, matte foliage and archive CRC passed. Package: {q['pkz_bytes']:,} bytes. Actual game appearance, riding, RAM/VRAM and FPS need the user's test. All players need this PKZ.'''
 rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v065 — C start dirt and cleared left grass strip',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
 asset=next(a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name)
 assert asset['size']==q['pkz_bytes'] and asset['digest']=='sha256:'+q['pkz_sha256']
 save(R/'BUILD/v065_delivery.json',dict(release_url=rel['html_url'],download_url=asset['browser_download_url'],release_id=rel['id'],pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes'],source_commit=q['source_commit']))
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write('[Download validated v065 PKZ]('+asset['browser_download_url']+')\n\n[Validation and install notes]('+rel['html_url']+')\n')
 print('V065_DOWNLOAD',asset['browser_download_url'],flush=True)

def diagnostics():
 if not os.environ.get('V065_RELEASE_ID'):return
 p=R/'BUILD'/('v065-diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for f in [*sorted((R/'DOCUMENTATION').glob('*v065*')),*sorted(O.glob('*validation.json'))]:
   if f.is_file():z.write(f,f.relative_to(R).as_posix())
 upload(release(),p)

if __name__=='__main__':{'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
