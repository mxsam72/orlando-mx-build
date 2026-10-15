"""Add the requested perpendicular pass and full-width face grooves in-place.

Reuses v058's colour scan, normal image slot and material layers. Grooming is
normal relief only; the two bank transitions and R11 move are real terrain.
"""
import json,os
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter1d,map_coordinates
from v059_geometry import R,PREV,O,M,S,sha,save,cross_points,corner_regions,smooth
from v058_surface import Circuit as BaseCircuit,source as previous,inventory
from v054_previews import Terrain
from v048_surface import normal_map

def source(name):return M/name if (M/name).is_file() else previous(name)

class Circuit(BaseCircuit):
 def __init__(self):
  super().__init__();self.terrain=Terrain(O/'terrain.raw');self.height=self.terrain.h;self.gx=self.terrain.gx;self.gz=self.terrain.gz
  self.profiles=json.loads((O/'jump_profiles.json').read_text());self.features=[(p['id'],p['station_start_m'],p['station_end_m']) for p in self.profiles if p['kind']!='none']
  self.corners=list(corner_regions(self.q,self.route['v054_old_station']))
  byid={p['id']:p for p in self.profiles};r14=byid['R14']
  self.cross_regions=self.corners+[('R04',self.corners[2][2],self.corners[3][1]),('R14_FACE',r14['station_start_m'],r14['lip_s']+1.2)]
  self.full_faces=[(n,byid[n]['station_start_m'],byid[n]['lip_s']+1.2) for n in ['R03','R07']]
  rng=np.random.default_rng(590151);self.cross_centres=[];self.cross_width=[];self.cross_depth=[];self.spacing=[]
  for name,lo,hi in self.cross_regions:
   ss=np.arange(lo-1,hi+1.01,.05);lat=np.linspace(-9,9,37);sg,lg=np.meshgrid(ss,lat);pp=cross_points(self.q,sg,lg);hh=self.terrain.ground(pp[:,:,0],pp[:,:,1]);xyz=np.dstack([pp,hh])
   metric=np.linalg.norm(np.gradient(xyz,.05,axis=1),axis=2).max(0);metric=maximum_filter1d(metric,31,mode='nearest')
   centers=[];position=lo-.5
   while position<hi+.5:
    factor=float(np.interp(position,ss,metric));centers.append(position);self.cross_width.append(rng.uniform(.045,.067)/max(factor,1));self.cross_depth.append(rng.uniform(.028,.042))
    position+=rng.uniform(.30,.46)/max(factor,1)
   self.cross_centres.extend(centers)
   # Direct 3D checks at every line, across the full authored 18m corridor.
   sg,lg=np.meshgrid(np.array(centers),lat);p=cross_points(self.q,sg,lg);hh=self.terrain.ground(p[:,:,0],p[:,:,1]);xyz=np.dstack([p,hh]);gaps=np.linalg.norm(np.diff(xyz,axis=1),axis=2)
   assert gaps.max()<=.5,(name,float(gaps.max()))
   self.spacing.append(dict(section=name,station_m=[lo,hi],line_count=len(centers),maximum_3d_spacing_m=float(gaps.max()),minimum_3d_spacing_m=float(gaps.min()),lateral_validation_m=[-9,9]))
  order=np.argsort(self.cross_centres);self.cross_centres=np.asarray(self.cross_centres)[order];self.cross_width=np.asarray(self.cross_width)[order];self.cross_depth=np.asarray(self.cross_depth)[order]
  self.tines=np.r_[-8.7,-8.7+np.cumsum(rng.uniform(.27,.43,60))];self.tines=self.tines[self.tines<8.8]
 def weights(self,x,z):
  ss,ll=self.coords(x,z);cross=np.zeros_like(ss);long=np.zeros_like(ss)
  for name,a,b in self.cross_regions:cross=np.maximum(cross,smooth((ss-a)/1.3)*smooth((b-ss)/1.3))
  for name,a,b in self.full_faces:long=np.maximum(long,smooth((ss-a)/.8)*smooth((b-ss)/.8))
  tx=np.interp(ss,self.q[:,3],self.v[:,0]);tz=np.interp(ss,self.q[:,3],self.v[:,1]);hx,hz=self.slope(x,z);face=smooth((hx*tx+hz*tz-.04)/.10)
  r14=next(r for r in self.cross_regions if r[0]=='R14_FACE');on14=(ss>=r14[1])&(ss<=r14[2]);cross=np.where(on14,cross*face,cross)
  side=1-smooth((abs(ll)-7.2)/2.5);scope=self.scope(x,z)
  return ss,ll,cross*side*scope,long*face*side*scope
 def additions(self,x,z):
  ss,ll,cross,long=self.weights(x,z);d=np.zeros_like(ss);idx=np.searchsorted(self.cross_centres,ss)
  for offset in [-1,0]:
   ii=np.clip(idx+offset,0,len(self.cross_centres)-1);u=(ss-self.cross_centres[ii])/self.cross_width[ii]
   d+=(-np.exp(-u*u)+.30*np.exp(-((u-1.8)/1.05)**2))*self.cross_depth[ii]*cross
  # Increase the lengthwise pass across the whole R03/R07 takeoff, including
  # both edges of the racing width. Retain the accepted underlying marks.
  for i,tine in enumerate(self.tines):
   w=.055+.018*np.sin(i*1.31)**2;u=(ll-tine)/w;activity=.82+.18*np.sin(ss*.16+i*1.7)**2
   d+=(-np.exp(-u*u)+.30*np.exp(-((u-1.7)/1.1)**2))*.045*activity*long
  return d,np.maximum(cross,long)

def author(c):
 a=np.array(Image.open(previous('v044_route_detail_n.tga')));n=len(a);dx=600/n;changed=0
 p=c.p;pmin=p.min(0)-18;pmax=p.max(0)+18;x0=max(1,int(pmin[0]/dx)-2);x1=min(n-1,int(pmax[0]/dx)+3);y0=max(1,int((600-pmax[1])/dx)-2);y1=min(n-1,int((600-pmin[1])/dx)+3)
 for row in range(y0,y1,64):
  end=min(row+64,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-1,end+1)+.5)*dx)
  relief,weight=c.additions(x,z);delta=normal_map(c,x,z,relief,dx)[1:-1]/127.5-1
  old=a[row:end,x0:x1,:3].copy();base=old/127.5-1
  slopes=-base[:,:,:2]/np.maximum(base[:,:,2,None],.20)-delta[:,:,:2]/np.maximum(delta[:,:,2,None],.20)
  nn=np.dstack([-slopes,np.ones(slopes.shape[:2])]);nn/=np.linalg.norm(nn,axis=2,keepdims=True)
  new=np.uint8(np.rint(np.clip(nn*127.5+127.5,0,255)));active=(weight[1:-1]>0)&(c.scope(x,z)[1:-1]>0)
  new=np.where(active[:,:,None],new,old);a[row:end,x0:x1,:3]=new;changed+=int(np.count_nonzero(np.any(new!=old,axis=2)))
  if (row-y0)//64%12==0:print('V059 grooming rows',row,'/',y1,flush=True)
 assert np.all(a[:,:,3]==2);temp=M/'macro_writing.tga';Image.fromarray(a).save(temp);temp.replace(M/'v044_route_detail_n.tga')
 a=np.array(Image.open(previous('mask_v046_wear.tga')));old=a[:,:,3].copy();n=len(a)
 for row in range(0,n,128):
  end=min(n,row+128);x,z=np.meshgrid((np.arange(n)+.5)*600/n,600-(np.arange(row,end)+.5)*600/n)
  ss,ll,cross,long=c.weights(x,z);weight=np.maximum(cross,long)
  target=np.maximum(old[row:end].astype(float),255*np.where(long>cross,.90,.82));alpha=np.uint8(np.rint(old[row:end]*(1-weight)+target*weight))
  alpha[old[row:end]==0]=0;a[row:end,:,3]=alpha
 assert np.array_equal(a[:,:,3]>0,old>0);Image.fromarray(a).save(M/'mask_v046_wear.tga')
 return changed

def validate(c,changed):
 before,_=inventory(previous);after,shaders=inventory(source);old={r['file']:r for r in before}
 assert {r['file'] for r in before}=={r['file'] for r in after}
 assert sum(r['rgba8_bytes'] for r in before)==sum(r['rgba8_bytes'] for r in after)
 allowed={'v044_route_detail_n.tga','mask_v046_wear.tga'}
 for r in after:
  if r['file'] not in allowed:assert r['sha256']==old[r['file']]['sha256'],r['file']
 a=np.asarray(Image.open(previous('mask_v046_wear.tga')));b=np.asarray(Image.open(source('mask_v046_wear.tga')))
 assert np.array_equal(a[:,:,:3],b[:,:,:3]) and np.array_equal(a[:,:,3]>0,b[:,:,3]>0)
 assert sha(source('v045_loose.tga'))=='1b04368a8847916d209ad71fb23886939c8c0bf631a0a9a5d44b4daa8b554cf7'
 assert sha(O/'compiled_track.hmf')==sha(PREV/'compiled_track.hmf')
 report=dict(checks_pass=True,version='v059',approved_C_photo_and_fine_normals_exact=True,base_method='C+B',
  perpendicular_standard=dict(angle_degrees=90,irregular_spacing=True,maximum_spacing_m=.5,scope='all 14 corners, R04 straight, R14 takeoff',applies_to_future_requests=True),
  spacing_checks=c.spacing,full_width_face_grooves=['R03','R07'],normal_atlas_size=[8192,8192],changed_macro_pixels=changed,
  active_terrain_inventory=after,active_shaders=shaders,rgba8_base_level_bytes_before=sum(r['rgba8_bytes'] for r in before),rgba8_base_level_bytes_after=sum(r['rgba8_bytes'] for r in after),
  added_layers=0,added_images=0,all_mask_footprints_exact=True,physical_material_declarations_exact=True,
  final_compilation_started=False,in_game_verified=False,memory_note='Source image allocation unchanged from v058; game RAM/VRAM and FPS unmeasured.')
 save(O/'surface_validation.json',report);save(S/'surface_validation.json',report)
 print('V059_SURFACE_PASS',changed,'macro pixels; all 16 spacing regions <=0.5m; image allocation unchanged',flush=True)

def main():
 M.mkdir(exist_ok=True,parents=True);c=Circuit();changed=author(c);validate(c,changed)

if __name__=='__main__':main()
