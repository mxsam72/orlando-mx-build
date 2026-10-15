"""Recover checksum-pinned delivered v056 and its complete accepted source stack."""
import concurrent.futures
import os
import shutil
import sys
import urllib.request
import zipfile
from v052_transfer import HEADERS,api,identity,safe,extract
from v048_surface import R,BASE,sha,save

PREV=R/'V056_OUTPUT'
O=R/'V057_OUTPUT'
M=O/'materials'
NAME='orlandomx_2026_v057'
DEST=R/'12_RELEASE'/NAME
TAG='v056-restored-corners-38665837940'
PINS={
 'OrlandoMX-v056-source-checkpoint.zip':(283975905,'2341678f44193466ee81a1e37cadf61c881a6f1dccd9222a7d4494caf330f4cd'),
 'OrlandoMX_v056_Validation.json':(126754,'e0a0e9f63e743e090c6226e784c3a50535f657d6cb1549faf1c4d68f8ef3ba25')
}

def download(item):
 name,(size,digest)=item;p=R/'BUILD/v057_inputs'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if not(p.exists() and p.stat().st_size==size and sha(p)==digest):
  with urllib.request.urlopen('https://github.com/mxsam72/orlando-mx-build/releases/download/'+TAG+'/'+name,timeout=300) as stream,p.with_suffix('.part').open('wb') as out:
   shutil.copyfileobj(stream,out,4*1024*1024)
  part=p.with_suffix('.part');assert part.stat().st_size==size and sha(part)==digest,name;part.replace(p)
 print('Verified v056 input',name,size,flush=True)
 return p

def current():
 identity();rel=api('/releases/tags/'+TAG);assert rel['id']==413330986 and not rel['draft']
 assets={a['name']:a for a in rel['assets']}
 for name,(size,digest) in PINS.items():assert assets[name]['size']==size and assets[name]['digest']=='sha256:'+digest,name
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(download,PINS.items()))
 folder=R/'BUILD/v057_inputs'
 with zipfile.ZipFile(folder/'OrlandoMX-v056-source-checkpoint.zip') as z:
  assert z.testzip() is None
  for i in z.infolist():
   safe(i.filename)
   if not i.is_dir() and i.filename.startswith(('V056_OUTPUT/','12_RELEASE/orlandomx_2026_v056/')):extract(z,i,R/i.filename)
 assert sha(PREV/'terrain.raw')=='ab99df42094ef29015f117babeffe555e814fc7f86cf836c60625b760868289f'
 assert sha(PREV/'scenery.fbx')=='c3ce33f0ed156031fd9d75a87d4786777333ac9097b7635b0fd23e06e3957389'
 save(R/'BUILD/v057_input_validation.json',dict(checks_pass=True,baseline='delivered v056, user-tested',pins=PINS,terrain_sha256=sha(PREV/'terrain.raw'),scenery_sha256=sha(PREV/'scenery.fbx')))
 (folder/'OrlandoMX-v056-source-checkpoint.zip').unlink()
 print('Delivered v056 source recovered exactly',flush=True)

def restore():
 from v056_inputs import restore as base_restore
 base_restore();current()

if __name__=='__main__':
 if not os.environ.get('V052_RELEASE_TOKEN'):HEADERS.pop('Authorization',None)
 {'restore':restore,'current':current}[sys.argv[1]]()
