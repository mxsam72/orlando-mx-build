"""Apply approved C loam + B jump grooves to the full accepted footprint."""
import gc,json,re,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates
from scipy.spatial import cKDTree
from v058_inputs import R,BASE,PREV,O,M,sha,save
from v058_trials import Section,smooth,source as baseline
from v048_surface import normal_map
from v057_surface import shader as old_shader
from v049_previews import layers

PHOTO_SHA='1b04368a8847916d209ad71fb23886939c8c0bf631a0a9a5d44b4daa8b554cf7'
CHANGED={'v045_loose.tga','v044_route_detail.tga','v044_route_detail_n.tga','mask_v046_wear.tga','mask_v046_packed.tga'}

def source(name):return M/name if (M/name).is_file() else baseline(name)

class Circuit(Section):
 def __init__(self):
  super().__init__();self.profiles=json.loads((PREV/'jump_profiles.json').read_text())
  self.features=[(p['id'],p['station_start_m'],p['station_end_m']) for p in self.profiles if p['kind']!='none']
  # Keep the precise feature windows used in the approved comparison.
  self.features=[(name,0.,51.5) if name=='R01' else (name,128.,177.) if name=='R02' else (name,a,b) for name,a,b in self.features]
  self.start=self.route['start'];self.start_tree=cKDTree(self.start[:,:2]);self.start_v=np.c_[np.cos(self.start[:,2]),np.sin(self.start[:,2])]
 def face_weight(self,x,z):
  s,l=self.coords(x,z);tx=np.interp(s,self.q[:,3],self.v[:,0]);tz=np.interp(s,self.q[:,3],self.v[:,1]);hx,hz=self.slope(x,z)
  feature=np.zeros_like(s)
  for _,a,b in self.features:feature=np.maximum(feature,smooth((s-a)/1.5)*smooth((b-s)/1.5))
  return smooth((np.abs(hx*tx+hz*tz)-.06)/.13)*feature
 def relief(self,x,z):
  s,l=self.coords(x,z);a=np.interp(s,self.arc_station,self.arc_distance)
  pos=np.stack([x.ravel(),z.ravel()],1);dmain,_=self.tree.query(pos,workers=2);ds,ii=self.start_tree.query(pos,workers=2)
  on_start=(ds+1.0<dmain)&(ds<12.)
  if np.any(on_start):
   delta=pos-self.start[ii,:2];direction=self.start_v[ii]
   along=self.start[ii,3]+np.sum(delta*direction,axis=1)
   lateral=delta[:,0]*-direction[:,1]+delta[:,1]*direction[:,0]
   a=np.where(on_start.reshape(x.shape),along.reshape(x.shape)+83.,a)
   l=np.where(on_start.reshape(x.shape),lateral.reshape(x.shape),l)
  hx,hz=self.slope(x,z);flat=1-smooth((np.hypot(hx,hz)-.07)/.24)
  n0=self.noise(a,l,.20,0);n1=self.noise(a*.7,l,.38,1);n2=self.noise(a,l,.85,2)
  clod=np.maximum(0,.65*n0+.35*n1-.42)**1.7
  relief=(clod-.07)*(.025+.016*flat)+(n2-.5)*.004
  for i,c in enumerate(np.arange(-11.,11.,.46)):
   center=c+.022*np.sin(a*.12+i*2.1)+.012*np.sin(a*.39+i)
   w=.105+.025*np.sin(i*1.71)**2
   activity=.23+.77*smooth((self.noise(a+i*11,l,2.7,3)-.28)/.47)
   groove=np.exp(-((l-center)/w)**2);shoulder=np.exp(-((l-center-w*1.6)/(w*1.1))**2)
   relief+=(-groove+shoulder*.35)*(.033+.012*flat)*activity
  return relief

def colour():
 im=np.asarray(Image.open(baseline('v045_loose.tga')).convert('RGB'),np.float32)
 n=np.asarray(Image.open(baseline('v045_loose_n.tga')),np.float32)[:,:,:3]/127.5-1
 gx=-n[:,:,0]/np.maximum(n[:,:,2],.25);gy=n[:,:,1]/np.maximum(n[:,:,2],.25)
 gx=gaussian_filter(gx,3.,mode='wrap');gy=gaussian_filter(gy,3.,mode='wrap')
 curvature=(np.roll(gx,-1,1)-np.roll(gx,1,1)+np.roll(gy,-1,0)-np.roll(gy,1,0))*.5
 cavity=np.clip(gaussian_filter(curvature,2.,mode='wrap')/.12,0,1);out=im*(1-cavity*.18)[:,:,None]
 out+=im.mean((0,1))-out.mean((0,1));out=np.uint8(np.rint(np.clip(out,8,235)))
 Image.fromarray(out).save(M/'v045_loose.tga');assert sha(M/'v045_loose.tga')==PHOTO_SHA,'Approved C photograph changed'
 shutil.copy2(M/'v045_loose.tga',M/'v044_route_detail.tga')
 print('V058_APPROVED_C_COLOUR_EXACT',PHOTO_SHA,flush=True)

def atlas(c):
 a=np.array(Image.open(baseline('v044_route_detail_n.tga')));n=a.shape[0];dx=600/n;changed=0
 p=np.r_[c.p,c.start[:,:2]];pmin=p.min(0)-19;pmax=p.max(0)+19
 x0=max(1,int(pmin[0]/dx)-3);x1=min(n-1,int(pmax[0]/dx)+3)
 y0=max(1,int((600-pmax[1])/dx)-3);y1=min(n-1,int((600-pmin[1])/dx)+3)
 for row in range(y0,y1,64):
  end=min(row+64,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-1,end+1)+.5)*dx)
  scope=c.scope(x,z)[1:-1];f=c.face_weight(x,z)[1:-1]
  target=normal_map(c,x,z,c.relief(x,z),dx)[1:-1];old=a[row:end,x0:x1,:3].copy()
  cn=(old/127.5-1)*(1-scope[:,:,None])+(target/127.5-1)*scope[:,:,None]
  cn/=np.maximum(np.linalg.norm(cn,axis=2,keepdims=True),1e-8)
  # Quantise the C control first, exactly as in the approved study. Preserve
  # the B/C interpolation magnitude; native shading renormalises after blend.
  cn=np.uint8(np.rint(np.clip(cn*127.5+127.5,0,255))).astype(np.float32)
  new=np.uint8(np.rint(np.clip(cn*(1-f[:,:,None])+old*f[:,:,None],0,255)))
  active=scope>0;new=np.where(active[:,:,None],new,old);a[row:end,x0:x1,:3]=new
  changed+=int(np.count_nonzero(np.any(new!=old,axis=2)))
  if (row-y0)//64%10==0:print('Full-route macro rows',row,'/',y1,flush=True)
 assert np.all(a[:,:,3]==2);Image.fromarray(a).save(M/'v044_route_detail_n.tga')
 return changed

def masks(c):
 cap=.55/(232/255)
 for name in ['mask_v046_wear.tga','mask_v046_packed.tga']:
  a=np.array(Image.open(baseline(name)));n=a.shape[0];original=a[:,:,3].copy()
  for row in range(0,n,128):
   end=min(row+128,n);x,z=np.meshgrid((np.arange(n)+.5)*600/n,600-(np.arange(row,end)+.5)*600/n)
   scope=c.scope(x,z);factor=cap+(1-cap)*c.face_weight(x,z) if name=='mask_v046_wear.tga' else .70
   # Apply the full method on the accepted photograph footprint, with the
   # same edge feather used by the source study.
   factor=1-scope+scope*factor
   target=np.uint8(np.rint(original[row:end].astype(np.float32)*factor))
   target[(original[row:end]>0)&(target==0)]=1;a[row:end,:,3]=target
  assert np.array_equal(a[:,:,3]>0,original>0);Image.fromarray(a).save(M/name)

def controls():
 text=(PREV/'compiled_track.hmf').read_text()
 for index,block in list(layers(text)):
  if index in [3,11,13]:text=text.replace(block,re.sub(r'repetitions\s*=\s*[\d.]+','repetitions = 200',block,count=1))
 (O/'compiled_track.hmf').write_text(text)
 for name,normal,reps,shine in [('v045_loose','v045_loose_n.tga',200,7),('v045_packed','v045_packed_n.tga',300,7),('v044_route_detail','v044_route_detail_n.tga',1,8)]:
  (M/(name+'.shd')).write_text('bump\n{\n map = '+normal+'\n repetitions = '+str(reps)+'\n}\nspecular\n{\n shininess = '+str(shine)+'\n}\n')

def inventory(resolver):
 text=(O/'compiled_track.hmf').read_text()+(R/'BUILD/v054_track.tht').read_text()
 names=set(re.findall(r'(?m)^\s*(?:map|mask)\s*=\s*(\S+)',text));shaders=[]
 for name in list(names):
  shader=resolver(name).with_suffix('.shd')
  if not shader.is_file():
   try:shader=old_shader(name)
   except StopIteration:continue
  if shader.is_file():
   shaders.append(dict(file=shader.name,sha256=sha(shader)));names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()))
 rows=[]
 for name in sorted(names):
  path=resolver(name);im=Image.open(path)
  rows.append(dict(file=name,size=list(im.size),mode=im.mode,rgba8_bytes=im.width*im.height*4,sha256=sha(path)))
 return rows,shaders

def validate(c,changed):
 before,_=inventory(baseline);after,shaders=inventory(source)
 assert {r['file'] for r in before}=={r['file'] for r in after}
 old={r['file']:r for r in before};saved=sum(r['rgba8_bytes'] for r in before)-sum(r['rgba8_bytes'] for r in after)
 assert saved==201326592
 for row in after:
  if row['file'] not in CHANGED:assert row['sha256']==old[row['file']]['sha256'],row['file']
  if row['file'].startswith('mask_'):
   a=np.asarray(Image.open(baseline(row['file'])));b=np.asarray(Image.open(source(row['file'])))
   if row['file'] in CHANGED:assert np.array_equal(a[:,:,:3],b[:,:,:3]) and np.array_equal(a[:,:,3]>0,b[:,:,3]>0)
   else:assert np.array_equal(a,b)
 oldim=Image.open(baseline('v044_route_detail_n.tga'));newim=Image.open(M/'v044_route_detail_n.tga');n=oldim.width;count=0
 for row in range(0,n,128):
  a=np.asarray(oldim.crop((0,row,n,min(n,row+128))));b=np.asarray(newim.crop((0,row,n,min(n,row+128))))
  yy,xx=np.where(np.any(a!=b,axis=2));count+=len(xx)
  if len(xx):assert np.all(c.scope((xx+.5)*600/n,600-(yy+row+.5)*600/n)>0)
  assert np.array_equal(a[:,:,3],b[:,:,3])
 assert count>0 and (changed is None or count==changed)
 changed=count
 ss=np.arange(0,c.length,.2);x=np.interp(ss,c.q[:,3],c.q[:,0]);z=np.interp(ss,c.q[:,3],c.q[:,1])
 q=np.asarray(Image.open(source('mask_v046_section.tga')).getchannel('A'),np.float32)/255
 coverage=map_coordinates(q,[(600-z)/600*len(q)-.5,x/600*len(q)-.5],order=1)
 oldq=np.asarray(Image.open(baseline('mask_v046_section.tga')).getchannel('A'),np.float32)/255
 old_coverage=map_coordinates(oldq,[(600-z)/600*len(oldq)-.5,x/600*len(oldq)-.5],order=1)
 # The accepted mask has two lightly feathered overlaps on its centreline.
 # Preserve its exact coverage, rather than extending the boundary to force 1.
 assert np.array_equal(q,oldq) and np.array_equal(coverage,old_coverage) and np.all(coverage>0)
 faces=[]
 for name,a,b in c.features:
  s=np.arange(a+.2,b-.2,.2);xx=np.interp(s,c.q[:,3],c.q[:,0]);zz=np.interp(s,c.q[:,3],c.q[:,1])
  p=next(p for p in c.profiles if p['id']==name);offset=p.get('lateral_offset_m',0.)
  xx-=offset*np.interp(s,c.q[:,3],c.v[:,1]);zz+=offset*np.interp(s,c.q[:,3],c.v[:,0]);f=c.face_weight(xx,zz)
  faces.append(dict(feature=name,station_m=[a,b],sampled_lateral_offset_m=offset,maximum_face_weight=float(f.max()),samples_with_grooves=int(np.count_nonzero(f>.05))))
 assert all(p['maximum_face_weight']>.1 for p in faces)
 text=(O/'compiled_track.hmf').read_text();assert len(list(layers(text)))==14
 strip_repeats=lambda t:re.sub(r'repetitions\s*=\s*[\d.]+','repetitions = SAME',t)
 assert strip_repeats(text)==strip_repeats((PREV/'compiled_track.hmf').read_text())
 report=dict(checks_pass=True,version='v058',approved_method='C+B',full_route=True,route_length_m=c.length,
  approved_C_photo_exact=True,approved_photo_sha256=PHOTO_SHA,photographic_tile_m=3,
  original_scanned_fine_normals_exact=True,full_accepted_photograph_footprint=True,centerline_coverage_min=float(coverage.min()),centerline_coverage_exact_v056=True,
  track_boundary_mask_exact=True,all_mask_footprints_exact=True,all_physical_material_declarations_exact=True,
  native_shader_repeat_semantics_confirmed='PiBoSo MXB guide: 0 inherits HMF; explicit absolute normal repeats supported',
  explicit_shader_repeats=dict(loose=200,packed=300,macro=1),changed_macro_pixels=changed,macro_changes_outside_footprint=0,
  jump_features=faces,starter_cultivation_follows_start_path=True,diagonal_tread_stamps_authored=False,
  layer_count=14,added_terrain_layers=0,added_terrain_images=0,active_terrain_inventory=after,active_shaders=shaders,
  rgba8_base_level_bytes_before=sum(r['rgba8_bytes'] for r in before),rgba8_base_level_bytes_after=sum(r['rgba8_bytes'] for r in after),
  rgba8_base_level_bytes_saved=saved,estimated_full_mip_bytes_saved=saved*4//3,
  memory_note='Source image allocation estimate; actual game RAM/VRAM and FPS unmeasured.',in_game_visual_check=False)
 save(O/'surface_validation.json',report);save(R/'V058_SOURCE/full_track_material_validation.json',report)
 print('V058_FULL_TRACK_C_B_VALIDATED: saved',saved,'RGBA8 base bytes;',len(faces),'jump features',flush=True)

def main():
 M.mkdir(parents=True,exist_ok=True);c=Circuit();colour();gc.collect();changed=atlas(c);masks(c);controls();validate(c,changed)

if __name__=='__main__':
 import sys
 if '--validate-existing' in sys.argv:validate(Circuit(),None)
 else:main()
