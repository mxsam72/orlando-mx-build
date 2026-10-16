"""Extend the accepted C soil over the missing start straight and left strip.

Only existing bitmap channels are edited. Terrain, scenery, riding surfaces,
race files, physical materials and the accepted B/C course remain unchanged.
The v064 checkpoint is self-contained; no historical source stack is needed.
"""
from pathlib import Path
import gc, hashlib, json, os
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v062_trials import Circuit, noise
from v048_surface import smooth, normal_map
from v054_previews import Terrain

R=Path(__file__).resolve().parents[1]
BASE=R/'V064_OUTPUT'; O=R/'V065_OUTPUT'; M=O/'materials'; S=R/'V065_SOURCE'
CHANGED=('mask_v046_section.tga','mask_v046_packed.tga','mask_v046_wear.tga',
         'mask_visual_grass.tga','v044_route_detail_n.tga')
TERRAIN_SHA='860350c4c733e5d26939e9e2f40204679ecef302d6e07889f78a849afc8a8fa2'
SCENERY_SHA='40d8e6ddeacfa0d0c3c9fad454abd2f83acee633fb367e31c8530d8dbafa6e99'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def source(name,baseline=False):
 folders=([BASE/'materials',BASE/'facility_textures',BASE] if baseline else
          [M,O/'facility_textures',O,BASE/'materials',BASE/'facility_textures',BASE])
 for folder in folders:
  if (folder/name).is_file():return folder/name
 raise FileNotFoundError(name)
def write_image(a,p):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.stem+'.writing.tga');Image.fromarray(a).save(tmp);tmp.replace(p)

class Start:
 def __init__(self):
  self.route=dict(np.load(BASE/'route.npz'));self.q=self.route['q'];self.start=self.route['start']
  self.length=float(self.q[-1,3]);self.tree=cKDTree(self.start[:,:2]);self.main_tree=cKDTree(self.q[:,:2])
  self.curve=CubicSpline(self.start[:,3],self.start[:,:2]);self.terrain=Terrain(BASE/'terrain.raw')
  self.knots=np.asarray(json.loads((BASE/'layout.json').read_text())['start_width_knots'])
  self.old_section=np.asarray(Image.open(source('mask_v046_section.tga',True)).getchannel('A'),np.float32)/255
 def slope(self,x,z):return self.terrain.slope(x,z)
 def common(self,x,z):
  shape=x.shape;pos=np.c_[x.ravel(),z.ravel()];ds,idx=self.tree.query(pos,workers=2)
  ss=self.start[idx,3].copy()
  for _ in range(3):
   p=self.curve(ss);v=self.curve(ss,1);a=self.curve(ss,2);delta=pos-p
   den=(v*v).sum(1)-(delta*a).sum(1)
   ss+=np.clip(np.sum(delta*v,axis=1)/np.maximum(den,.12),-.7,.7)
   ss=np.clip(ss,-8,float(self.start[-1,3])+4)
  p=self.curve(ss);v=self.curve(ss,1);v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-8)
  delta=pos-p;l=delta[:,0]*-v[:,1]+delta[:,1]*v[:,0]
  half=np.interp(ss,self.knots[:,0],self.knots[:,1])/2
  # Full start width; the circled left strip extends seven metres outward.
  # The last two metres blend into untouched landscaping.
  left_extra=7*smooth((79-ss)/12)
  side=smooth((l+half+1.2)/1.2)*smooth((half+left_extra+1.5-l)/1.5)
  along=smooth((ss+2.8)/2.8)*smooth((82-ss)/18)
  w=(side*along).reshape(shape)
  # The screenshot's green band extends between the straight and the
  # neighbouring course, beyond the lane's immediate seven-metre shoulder.
  # Use its world-space footprint so the bending start centreline cannot
  # incorrectly assign its far end to a later station and leave a fringe.
  strip=smooth((x-379)/2)*smooth((400-x)/2)*smooth((z-168)/3)*smooth((250-z)/8)
  w=np.maximum(w,strip);grass_scope=w.copy()
  dm,_=self.main_tree.query(pos,workers=2)
  n=len(self.old_section);old=map_coordinates(self.old_section,[(600-z)/600*n-.5,x/600*n-.5],order=1,mode='nearest')
  # Keep the adjacent original B corner/approach exact even where the
  # enlarged shoulder is close to another part of the main course.
  protect=((dm+1<ds).reshape(shape))&(old>.03)
  w=np.where(protect,0,w)
  ss=ss.reshape(shape);l=l.reshape(shape);half=half.reshape(shape);v=v.reshape(*shape,2)
  core=1-smooth((abs(l)-half+.5)/1.8);hx,hz=self.slope(x,z)
  face=smooth((abs(hx*v[...,0]+hz*v[...,1])-.07)/.18)
  f=dict(s=ss+self.length+20,l=l,half=half,scope=w,grass_scope=grass_scope,corner=np.zeros(shape),face=face,core=core,shoulder=1-core)
  f.update({'n'+str(i):noise(x,z,scale,seed) for i,(scale,seed) in enumerate([(.27,13),(.56,41),(1.25,62),(3.7,19),(9.2,87)])})
  return f

def retain():
 for folder in [O,M,S]:folder.mkdir(parents=True,exist_ok=True)
 retained=[]
 for p in sorted(BASE.iterdir()):
  if not p.is_file() or p.suffix=='.json':continue
  dest=O/p.name
  if not dest.exists():os.link(p,dest)
  assert sha(dest)==sha(p)
  retained.append(dict(file=p.name,sha256=sha(p)))
 assert sha(O/'terrain.raw')==TERRAIN_SHA and sha(O/'scenery.fbx')==SCENERY_SHA
 return retained

def author(c,name):
 old=np.array(Image.open(source(name,True)));out=old.copy();n=len(old);dx=600/n
 normal=name.endswith('_n.tga');bounds=(377.,443.,165.,260.)
 x0=max(1,int(bounds[0]/dx));x1=min(n-1,int(bounds[1]/dx)+1)
 y0=max(1,int((600-bounds[3])/dx));y1=min(n-1,int((600-bounds[2])/dx)+1)
 changed=0;outside=0
 for row in range(y0,y1,80):
  end=min(row+80,y1);halo=1 if normal else 0
  x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-halo,end+halo)+.5)*dx)
  f=c.common(x,z);w=f['grass_scope'] if name=='mask_visual_grass.tga' else f['scope'];relief,rgb=Circuit.fields(c,x,z,f,'C')
  before=old[row:end,x0:x1]
  if normal:
   nn=normal_map(c,x,z,relief,dx)[1:-1]/127.5-1;w=w[1:-1]
   v=(before[:,:,:3]/127.5-1)*(1-w[...,None])+nn*w[...,None]
   v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-8)
   new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)))
   new=np.where((w>0)[...,None],new,before[:,:,:3]);out[row:end,x0:x1,:3]=new
   diff=np.any(new!=before[:,:,:3],axis=2)
  else:
   factor=np.mean(rgb/np.array([107.45,96.81,77.44]),axis=2)
   if name=='mask_v046_section.tga':target=np.full(w.shape,255.)
   elif name=='mask_v046_wear.tga':target=255*(.62+.035*f['face'])
   elif name=='mask_v046_packed.tga':target=255*np.clip(.45+(1-factor)*2.7-.15*f['shoulder'],.05,.94)
   else:target=np.zeros(w.shape)
   new=np.uint8(np.rint(before[:,:,3]*(1-w)+target*w))
   out[row:end,x0:x1,3]=new;diff=new!=before[:,:,3]
  assert not np.any(diff&(w==0));changed+=int(diff.sum())
  if (row-y0)//80%6==0:print('START_C_ROWS',name,row,'/',y1,flush=True)
 if normal:assert np.array_equal(out[:,:,3],old[:,:,3])
 else:assert np.array_equal(out[:,:,:3],old[:,:,:3])
 # Pixels outside the bounding rectangle and zero-weight support stay exact.
 assert np.array_equal(out[:y0],old[:y0]) and np.array_equal(out[y1:],old[y1:])
 assert np.array_equal(out[y0:y1,:x0],old[y0:y1,:x0]) and np.array_equal(out[y0:y1,x1:],old[y0:y1,x1:])
 write_image(out,M/name);del old,out;gc.collect()
 return dict(file=name,changed_pixels=changed,changes_outside_start_scope=outside)

def validate(c,retained,edits):
 prior=json.loads((BASE/'surface_validation.json').read_text());images=[]
 for row in prior['active_terrain_inventory']:
  p=source(row['file']);im=Image.open(p)
  assert list(im.size)==row['size'] and im.mode==row['mode']
  if row['file'] not in CHANGED:assert sha(p)==row['sha256']
  images.append(dict(row,sha256=sha(p)))
 shaders=[dict(row,sha256=sha(source(row['file']))) for row in prior['active_shaders']]
 assert all(row['sha256']==old['sha256'] for row,old in zip(shaders,prior['active_shaders']))
 # Full opening lane, including previously empty first 60 m.
 stations=np.linspace(.5,60,120);lats=np.linspace(-18.5,18.5,75);ss,ll=np.meshgrid(stations,lats)
 p=c.curve(ss);v=c.curve(ss,1);v/=np.linalg.norm(v,axis=2,keepdims=True)
 x=p[...,0]-v[...,1]*ll;z=p[...,1]+v[...,0]*ll
 for name,target in [('mask_v046_section.tga',255),('mask_visual_grass.tga',0)]:
  a=np.asarray(Image.open(source(name)).getchannel('A'));n=len(a)
  samples=map_coordinates(a,[(600-z)/600*n-.5,x/600*n-.5],order=0,mode='nearest')
  # Gate and physical edge have a deliberate sub-metre feather.
  core=(ss>=1)&(abs(ll)<=18.0)
  assert np.all(samples[core]==target),(name,int(samples[core].min()),int(samples[core].max()))
 # Circled strip: six metres beyond left edge, away from gate and end blends.
 x,z=np.meshgrid(np.linspace(381.5,396.5,31),np.linspace(172,241,100))
 a=np.asarray(Image.open(source('mask_visual_grass.tga')).getchannel('A'));n=len(a)
 strip=map_coordinates(a,[(600-z)/600*n-.5,x/600*n-.5],order=0,mode='nearest')
 assert int(strip.max())==0,strip.max()
 allocation=sum(row['rgba8_bytes'] for row in images)
 assert allocation==prior['texture_allocation_bytes']
 report=dict(checks_pass=True,version='v065 start C coverage and left grass strip',baseline='v064-hybrid-38832665174',
  changed_material_files=edits,retained_source_files=retained,active_terrain_inventory=images,active_shaders=shaders,
  texture_allocation_bytes=allocation,rgba8_base_level_bytes_before=allocation,rgba8_base_level_bytes_after=allocation,
  added_images=0,added_layers=0,layer_count=14,start_C_full_opening_coverage=True,circled_visual_grass_strip_removed=True,
  physical_grass_and_physical_declarations_unchanged=True,pit_grass_outside_start_scope_exact=True,
  original_B_corners_and_C_course_outside_start_scope_exact=True,normal_specular_alpha_exact=True,mask_RGB_exact=True,
  terrain_and_wall_roller_exact=True,scenery_vehicles_and_sign_exact=True,lighting_exact_v064=True,
  correction='v064 C generation inherited masks that were empty in the opening 60 m. v065 extends their coverage explicitly.',
  native_compilation_started=False,in_game_verified=False)
 save(S/'surface_validation.json',report);save(O/'surface_validation.json',report)
 print('V065_START_C_PASS; full opening lane, left grass removed, allocation unchanged',allocation,flush=True)
 return report

def main():
 retained=retain();c=Start();edits=[author(c,name) for name in CHANGED];validate(c,retained,edits)
if __name__=='__main__':main()
