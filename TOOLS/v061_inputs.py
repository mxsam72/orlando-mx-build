"""Pinned v060 source and its immutable material dependencies for review only."""
import concurrent.futures,io,json,os,shutil,zipfile,urllib.request
from pathlib import Path
from v048_surface import R,sha,save
from download_v048_inputs import INPUTS
from v054_inputs import EXTRA
from v056_inputs import PINS as P54,TAG as T54
from v057_inputs import PINS as P56,TAG as T56

PREV=R/'V060_OUTPUT';O=R/'V061_OUTPUT';M=O/'materials';S=R/'V061_SOURCE'
CACHE=R/'BUILD/v061_inputs'
PINS={k:INPUTS[k] for k in ['v044_source.zip','v046_source.zip']}
PINS['v052_source.zip']=EXTRA['v052_source.zip']
for key,tag,pins,name in [('v054_source.zip',T54,P54,'OrlandoMX-v054-source-checkpoint.zip'),('v056_source.zip',T56,P56,'OrlandoMX-v056-source-checkpoint.zip')]:
 size,digest=pins[name];PINS[key]=(tag+'/'+name,size,digest)
PINS['v060_source.zip']=('v060-dense-grooming-38699998845/OrlandoMX-v060-source-checkpoint.zip',561608311,'d2d62ebb120323bfc55a6e30bf6a851b5b2b882c64d0cbed6d6248b72cff73a5')

def download(item):
 name,(suffix,size,digest)=item;CACHE.mkdir(parents=True,exist_ok=True);dest=CACHE/name
 existing=CACHE/'OrlandoMX-v060-source-checkpoint.zip'
 if name=='v060_source.zip' and existing.exists() and sha(existing)==digest:return existing
 if dest.exists() and dest.stat().st_size==size and sha(dest)==digest:return dest
 temp=dest.with_suffix('.downloading');req=urllib.request.Request('https://github.com/mxsam72/orlando-mx-build/releases/download/'+suffix,headers={'User-Agent':'OrlandoMX-v061-review'})
 with urllib.request.urlopen(req,timeout=120) as inp,temp.open('wb') as out:
  shutil.copyfileobj(inp,out,4*1024*1024);out.flush();os.fsync(out.fileno())
 assert temp.stat().st_size==size and sha(temp)==digest,name
 temp.replace(dest);os.utime(dest,None);print('VERIFIED_DEPENDENCY',name,size,flush=True);return dest

def extract(z,name,dest):
 assert not Path(name).is_absolute() and '..' not in Path(name).parts
 dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_name(dest.name+'.extracting')
 with z.open(name) as inp,temp.open('wb') as out:shutil.copyfileobj(inp,out,4*1024*1024);out.flush();os.fsync(out.fileno())
 temp.replace(dest);os.utime(dest,None)

def restore():
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:files=dict(zip(PINS,pool.map(download,PINS.items())))
 for key,path in files.items():
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None,key
   for name in z.namelist():
    p=Path(name)
    if name.endswith('/'):continue
    keep=False
    if key=='v060_source.zip':keep=name.startswith(('V060_OUTPUT/','V058_OUTPUT/materials/','V059_OUTPUT/materials/')) and not p.name.startswith('.')
    else:
     folder={'v044_source.zip':'V044_OUTPUT','v046_source.zip':'V046_OUTPUT','v052_source.zip':'V052_OUTPUT','v054_source.zip':'V054_OUTPUT','v056_source.zip':'V056_OUTPUT'}[key]
     keep=name.startswith((folder+'/materials/',folder+'/masks/')) and p.suffix in ['.tga','.shd','.flg']
     keep|=name==folder+'/v024_pit_gravel.tga'
    if keep:extract(z,name,R/name)
   if key=='v044_source.zip':
    # Concatenate nested ZIP parts on disk instead of retaining a second
    # gigabyte-sized copy in memory just to recover these two fixed images.
    nested=R/'BUILD/v061_cache/original_native_inputs.zip';nested.parent.mkdir(parents=True,exist_ok=True)
    with nested.open('wb') as out:
     for name in sorted(n for n in z.namelist() if n.startswith('BUILD_INPUTS/native_inputs.zip.part')):
      with z.open(name) as inp:shutil.copyfileobj(inp,out,4*1024*1024)
    with zipfile.ZipFile(nested) as inner:
     for name,dest in [('05_NORMALS/grass_n.tga',R/'V044_OUTPUT/grass_n.tga'),('04_TEXTURES/basemap.tga',R/'V044_OUTPUT/basemap.tga')]:extract(inner,name,dest)
     tht=next(n for n in inner.namelist() if Path(n).name=='track.tht');extract(inner,tht,R/'BUILD/v054_track.tht')
    nested.unlink()
 print('V061_PINNED_BASELINE_MATERIALS_RESTORED',flush=True)

def candidates(name):
 for folder in [PREV/'materials',R/'V059_OUTPUT/materials',R/'V058_OUTPUT/materials',R/'V056_OUTPUT/materials',R/'V054_OUTPUT/materials',R/'V052_OUTPUT/materials',R/'V046_OUTPUT/materials',R/'V044_OUTPUT/materials',R/'V044_OUTPUT']:
  yield folder/name
 if name.startswith('mask_'):yield R/'V044_OUTPUT/masks'/name[5:]

_expected=None;_resolved={}
def baseline(name):
 global _expected
 if name in _resolved:return _resolved[name]
 if _expected is None:
  q=json.loads((PREV/'surface_validation.json').read_text());_expected={r['file']:r['sha256'] for r in q['active_terrain_inventory']+q['active_shaders']}
 paths=[p for p in candidates(name) if p.is_file()]
 for p in paths:
  if name not in _expected or sha(p)==_expected[name]:_resolved[name]=p;return p
 raise FileNotFoundError((name,'No exact v060 source found',[str(p) for p in paths]))

def source(name):return M/name if (M/name).is_file() else baseline(name)

if __name__=='__main__':restore()
