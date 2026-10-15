"""Preserve final inputs and publish only a completely validated native package."""
import os,sys,zipfile
from v052_transfer import api,identity,upload
from v060_inputs import R,O,S,NAME,DEST,sha,save
from v054_geometry import read

def release():
 rel=api('/releases/'+os.environ['V060_RELEASE_ID'])
 assert rel['draft'] and rel['tag_name'].startswith('v060-dense-grooming-')
 return rel

def checkpoint():
 identity()
 for name in ['terrain_validation','surface_validation','scenery_validation','race_validation','precompile_validation']:
  assert read(O/(name+'.json'))['checks_pass']
 archive=R/'BUILD/OrlandoMX-v060-source-checkpoint.zip';temporary=archive.with_suffix('.zip.writing')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  # All new source, original approved C+B overlays, and the v059 underlay
  # are preserved. Older immutable dependencies have authenticated pins.
  for folder in [O,DEST,S,R/'V058_OUTPUT/materials',R/'V059_OUTPUT/materials',R/'V059_SOURCE']:
   for p in sorted(folder.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(R).as_posix())
  for p in sorted((R/'TOOLS').glob('*v060*.py')):z.write(p,p.relative_to(R).as_posix())
  for name in ['v054_input_validation.json','v057_input_validation.json','v058_input_validation.json']:
   p=R/'BUILD'/name;z.write(p,p.relative_to(R).as_posix())
 with temporary.open('rb') as f:os.fsync(f.fileno())
 with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
 temporary.replace(archive)
 descriptor=R/'BUILD/v060_checkpoint_descriptor.json'
 save(descriptor,dict(version='v060',source_commit=os.environ['GITHUB_SHA'],source_run=int(os.environ['GITHUB_RUN_ID']),
  file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),terrain_sha256=sha(O/'terrain.raw'),
  scenery_sha256=sha(O/'scenery.fbx'),surface_validation_sha256=sha(O/'surface_validation.json'),checked_source=True))
 rel=api('/releases',dict(tag_name='v060-dense-grooming-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],
  name='Orlando MX v060 — tighter grooming; native build pending',
  body='Approved C+B dirt with denser added grooming in all existing areas. Irregular gaps capped at 0.3m, unchanged texture allocation. v059 bank smoothing and jump-pair move retained, along with the approved Express, sign and Cybertruck changes. Native compilation pending.',
  draft=True,prerelease=True,make_latest='false'))
 for p in [archive,descriptor]:upload(rel,p)
 for p in sorted(S.glob('*.json')):upload(rel,p)
 with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as env:env.write('V060_RELEASE_ID='+str(rel['id'])+'\n')
 print('V060_SOURCE_RELEASE',rel['id'],rel['tag_name'],flush=True)

def preserve_edf():
 archive=R/'BUILD/OrlandoMX-v060-native-scenery.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.write(R/'BUILD/v060_stage/scenery.edf','scenery.edf');z.write(R/'DOCUMENTATION/fbx2edf_v060.log','fbx2edf_v060.log')
 upload(release(),archive)

def preserve_native():
 rel=release()
 for p in [R/'12_RELEASE/OrlandoMX_2026_v060.pkz',R/'12_RELEASE/OrlandoMX_2026_v060.pkz.sha256',O/'native_compile_results.json']:upload(rel,p)

def deliver():
 identity();q=read(R/'12_RELEASE/OrlandoMX_v060_Validation.json')
 assert all(q[k] for k in ['compiled','source_checks','centerline_merged','native_collision_exact_accepted_source','package_integrity_passed','package_size_budget_passed'])
 assert q['native_object_textures']['checks_pass'] and all(v['checks_pass'] for v in q['source_validation'].values())
 assert q['native_height_validation']['checks_pass'] and q['native_height_validation']['native_all_14_corner_grids_exact_v059']
 assert q['estimated_source_texture_and_geometry_budget_not_increased']
 p=R/'12_RELEASE/OrlandoMX_2026_v060.pkz';assert sha(p)==q['pkz_sha256'] and p.stat().st_size<=964987509
 rel=release();assert rel['target_commitish']==q['source_commit']
 for name in ['OrlandoMX_v060_Validation.json','Install_v060.txt']:upload(rel,R/'12_RELEASE'/name)
 for name in ['native_height_validation.json','native_staging_validation.json']:upload(rel,O/name)
 body=f'''Approved C photographic loam with B jump grooves across the track. All 16 existing perpendicular grooming regions (14 corners, R04 and R14 face) now use denser, irregular spacing capped at 0.3m. The added lengthwise tines across R03/R07 are tightened too. Original photo colours, fine normals, masks, boundaries and terrain material layers remain exact to v059. No new texture slots or layers; source texture allocation is unchanged.

Retains the approved v059 geometry: smoother corner 03/09 bank transitions and the second/third R11 mound pair translated forward 9.9m while retaining 9.9m crest spacing. All other jump crests, the first single, asphalt courses and race/reset files remain fixed. Three affected edge markers stay seated on the ground. The approved black Chevrolet Express, readable solid cardboard FREE CANDY sign and alternating 3 black/2 stainless Cybertrucks are retained.

Official native scenery, collision and visual terrain compilation completed. All 4,198,401 visual and collision height samples match the accepted source. Native terrain/object bitmap payloads, scenery coordinate probes, matte foliage, race-file hashes, merged centerline and 13-entry ZIP CRC passed. Package: {q['pkz_bytes']:,} bytes. Actual MX Bikes appearance, riding, RAM/VRAM and FPS still need a game test. All players need the same PKZ.'''
 rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v060 — tighter grooming and approved C+B dirt',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
 asset=next(a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name)
 assert asset['size']==q['pkz_bytes'] and asset['digest']=='sha256:'+q['pkz_sha256']
 save(R/'BUILD/v060_delivery.json',dict(release_url=rel['html_url'],download_url=asset['browser_download_url'],release_id=rel['id'],
  pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes'],source_commit=q['source_commit']))
 summary=os.environ.get('GITHUB_STEP_SUMMARY')
 if summary:
  with open(summary,'a',encoding='utf-8') as f:f.write('[Download validated v060 PKZ]('+asset['browser_download_url']+')\n\n[Build validation and installation notes]('+rel['html_url']+')\n')
 print('V060_DOWNLOAD',asset['browser_download_url'],flush=True)

def diagnostics():
 if not os.environ.get('V060_RELEASE_ID'):return
 p=R/'BUILD'/('v060-diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for f in [*sorted((R/'DOCUMENTATION').glob('*v060*')),*sorted(O.glob('*validation.json'))]:
   if f.is_file():z.write(f,f.relative_to(R).as_posix())
 upload(release(),p)

if __name__=='__main__':{'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
