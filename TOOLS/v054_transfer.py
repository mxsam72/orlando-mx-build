"""Checkpoint reviewed v054 sources and publish only verified native builds."""
import base64,json,os,shutil,sys,urllib.request,zipfile
from pathlib import Path
from v052_transfer import api,identity,upload,safe,extract,HEADERS
from v054_geometry import R,BASE,PREV,O,DEST,NAME,read,sha,save
from resume_v052 import NoAuthRedirect

def source():
 from v054_inputs import restore
 restore();O.mkdir(parents=True,exist_ok=True);shutil.copytree(PREV,O,dirs_exist_ok=True)

def checkpoint():
 identity()
 checks=['terrain_validation','surface_validation','scenery_validation','race_validation','independent_validation','native_route_validation']
 assert all(read(O/(n+'.json'))['checks_pass'] for n in checks)
 review=R/'BUILD/v054_review';assert read(review/'manifest.json')['source_only']
 archive=R/'BUILD/OrlandoMX-v054-source-checkpoint.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for folder in [O,DEST,review,R/'V054_SOURCE']:
   if not folder.exists():continue
   for p in sorted(folder.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(R).as_posix())
  for p in sorted((R/'TOOLS').glob('*v054*.py')):z.write(p,p.relative_to(R).as_posix())
 descriptor=R/'BUILD/v054_checkpoint_descriptor.json';save(descriptor,dict(version='v054',baseline='v052',source_commit=os.environ['GITHUB_SHA'],source_run=int(os.environ['GITHUB_RUN_ID']),file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),checked_source=True))
 rel=api('/releases',dict(tag_name='v054-start-corners-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX v054 A/B/C starting path and corners — native build pending',body='User-authorized A/B/C changes from delivered v052. Exact v052 soil colour and photographic tiles retained. Source geometry, lane grade, masks, scenery clearance and race references checked; native compilation pending.',draft=True,prerelease=True,make_latest='false'))
 for p in [archive,descriptor]:upload(rel,p)
 for p in sorted(review.iterdir()):
  if p.is_file():upload(rel,p)
 print('V054_SOURCE_RELEASE',rel['id'],rel['tag_name'],flush=True)
 with open(os.environ['GITHUB_ENV'],'a') as env:env.write('V054_RELEASE_ID='+str(rel['id'])+'\n')
 # Browser-viewable images use a separate folder; no large track files go in git.
 branch=os.environ['GITHUB_REF_NAME'];head=api('/git/ref/heads/'+branch)['object']['sha'];base=api('/git/commits/'+head);entries=[]
 files={p.name:p.read_bytes() for p in review.iterdir() if p.suffix in ['.png','.jpg']}
 text='''# v054 A/B/C starting-path revision\n\nv052 is the approved baseline. The cancelled v053 dirt changes are not included. These are source geometry/material previews; scenery is omitted from the material views, and these are not MX Bikes screenshots.\n\n## Paths\n\n![Path comparison](v054_path_comparison.png)\n\n## Start and wider A corner — v052 left, v054 right\n\n![Start and A](comparison_start_and_A.jpg)\n\n## Wider C entry to the eight rollers — v052 left, v054 right\n\n![Roller entry C](comparison_roller_entry_C.jpg)\n\n## Entry height — matched source views\n\n![v052 entry](v052_start_merge.jpg)\n\n![v054 entry](v054_start_merge.jpg)\n'''
 files['README.md']=text.encode()
 for name,data in files.items():
  blob=api('/git/blobs',dict(content=base64.b64encode(data).decode(),encoding='base64'));entries.append(dict(path='PREVIEWS/v054/'+name,mode='100644',type='blob',sha=blob['sha']))
 tree=api('/git/trees',dict(base_tree=base['tree']['sha'],tree=entries));commit=api('/git/commits',dict(message='Publish checked v054 A/B/C source comparisons',tree=tree['sha'],parents=[head]))
 assert api('/git/ref/heads/'+branch)['object']['sha']==head
 api('/git/refs/heads/'+branch,dict(sha=commit['sha'],force=False),method='PATCH')
 print('V054_PREVIEW_PAGE','https://github.com/mxsam72/orlando-mx-build/blob/'+branch+'/PREVIEWS/v054/README.md',flush=True)

def restore_checkpoint():
 identity();rid=os.environ['V054_SOURCE_RELEASE_ID'];rel=api('/releases/'+rid);assert rel['draft'] and rel['tag_name'].startswith('v054-start-corners-')
 assets={a['name']:a for a in rel['assets']}
 def get(name):
  a=assets[name];p=R/'BUILD'/name;p.parent.mkdir(parents=True,exist_ok=True)
  req=urllib.request.Request(a['url'],headers=HEADERS|{'Accept':'application/octet-stream'})
  with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=300) as src,p.open('wb') as target:shutil.copyfileobj(src,target,4*1024*1024)
  assert p.stat().st_size==a['size'] and a['digest']=='sha256:'+sha(p);return p
 descriptor=read(get('v054_checkpoint_descriptor.json'));assert descriptor['checked_source'] and descriptor['baseline']=='v052'
 p=get(descriptor['file']);assert sha(p)==descriptor['sha256'] and p.stat().st_size==descriptor['bytes']
 with zipfile.ZipFile(p) as z:
  for i in z.infolist():
   safe(i.filename)
   if not i.is_dir() and i.filename.startswith(('V054_OUTPUT/','12_RELEASE/orlandomx_2026_v054/','BUILD/v054_review/','V054_SOURCE/')):extract(z,i,R/i.filename)
 p.unlink();assert sha(O/'terrain.raw')==descriptor['terrain_sha256'] and sha(O/'scenery.fbx')==descriptor['scenery_sha256']
 save(R/'BUILD/v054_recovery.json',dict(checks_pass=True,source_release_id=int(rid),descriptor=descriptor,reviewed_source_recovered_exact=True))
 with open(os.environ['GITHUB_ENV'],'a') as env:env.write('V054_RELEASE_ID='+rid+'\n')
 print('V054_REVIEWED_SOURCE_RESTORED',rid,flush=True)

def preserve_native():
 rel=api('/releases/'+os.environ['V054_RELEASE_ID']);assert rel['draft']
 for name in ['OrlandoMX_2026_v054.pkz','OrlandoMX_2026_v054.pkz.sha256','OrlandoMX_v054_Validation.json','Install_v054.txt']:upload(rel,R/'12_RELEASE'/name)
def deliver():
 q=read(R/'12_RELEASE/OrlandoMX_v054_Validation.json');assert q['compiled'] and q['source_checks'] and q['centerline_merged'] and q['native_collision_updated'] and q['package_integrity_passed']
 assert q['native_object_textures']['checks_pass'] and q['package_size_budget_passed'] and q['source_validation']['independent_validation']['checks_pass']
 rel=api('/releases/'+os.environ['V054_RELEASE_ID']);assert rel['draft'];assert sha(R/'12_RELEASE/OrlandoMX_2026_v054.pkz')==q['pkz_sha256']
 preserve_native();body=f'''A/B/C geometry update from delivered v052.\n\nA: the corner moves outward, with a longer approach/return section to make room for the revised start. B: the start continues through the new space and enters through a smooth bank opening farther along the main corner. C: a broader sweep replaces the tight entry to the eight rollers.\n\nv052 photographic dirt colours, soil tiles, normal maps and matte foliage remain. R09's 50 m double profile and all eight R17 roller heights with 10 m crest spacing are retained. Only masks, directional atlas pixels, terrain and trackside objects touched by the changed corridors move. Starting gates and pits retain their world positions. Native main/start lines, checkpoint modes, sector one and reset stations follow the new route; the UI map is updated.\n\nSource terrain, grade, route/race and scenery checks passed. Matched source previews were reviewed. Official FBX2EDF, TerrainEd MAP/TRH and TrackEd centreline merge completed; native texture, vertex, collision and archive checks passed. PKZ {q['pkz_bytes']:,} bytes.\n\nIn-game load, gate-drop/first-lap timing, resets, riding and FPS require the user's ride test. All participants need the same package.'''
 rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v054 — wider A/C corners and clear new start entry',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
 save(R/'BUILD/v054_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes']))
 print('V054_RELEASE',rel['html_url'],flush=True);print('V054_DOWNLOAD',next(a['browser_download_url'] for a in api('/releases/'+str(rel['id']))['assets'] if a['name']=='OrlandoMX_2026_v054.pkz'),flush=True)
if __name__=='__main__':{'source':source,'checkpoint':checkpoint,'restore_checkpoint':restore_checkpoint,'deliver':deliver}[sys.argv[1]]()
