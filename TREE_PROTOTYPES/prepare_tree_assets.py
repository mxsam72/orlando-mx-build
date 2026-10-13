"""Prepare pinned foliage sources and authenticated CC0 photographic materials."""
from pathlib import Path
import json,hashlib,urllib.request,shutil,tarfile
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parent;T=R/'textures';T.mkdir(exist_ok=True)
def fetch(url,timeout=120):
    req=urllib.request.Request(url,headers={'User-Agent':'OrlandoMX-v044-CC0-authoring'})
    return urllib.request.urlopen(req,timeout=timeout)
pin={'CK_pine_foliage':'dc15878c44431f4670ff82aa59dd520c8c1f27b0e8975b3967fa866467cd3f19','CK_woodland_foliage':'881fa65a86e48fa8f620258e1ba9d857f22d9fda34209ed8c394d0833b75eaac'}
provenance=[]
for name,digest in pin.items():
    p=T/(name+'.webp');assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    im=Image.open(p).convert('RGBA').resize((2048,2048),Image.Resampling.LANCZOS);assert im.getchannel('A').getextrema()==(0,255)
    im.save(T/(name+'.tga'));provenance.append(dict(name=name,source='Generated foliage atlas',sha256=digest,alpha=True,pixels=2048))
    (T/(name+'.shd')).write_text('specular\n{\n shininess = 8\n}\n')
for asset,kind,name in [('pine_bark','Diffuse','pine_bark.tga'),('pine_bark','nor_gl','pine_bark_n.tga'),('farm_soil','Diffuse','review_soil.tga')]:
    with fetch('https://api.polyhaven.com/files/'+asset) as r:metadata=json.load(r)
    entry=metadata[kind]['2k']['jpg'];p=T/(asset+'_'+kind+'.jpg')
    with fetch(entry['url'],180) as r,p.open('wb') as f:shutil.copyfileobj(r,f,4194304)
    assert hashlib.md5(p.read_bytes()).hexdigest()==entry['md5']
    im=Image.open(p).convert('RGBA' if kind=='nor_gl' else 'RGB')
    if kind=='nor_gl':im.putalpha(Image.new('L',im.size,2))
    if name=='review_soil.tga':
        a=np.asarray(im,np.float32);a=(a-a.mean((0,1)))*1.08+np.array([114,96,78]);im=Image.fromarray(np.uint8(np.rint(np.clip(a,8,235))))
    im.save(T/name);provenance.append(dict(name=name,asset=asset,provider='Poly Haven',license='CC0',url=entry['url'],md5=entry['md5']))
(T/'pine_bark.shd').write_text('bump\n{\n map = pine_bark_n.tga\n}\nspecular\n{\n shininess = 8\n}\n')
(R/'texture_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
base='https://download.blender.org/release/Blender4.5/';name='blender-4.5.3-linux-x64.tar.xz'
with fetch(base+'blender-4.5.3.sha256') as r:manifest=r.read().decode()
digest=next(x.split()[0] for x in manifest.splitlines() if name in x)
archive=R/name
with fetch(base+name,300) as r,archive.open('wb') as f:shutil.copyfileobj(r,f,4194304)
h=hashlib.sha256()
with archive.open('rb') as f:
    while b:=f.read(4194304):h.update(b)
assert h.hexdigest()==digest
with tarfile.open(archive) as z:z.extractall(R,filter='data')
archive.unlink();print('Pinned foliage, authenticated CC0 photographs and official Blender restored.',flush=True)
