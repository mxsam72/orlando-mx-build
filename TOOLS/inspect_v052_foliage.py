"""Inspect the published tree colour/alpha and shader inputs without rebuilding."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

R=Path(__file__).resolve().parents[1]
OUT=R/'BUILD/v052_foliage_inspection'
URL='https://github.com/mxsam72/orlando-mx-build/releases/download/v047-realistic-trees-38458081921/OrlandoMX-v047-tree-source-checkpoint.zip'
SIZE=292379577
DIGEST='0a1f44d74eef2908a17e120fac9eed7ad9ec416fa693c51d0c6a08c83749cdf1'

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 p=OUT/'source.zip'
 with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'OrlandoMX-tree-inspection'}),timeout=180) as src,p.open('wb') as dst:
  while block:=src.read(4*1024*1024):dst.write(block)
 assert p.stat().st_size==SIZE and hashlib.sha256(p.read_bytes()).hexdigest()==DIGEST
 report={}
 with zipfile.ZipFile(p) as z:
  names=[n for n in z.namelist() if n.startswith('V047_OUTPUT/facility_textures/') and ('pine' in n or 'woodland' in n)]
  print('Foliage files',names,flush=True)
  for name in names:
   raw=z.read(name);target=OUT/Path(name).name;target.write_bytes(raw)
   if name.endswith('.shd'):
    report[Path(name).name]=dict(shader=raw.decode());continue
   if not name.endswith('.tga'):continue
   im=Image.open(target).convert('RGBA');a=np.asarray(im);opaque=a[:,:,3]>=128
   white=opaque&(a[:,:,:3].min(2)>180)
   neutral=opaque&(a[:,:,:3].max(2)-a[:,:,:3].min(2)<35)&(a[:,:,:3].mean(2)>170)
   report[Path(name).name]=dict(size=im.size,mode=Image.open(target).mode,alpha_min=int(a[:,:,3].min()),alpha_max=int(a[:,:,3].max()),
    opaque_pixels=int(opaque.sum()),white_pixels=int(white.sum()),pale_neutral_pixels=int(neutral.sum()),
    opaque_rgb_mean=a[:,:,:3][opaque].mean(0).tolist(),sha256=hashlib.sha256(raw).hexdigest())
   if '_n.tga' in name:continue
   bg=Image.new('RGBA',im.size,(34,44,56,255));bg.alpha_composite(im)
   show=bg.convert('RGB').resize((1024,1024))
   draw=ImageDraw.Draw(show);draw.rectangle((0,0,1024,42),fill=(20,24,29));draw.text((12,14),Path(name).name+' — source texture on dark background',fill='white')
   show.save(OUT/(target.stem+'_colour.jpg'),quality=95)
   Image.fromarray(a[:,:,3]).save(OUT/(target.stem+'_alpha.png'))
 p.unlink()
 (OUT/'report.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
