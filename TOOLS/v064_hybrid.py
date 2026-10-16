"""Original v062 B in all 14 corners; original C on the remaining MX surface."""
import gc,json,os,zipfile
import numpy as np
from PIL import Image
from v062_trials import R,BASE,Circuit as OriginalCircuit,source as original,write_image,smooth,sha,save
from v061_inputs import PINS,CACHE as INPUTS

O=R/'V064_OUTPUT';M=O/'materials';S=R/'V064_SOURCE';PREV=R/'V062_OUTPUT/C'
FADE=5.0
CHANGED={'v044_route_detail_n.tga','mask_v046_packed.tga','mask_v046_wear.tga'}

def source(name):return M/name if (M/name).is_file() else original(name,'C')

class Circuit(OriginalCircuit):
 def __init__(self):
  super().__init__()
  archive=INPUTS/'v044_source.zip';assert sha(archive)==PINS['v044_source.zip'][2]
  with zipfile.ZipFile(archive) as z:turns=json.loads(z.read('V044_OUTPUT/turns.json'))
  self.corners=[]
  for turn in turns:
   lo,hi=np.interp([turn['arc_start'],turn['arc_end']],self.route['v054_old_station'],self.q[:,3])
   self.corners.append(dict(id=turn['id'],station_m=[float(lo),float(hi)],entry_blend_m=[float(lo-FADE),float(lo)],exit_blend_m=[float(hi),float(hi+FADE)]))
  assert len(self.corners)==14 and all(t['station_m'][1]>t['station_m'][0] for t in self.corners)
 def by_station(self,s):
  w=np.zeros_like(s,dtype=float)
  for turn in self.corners:
   lo,hi=turn['station_m'];w=np.maximum(w,smooth((s-lo+FADE)/FADE)*smooth((hi+FADE-s)/FADE))
  return w
 def corner_weight(self,x,z):
  s,_=self.coords(x,z);pos=np.c_[x.ravel(),z.ravel()]
  dm,_=self.tree.query(pos,workers=2);ds,_=self.start_tree.query(pos,workers=2)
  start=((ds+1<dm)&(ds<24)).reshape(x.shape)
  return np.where(start,0,self.by_station(s))

def retain():
 O.mkdir(parents=True,exist_ok=True);M.mkdir(exist_ok=True);S.mkdir(exist_ok=True);rows=[]
 for name in ['terrain.raw','scenery.fbx','route.npz','jump_profiles.json','layout.json','main.tcl','start.tcl','compiled_track.hmf','trial_daylight.amb']:
  dest=O/name
  if not dest.exists():os.link(PREV/name,dest)
  assert sha(dest)==sha(PREV/name);rows.append(dict(file=name,sha256=sha(dest)))
 return rows

def author(c,name):
 b=np.asarray(Image.open(original(name,'B')));cc=np.asarray(Image.open(original(name,'C')));out=cc.copy();n=len(out);dx=600/n
 assert b.shape==cc.shape and b.dtype==cc.dtype
 normal=name=='v044_route_detail_n.tga'
 assert np.array_equal(b[:,:,3],cc[:,:,3]) if normal else np.array_equal(b[:,:,:3],cc[:,:,:3])
 counts=dict(B_exact_pixels=0,C_exact_pixels=0,transition_pixels=0,changed_pixels_from_C=0)
 for row in range(0,n,96):
  end=min(row+96,n);bb=b[row:end];before=cc[row:end]
  diff=np.any(bb[:,:,:3]!=before[:,:,:3],axis=2) if normal else bb[:,:,3]!=before[:,:,3]
  rr,col=np.nonzero(diff)
  if not len(rr):continue
  x=(col+.5)*dx;z=600-(rr+row+.5)*dx;w=c.corner_weight(x,z)
  isb=w>=1;isc=w<=0;blend=~(isb|isc);counts['B_exact_pixels']+=int(isb.sum());counts['C_exact_pixels']+=int(isc.sum());counts['transition_pixels']+=int(blend.sum())
  if normal:
   bv=bb[rr,col,:3];cv=before[rr,col,:3];new=cv.copy();new[isb]=bv[isb]
   v=(cv[blend]/127.5-1)*(1-w[blend,None])+(bv[blend]/127.5-1)*w[blend,None]
   v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-8);new[blend]=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)))
   out[row+rr,col,:3]=new;changed=np.any(new!=cv,axis=1)
   assert np.array_equal(new[isb],bv[isb]) and np.array_equal(new[isc],cv[isc])
  else:
   bv=bb[rr,col,3];cv=before[rr,col,3];new=np.uint8(np.rint(cv*(1-w)+bv*w));out[row+rr,col,3]=new;changed=new!=cv
   assert np.array_equal(new[isb],bv[isb]) and np.array_equal(new[isc],cv[isc])
  counts['changed_pixels_from_C']+=int(changed.sum())
  if row//96%12==0:print('HYBRID_ROWS',name,row,'/',n,flush=True)
 if normal:assert np.array_equal(out[:,:,3],cc[:,:,3])
 else:
  assert np.array_equal(out[:,:,:3],cc[:,:,:3]);assert np.array_equal(out[:,:,3]>0,cc[:,:,3]>0)
 write_image(out,M/name);del b,cc,out;gc.collect();return dict(file=name,**counts)

def validate(c,retained,edits):
 trials=json.loads((R/'V062_SOURCE/trial_validation.json').read_text());bc={d['method']:d for d in trials['designs'] if d['method'] in ['B','C']};images=[]
 for item in bc['C']['active_terrain_inventory']:
  name=item['file'];p=source(name);im=Image.open(p);actual=sha(p);assert list(im.size)==item['size'] and im.mode==item['mode']
  if name not in CHANGED:
   other=next(a for a in bc['B']['active_terrain_inventory'] if a['file']==name)
   assert actual==item['sha256']==other['sha256'],name
  images.append(dict(item,sha256=actual))
 # Verify every named arc, across all sampled stations, has unmodified B weight.
 for turn in c.corners:
  lo,hi=turn['station_m'];assert np.all(c.by_station(np.linspace(lo,hi,501))==1)
  assert c.by_station(np.array([lo-FADE-.01,hi+FADE+.01])).min()>=0
 ss=np.arange(0,c.length,.025);weights=c.by_station(ss);assert np.all((weights>=0)&(weights<=1)) and np.any(weights==0)
 # Check the actual written images independently in chunks against source B/C.
 for edit in edits:
  name=edit['file'];im=np.asarray(Image.open(source(name)));b=np.asarray(Image.open(original(name,'B')));cc=np.asarray(Image.open(original(name,'C')));n=len(im);normal=name=='v044_route_detail_n.tga'
  for row in range(0,n,192):
   end=min(row+192,n);diff=np.any(b[row:end]!=cc[row:end],axis=2);rr,col=np.nonzero(diff)
   if not len(rr):continue
   w=c.corner_weight((col+.5)*600/n,600-(rr+row+.5)*600/n)
   assert np.array_equal(im[row+rr[w==1],col[w==1]],b[row+rr[w==1],col[w==1]])
   assert np.array_equal(im[row+rr[w==0],col[w==0]],cc[row+rr[w==0],col[w==0]])
   # A changed output texel must be a B/C difference within the blend support.
   same=~diff;assert np.array_equal(im[row:end][same],cc[row:end][same])
  if normal:assert np.array_equal(im[:,:,3],cc[:,:,3])
  else:assert np.array_equal(im[:,:,:3],cc[:,:,:3]) and np.array_equal(im[:,:,3]>0,cc[:,:,3]>0)
  # Speedway roller and its shoulder remain byte-exact, including visual maps.
  box=(int(525/600*n),int((600-252)/600*n),int(545/600*n)+1,int((600-218)/600*n)+1)
  x0,y0,x1,y1=box;assert np.array_equal(im[y0:y1,x0:x1],cc[y0:y1,x0:x1])
  del im,b,cc;gc.collect()
 for name in ['terrain.raw','scenery.fbx']:
  assert sha(O/name)==sha(BASE/name)
 allocation=sum(a['rgba8_bytes'] for a in images);assert allocation==bc['B']['rgba8_base_level_bytes']==bc['C']['rgba8_base_level_bytes']
 report=dict(checks_pass=True,version='v064 original B corners plus C elsewhere',
  baseline_source_commit='5e5f34951f96bb09a940ce6326a02e31176b1315',rejected_dense_v063_not_used=True,
  corner_method='Original v062 B; exact throughout every mapped T01-T14 corner arc',remaining_surface_method='Original v062 C; exact outside corner blend support, including start lane',
  corner_blend_distance_m=FADE,corner_regions=c.corners,changed_material_files=edits,retained_source_files=retained,active_terrain_inventory=images,
  texture_allocation_bytes=allocation,added_images=0,added_layers=0,layer_count=14,
  normal_specular_alpha_exact=True,mask_RGB_and_nonzero_footprints_exact=True,photographic_RGB_and_fine_normals_exact_v062=True,
  all_geometry_and_wall_roller_exact=True,wall_roller_material_texels_exact=True,vehicles_and_sign_exact=True,lighting_exact_v062=True,
  final_compilation_started=False,in_game_verified=False,
  preview_note='Actual material/terrain source renders with approximate filtering and daylight; scenery omitted; not native game captures.')
 save(S/'corner_regions.json',c.corners);save(S/'surface_validation.json',report);save(O/'surface_validation.json',report)
 print('V064_HYBRID_PASS; all 14 arcs B; remaining surface C; roller exact; allocation',allocation,flush=True)

def main():
 retained=retain();c=Circuit();edits=[author(c,name) for name in sorted(CHANGED)];validate(c,retained,edits)

if __name__=='__main__':main()
