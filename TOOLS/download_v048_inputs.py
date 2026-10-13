"""Restore authenticated published inputs for the v048 visual-only sample."""
from pathlib import Path
import concurrent.futures, hashlib, urllib.request, json, time

REPO = 'https://github.com/mxsam72/orlando-mx-build/releases/download/'
INPUTS = {
 'v044_source.zip': ('untagged-281f90b2ce09d3a57800/OrlandoMX-v044-source-checkpoint.zip', 1599713927, '1c45844424b0f8e9384a9344f0563b6f108e5003f699c71430dc499166bff881'),
 'v046_source.zip': ('v046-persistent-dirt-38405384917/OrlandoMX-v046-dirt-source-checkpoint.zip', 304060299, 'ee9f0d2475865f437ac321379708226f3950129bb8901c5c64a1a253a1ee2a8d'),
 'v047.pkz': ('v047-realistic-trees-38458081921/OrlandoMX_2026_v047.pkz', 917973744, 'f841c49859be1fe34c9e5641d39ed2b3f7eaabb981f55660a1b1b5f9fb4cf783'),
 'v047_native.zip': ('v047-realistic-trees-38458081921/OrlandoMX-v047-native-scenery.zip', 226150374, 'ebc41d61f88d7b661ce9b380a0efb108c21f3db6efd5775e7cee3a69fcd21fe7'),
 'v047_validation.json': ('v047-realistic-trees-38458081921/OrlandoMX_v047_Validation.json', 905430, '8a122933bd61eb4851f59e15750b70e169992b6fbaafbcbecb7899b4cb97c461'),
 'v046_validation.json': ('v046-persistent-dirt-38405384917/OrlandoMX_v046_Validation.json', 35757, '137d601415687f7231c46d2b98c29076bd179a8edce8c21130d9fb9ea8868a0b'),
}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
 return h.hexdigest()

def download(item):
 name,(url,size,digest)=item; path=Path('BUILD/v048_inputs')/name; path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists() and path.stat().st_size==size and sha(path)==digest:
  print('cached',name,flush=True); return
 for attempt in range(4):
  try:
   req=urllib.request.Request(REPO+url,headers={'User-Agent':'OrlandoMX-v048-authoring'})
   with urllib.request.urlopen(req,timeout=120) as response, path.with_suffix(path.suffix+'.part').open('wb') as f:
    while block:=response.read(4*1024*1024): f.write(block)
   part=path.with_suffix(path.suffix+'.part')
   assert part.stat().st_size==size, (name,part.stat().st_size,size)
   assert sha(part)==digest, name+' SHA256 mismatch'
   part.replace(path); print('verified',name,size,flush=True); return
  except Exception as exc:
   print('retry',name,attempt+1,str(exc),flush=True)
   if attempt==3: raise
   time.sleep(2+attempt)

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(download,INPUTS.items()))
