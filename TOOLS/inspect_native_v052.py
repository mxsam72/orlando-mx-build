"""Inspect the actual alpha-only native specular record from the saved EDF."""
import hashlib,json,mmap,os,shutil,struct,urllib.request,zipfile
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];OUT=R/'BUILD/v052_native_specular_inspection'
ASSET='https://api.github.com/repos/mxsam72/orlando-mx-build/releases/assets/639758797'
SIZE=228735599;SHA='1967697ea9e16a6a8ad12c73b1fef10a4d25472fcffac209cc1be35ede41aff3'
class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  out=super().redirect_request(req,fp,code,msg,headers,newurl)
  if out is not None:out.remove_header('Authorization');out.remove_header('Accept')
  return out
def main():
 OUT.mkdir(parents=True,exist_ok=True);p=OUT/'native.zip'
 req=urllib.request.Request(ASSET,headers={'Authorization':'Bearer '+os.environ['V052_RELEASE_TOKEN'],'Accept':'application/octet-stream','User-Agent':'OrlandoMX-v052-record-inspection'})
 with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=180) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
 assert p.stat().st_size==SIZE and hashlib.sha256(p.read_bytes()).hexdigest()==SHA
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  with z.open('scenery.edf') as src,(OUT/'scenery.edf').open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
 report={}
 with (OUT/'scenery.edf').open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  assert raw[:4]==b'EDF\0'
  for name in ['v052_foliage_specular','pine_bark_n','CK_TREE_v047_pine']:
   key=name.encode()+bytes(100-len(name));pos=raw.find(key);rows=[]
   while pos>=0:
    b=raw[pos:pos+512];(OUT/(name+'_'+str(pos)+'.bin')).write_bytes(b)
    rows.append(dict(offset=pos,header_hex=b[:220].hex(),
     dimensions_at_100=list(struct.unpack_from('<2I',b,100)),dimensions_at_104=list(struct.unpack_from('<2I',b,104)),
     hash_at_108=b[108:124].hex(),hash_at_112=b[112:128].hex(),uint32_after_124=list(struct.unpack_from('<16I',b,124))))
    pos=raw.find(key,pos+1)
   report[name]=rows
 (OUT/'scenery.edf').unlink();p.unlink()
 report['source_zero_alpha_md5']=hashlib.md5(bytes(16*16)).hexdigest()
 (OUT/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
