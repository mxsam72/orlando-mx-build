"""Reproducible visual-only material pass; never writes height or physics data."""
from pathlib import Path
import json,zipfile,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,gaussian_filter1d
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[1]
N=2048
rng=np.random.default_rng(8008)
def mask(n):return np.asarray(Image.open(R/f'03_MASKS/{n}.tga').getchannel('A'),dtype=np.float32)/255
def save(n,a):
 im=Image.fromarray(np.uint8(np.clip(a,0,1)*255));im.save(R/f'03_MASKS/{n}.png')
 out=Image.new('RGBA',im.size,'white');out.putalpha(im);out.save(R/f'03_MASKS/{n}.tga')
def smooth(a):
 a=np.clip(a,0,1);return a*a*(3-2*a)
def noise(sig):
 a=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),sig);return a/a.std()
def main():
 texturezip=R.parent/'recovered/current/OrlandoMX_v008_TexturePack.zip'
 with zipfile.ZipFile(texturezip) as z:
  for n in ['soil','soil_wet','prepared','prepared_wet','worked','worked_wet','grass']:
   (R/f'04_TEXTURES/{n}.tga').write_bytes(z.read(f'v008_texture_pack/{n}_v008.tga'))
 d=np.load(R/'01_GIS_AERIAL/route.npz');q=d['q'];width=d['width'];L=q[-1,3]
 tree=cKDTree(q[:-1,:2]);sf=np.zeros((N,N),np.float32);lat=sf.copy();wf=sf.copy()
 axis=np.linspace(0,600,N)
 for row in range(0,N,64):
  z,x=np.meshgrid(600-axis[row:row+64],axis,indexing='ij');p=np.c_[x.ravel(),z.ravel()];_,ind=tree.query(p,workers=2);delta=p-q[ind,:2];th=q[ind,2]
  sf[row:row+len(x)]=((q[ind,3]+delta[:,0]*np.cos(th)+delta[:,1]*np.sin(th))%L).reshape(x.shape)
  lat[row:row+len(x)]=(-delta[:,0]*np.sin(th)+delta[:,1]*np.cos(th)).reshape(x.shape);wf[row:row+len(x)]=width[ind].reshape(x.shape)
 macro=noise(25);fine=noise(2)
 race=mask('visual_racing');worked=mask('visual_worked')
 activity=np.zeros_like(sf)
 for j in json.loads((R/'02_HEIGHTMAP/jump_profiles.json').read_text()):
  lip=j['lip_s'];top=j.get('top_m',0);landing=j.get('landing_m',8);face=j.get('face_m',6)
  for center,spread,weight in [(lip-face*.65,face*.9,.55),(lip+top+landing*.55,landing*.85,.65)]:
   ds=(sf-center+L*.5)%L-L*.5;activity=np.maximum(activity,weight*np.exp(-(ds/spread)**2))
 samples=np.linspace(0,L,4096);theta=np.interp(samples,q[:,3],np.unwrap(q[:,2]));bend=np.clip(abs(gaussian_filter1d(np.gradient(theta,samples),6))/.065,0,1)
 for offset in [-10,0,12]:activity=np.maximum(activity,.55*np.interp((sf+offset)%L,samples,bend))
 lanes=np.zeros_like(sf)
 for i,pos in enumerate([-2.8,-1.25,.35,2.1]):
  w=gaussian_filter1d(rng.normal(size=4096),25,mode='wrap');w/=w.std();wander=np.interp(sf,samples,w)*.23
  line=np.exp(-((lat-pos*wf/12-wander)/(.24+.25*activity))**2)
  lanes=np.maximum(lanes,line)
 worked=np.clip(worked*.65+race*activity*(.26+.55*lanes)*np.clip(1+.18*macro+.08*fine,.5,1.4),0,.9)
 race=np.clip(race*(1-.055*smooth(macro+.4))+.08*gaussian_filter(race,4),0,1)
 grass=mask('visual_grass');grass*=np.clip(1+.09*fine,.7,1.1)
 save('visual_racing',race);save('visual_worked',worked);save('visual_grass',grass)
 sand=mask('sand');save('visual_sand',np.clip(sand*(.8+.15*smooth(macro)) + race*.12*smooth(macro-.15),0,1))
 p=R/'BUILD/track.hmf';p.write_text(p.read_text().replace('mask_sand.tga','mask_visual_sand.tga'))
 # Subtle texture-correlated shading normals, no height/collision displacement.
 for name,strength,spec in [('soil',3,5),('prepared',3,5),('worked',4,7),('grass',2,0)]:
  a=np.asarray(Image.open(R/f'04_TEXTURES/{name}.tga').resize((1024,1024)).convert('RGB'),dtype=np.float32).mean(2)/255
  a=gaussian_filter(a,.7,mode='wrap')-gaussian_filter(a,9,mode='wrap')
  gx=(np.roll(a,-1,1)-np.roll(a,1,1))*.5;gy=(np.roll(a,-1,0)-np.roll(a,1,0))*.5
  v=np.dstack([-gx*strength,gy*strength,np.ones_like(a)]);v/=np.linalg.norm(v,axis=2)[:,:,None]
  out=np.dstack([np.uint8((v*.5+.5)*255),np.full(a.shape,spec,np.uint8)])
  Image.fromarray(out).save(R/f'05_NORMALS/{name}_n.tga')
 print('Visual-only masks and texture-correlated normals complete',flush=True)
if __name__=='__main__':main()
