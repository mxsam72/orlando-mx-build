"""Pinned tested terrain and saved, approved v057 source/native scenery."""
import os,shutil,sys,urllib.request,urllib.error,urllib.parse,zipfile
from pathlib import Path
from v057_inputs import R,BASE,PREV,sha,save,restore as restore_tested
from v052_transfer import api,HEADERS,extract,safe

O=R/'V058_OUTPUT';M=O/'materials';NAME='orlandomx_2026_v058';DEST=R/'12_RELEASE'/NAME
SAVED=R/'BUILD/v058_native_scenery'
RELEASE_ID=413398508
PINS={
 'OrlandoMX-v057-source-checkpoint.zip':(642577865,493569965,'0d5132bc2988ceef2acdaf72abcc2ff83817109e349a59755a87c7acf8a72169'),
 'v057_checkpoint_descriptor.json':(642582035,616,'583431f7d8a176a7b8e8b3d9c20e3d5b91508bed188614506d3723bcbf60775e'),
 'OrlandoMX-v057-native-scenery.zip':(642593580,229447666,'c2f0a27e90d92989080145c6131677bec77131563e7c529b6ce717f4dc4e8c43')}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def saved_asset(name,pin):
 aid,size,digest=pin;p=R/'BUILD/v058_inputs'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.stat().st_size==size and sha(p)==digest:return p
 url='https://api.github.com/repos/mxsam72/orlando-mx-build/releases/assets/'+str(aid)
 req=urllib.request.Request(url,headers=HEADERS|{'Accept':'application/octet-stream'})
 try:response=urllib.request.build_opener(NoRedirect()).open(req,timeout=300)
 except urllib.error.HTTPError as error:
  if error.code not in [301,302,303,307,308]:raise
  target=error.headers['Location'];parsed=urllib.parse.urlsplit(target)
  assert parsed.scheme=='https' and parsed.hostname.endswith('.githubusercontent.com')
  # A fresh unauthenticated request never forwards the GitHub token to storage.
  response=urllib.request.urlopen(target,timeout=300)
 with response as src,p.with_suffix('.part').open('wb') as out:shutil.copyfileobj(src,out,4*1024*1024)
 part=p.with_suffix('.part');assert part.stat().st_size==size and sha(part)==digest,name;part.replace(p)
 print('Verified saved v057 asset',name,size,flush=True);return p

def restore():
 restore_tested();rel=api('/releases/'+str(RELEASE_ID));assert rel['tag_name']=='v057-loam-express-38677167308'
 assets={a['name']:a for a in rel['assets']}
 for name,(aid,size,digest) in PINS.items():
  a=assets[name];assert a['id']==aid and a['size']==size and a['digest']=='sha256:'+digest
  saved_asset(name,PINS[name])
 folder=R/'BUILD/v058_inputs'
 keep={'scenery.fbx','scenery_validation.json','native_probes.json','vehicle_meshes.json'}
 with zipfile.ZipFile(folder/'OrlandoMX-v057-source-checkpoint.zip') as z:
  assert z.testzip() is None
  for item in z.infolist():
   safe(item.filename)
   if not item.is_dir() and (item.filename in {'V057_OUTPUT/'+n for n in keep} or item.filename.startswith('V057_OUTPUT/facility_textures/')):
    extract(z,item,R/item.filename)
 import json
 descriptor=json.loads((folder/'v057_checkpoint_descriptor.json').read_text())
 assert descriptor['source_commit']=='8903065aca3301fd0eed0522738f370eb69743ca' and descriptor['checked_source']
 assert sha(R/'V057_OUTPUT/scenery.fbx')==descriptor['scenery_sha256']
 SAVED.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(folder/'OrlandoMX-v057-native-scenery.zip') as z:
  assert z.testzip() is None and set(z.namelist())=={'scenery.edf','fbx2edf_v057.log'}
  for name in z.namelist():extract(z,z.getinfo(name),SAVED/name)
 assert (SAVED/'scenery.edf').read_bytes()[:4]==b'EDF\0'
 save(R/'BUILD/v058_input_validation.json',dict(checks_pass=True,pinned_saved_assets=PINS,
  scenery_source_sha256=descriptor['scenery_sha256'],scenery_edf_sha256=sha(SAVED/'scenery.edf'),
  approved_source_commit=descriptor['source_commit'],reused_saved_native_scenery=True))
 for p in folder.glob('*.zip'):p.unlink()
 print('V058_PINNED_APPROVED_SCENERY_AND_TESTED_TERRAIN_RECOVERED',flush=True)

if __name__=='__main__':restore()
