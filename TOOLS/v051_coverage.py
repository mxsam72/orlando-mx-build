"""Shared safe MX verge coverage and separately scoped legacy-layer trials."""
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,map_coordinates,gaussian_filter
from scipy.spatial import cKDTree
from v048_surface import R,BASE,DIRT,SIZE,sha,save,tga,smooth,window

TRIALS=[
 dict(id='A',feature='R03 table-single',layer=2,mask='mask_visual_racing.tga',lo=232.,hi=279.,change='Remove only the historic prepared-soil overlay'),
 dict(id='B',feature='R10 big tabletop',layer=8,mask='mask_v032_packed.tga',lo=743.2,hi=813.2,change='Remove only the historic packed-soil overlay'),
 dict(id='C',feature='R17 eight rollers',layer=9,mask='mask_v032_face.tga',lo=1305.4,hi=1385.4,change='Remove only the historic jump-face overlay'),
]

def baseline_mask(name):
 for p in [BASE/'masks'/name.removeprefix('mask_'),BASE/'materials'/name]:
  if p.exists():return p
 raise FileNotFoundError(name)

class Verge:
 def __init__(self):
  self.q=dict(np.load(BASE/'route.npz'))
  self.tree=cKDTree(self.q['q'][:,:2]);self.n=2048
  # Protect the entire existing riding mask, including its jump banks, plus
  # a natural bare transition. Road and paddock masks retain their appearance.
  dirt=np.asarray(Image.open(DIRT/'materials/mask_v046_section.tga').getchannel('A').resize((self.n,self.n),Image.Resampling.BILINEAR))
  self.clearance=distance_transform_edt(dirt<245)*SIZE/self.n
  roads=np.asarray(Image.open(BASE/'masks/v024_pit_roads.tga').getchannel('A'))
  pits=np.asarray(Image.open(BASE/'masks/pits.tga').getchannel('A'))
  self.roads=distance_transform_edt(roads<=8)*SIZE/self.n
  self.pits=pits
  x=(np.arange(self.n)+.5)*SIZE/self.n;z=SIZE-x
  self.mask=np.zeros((self.n,self.n),np.float32)
  rng=np.random.default_rng(510051);noise=gaussian_filter(rng.random((self.n,self.n),dtype=np.float32),18)
  noise=(noise-noise.mean())/max(noise.std(),1e-7)
  for y in range(0,self.n,64):
   xx,zz=np.meshgrid(x,z[y:y+64]);d,ix=self.tree.query(np.stack([xx.ravel(),zz.ravel()],1),workers=2)
   d=d.reshape(xx.shape);width=self.q['width'][ix].reshape(xx.shape)
   near=smooth((29-d)/7)
   safe=smooth((self.clearance[y:y+64]-1.05)/.95)*smooth((self.roads[y:y+64]-.85)/.7)
   safe*=self.pits[y:y+64]<8
   safe*=d>width/2+1.0
   self.mask[y:y+64]=np.clip(.83+.08*noise[y:y+64],.65,.97)*near*safe
 def sample(self,p):
  p=np.asarray(p)
  return map_coordinates(self.mask,[(SIZE-p[:,1])/SIZE*self.n-.5,p[:,0]/SIZE*self.n-.5],order=1,mode='constant',cval=0.)

def author(sample,out):
 out.mkdir(parents=True,exist_ok=True);verge=Verge();old=np.array(Image.open(baseline_mask('mask_visual_grass.tga')))
 new=old.copy();new[:,:,3]=np.maximum(old[:,:,3],np.uint8(np.rint(verge.mask*255)))
 assert np.array_equal(new[:,:,:3],old[:,:,:3]);changed=new[:,:,3]!=old[:,:,3]
 assert np.all(verge.clearance[changed]>1.05) and np.all(verge.roads[changed]>.85) and np.all(verge.pits[changed]<8)
 tga(new,out/'mask_visual_grass.tga')
 reports=[]
 for trial in TRIALS:
  p=baseline_mask(trial['mask']);a=np.array(Image.open(p));n=a.shape[0];x=(np.arange(n)+.5)*SIZE/n;z=SIZE-x
  edited=a.copy();total=0;outside=0
  for y in range(0,n,64):
   xx,zz=np.meshgrid(x,z[y:y+64]);s,l=sample.coords(xx,zz)
   scope=sample.scope(xx,zz)*window(s,trial['lo'],trial['hi'],3.)
   alpha=np.uint8(np.rint(a[y:y+64,:,3]*(1-scope)))
   change=alpha!=a[y:y+64,:,3];total+=int(change.sum());outside+=int(np.count_nonzero(change&(scope<=0)))
   edited[y:y+64,:,3]=alpha
  assert total>0 and outside==0,(trial['id'],'empty or out-of-scope trial')
  assert np.array_equal(a[:,:,:3],edited[:,:,:3]);tga(edited,out/trial['mask'])
  reports.append(dict(trial,checks_pass=True,changed_pixels=total,changed_pixels_outside_section=outside,
   original_sha256=sha(p),authored_sha256=sha(out/trial['mask']),global_layer_retained=True))
 save(out.parent/'v051_layer_trials.json',dict(checks_pass=True,one_change_per_section=True,nonoverlapping_station_intervals=True,
  trials=reports,global_layer_count=14,global_texture_allocations_removed=0,
  note='Each old overlay is removed only in its named section. Textures remain required elsewhere; archive savings are measured after native compilation.'))
 save(out.parent/'v051_verge_validation.json',dict(checks_pass=True,existing_grass_layer=5,added_layers=0,changed_ground_pixels=int(changed.sum()),
  new_grass_ground_area_m2=float(changed.sum()*(SIZE/verge.n)**2),riding_corridor_clearance_m=1.05,road_clearance_m=.85,
  paddock_excluded=True,photographic_ground_tile_unchanged=True,mask_sha256=sha(out/'mask_visual_grass.tga')))
 return verge
