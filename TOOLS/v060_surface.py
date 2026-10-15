"""Tighten added grooming everywhere, without new textures or geometry."""
import json,os,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter1d
import v059_surface as previous_author
from v059_surface import Circuit as OldCircuit,source as previous
from v058_surface import inventory
from v059_geometry import R,sha,save,cross_points,smooth

PREV=R/'V059_OUTPUT';O=R/'V060_OUTPUT';M=O/'materials';S=R/'V060_SOURCE'

def source(name):return M/name if (M/name).is_file() else previous(name)

def retain():
 O.mkdir(exist_ok=True);M.mkdir(exist_ok=True);S.mkdir(exist_ok=True)
 names=['terrain.raw','terrain_16bit.png','route.npz','layout.json','main.tcl','start.tcl','compiled_track.hmf','jump_profiles.json','scenery.fbx','native_probes.json','vehicle_meshes.json','scenery_validation.json','terrain_validation.json']
 for name in names:
  dest=O/name
  if not dest.exists():os.link(PREV/name,dest)
  assert sha(dest)==sha(PREV/name),name
 return [dict(file=n,sha256=sha(O/n)) for n in names]

class Circuit(OldCircuit):
 def __init__(self):
  super().__init__();rng=np.random.default_rng(600151);old_counts={r['section']:r['line_count'] for r in self.spacing}
  centres=[];widths=[];depths=[];labels=[]
  checks=[]
  for name,lo,hi in self.cross_regions:
   ss=np.arange(lo-1,hi+1.01,.05);lat=np.linspace(-9,9,37);sg,lg=np.meshgrid(ss,lat);p=cross_points(self.q,sg,lg);hh=self.terrain.ground(p[:,:,0],p[:,:,1]);xyz=np.dstack([p,hh])
   metric=maximum_filter1d(np.linalg.norm(np.gradient(xyz,.05,axis=1),axis=2).max(0),31,mode='nearest');position=lo-.5;local=[]
   while position<hi+.5:
    factor=max(float(np.interp(position,ss,metric)),1.);local.append(position);widths.append(rng.uniform(.045,.067)/factor);depths.append(rng.uniform(.028,.042));labels.append(name);position+=rng.uniform(.18,.28)/factor
   centres.extend(local);sg,lg=np.meshgrid(np.array(local),lat);p=cross_points(self.q,sg,lg);xyz=np.dstack([p,self.terrain.ground(p[:,:,0],p[:,:,1])]);gaps=np.linalg.norm(np.diff(xyz,axis=1),axis=2)
   assert gaps.max()<=.30 and len(local)>old_counts[name]
   checks.append(dict(section=name,station_m=[lo,hi],old_line_count=old_counts[name],new_line_count=len(local),maximum_3d_spacing_m=float(gaps.max()),minimum_3d_spacing_m=float(gaps.min()),lateral_validation_m=[-9,9]))
  order=np.argsort(centres);self.cross_centres=np.asarray(centres)[order];self.cross_width=np.asarray(widths)[order];self.cross_depth=np.asarray(depths)[order];self.cross_labels=np.asarray(labels)[order];self.dense_checks=checks
  # The other added pass runs lengthwise on R03/R07. Tighten those tines too,
  # measuring across the actual sloping faces rather than in atlas pixels.
  old_tines=len(self.tines);lat=np.arange(-9.,9.001,.04);metric=np.ones_like(lat)
  for name,lo,hi in self.full_faces:
   ss=np.arange(lo,hi+.01,.25);lg,sg=np.meshgrid(lat,ss);p=cross_points(self.q,sg,lg);xyz=np.dstack([p,self.terrain.ground(p[:,:,0],p[:,:,1])])
   metric=np.maximum(metric,np.linalg.norm(np.gradient(xyz,.04,axis=1),axis=2).max(0))
  metric=maximum_filter1d(metric,15,mode='nearest');tines=[];position=-8.7
  while position<8.8:
   tines.append(position);position+=rng.uniform(.18,.28)/max(float(np.interp(position,lat,metric)),1.)
  self.tines=np.asarray(tines);self.face_checks=[];assert len(tines)>old_tines
  for name,lo,hi in self.full_faces:
   ss=np.arange(lo,hi+.01,.25);lg,sg=np.meshgrid(self.tines,ss);p=cross_points(self.q,sg,lg);xyz=np.dstack([p,self.terrain.ground(p[:,:,0],p[:,:,1])]);gaps=np.linalg.norm(np.diff(xyz,axis=1),axis=2)
   assert gaps.max()<=.30
   self.face_checks.append(dict(section=name,old_line_count=old_tines,new_line_count=len(tines),maximum_3d_spacing_m=float(gaps.max()),minimum_3d_spacing_m=float(gaps.min())))
 def edit_weight(self,x,z):
  _,_,cross,long=self.weights(x,z)
  return np.maximum(cross,long)

def constrain(c):
 """Keep every texel outside the existing grooming envelope exact to v059."""
 path=M/'v044_route_detail_n.tga';a=np.array(Image.open(path));old=Image.open(previous('v044_route_detail_n.tga'));n=len(a);count=0
 for row in range(0,n,96):
  end=min(n,row+96);before=np.asarray(old.crop((0,row,n,end)));candidate=a[row:end]
  yy,xx=np.where(np.any(candidate[:,:,:3]!=before[:,:,:3],axis=2))
  if len(xx):
   w=c.edit_weight((xx+.5)*600/n,600-(yy+row+.5)*600/n)
   result=np.uint8(np.rint(before[yy,xx,:3]*(1-w[:,None])+candidate[yy,xx,:3]*w[:,None]))
   candidate[yy,xx,:3]=result
   changed=np.any(result!=before[yy,xx,:3],axis=1);assert np.all(w[changed]>0);count+=int(changed.sum())
  assert np.array_equal(candidate[:,:,3],before[:,:,3])
 temporary=M/'dense_grooming_writing.tga';Image.fromarray(a).save(temporary);temporary.replace(path);return count

def main():
 retained=retain();c=Circuit();old_m=previous_author.M
 try:
  previous_author.M=M;previous_author.author(c)
 finally:previous_author.M=old_m
 assert sha(M/'mask_v046_wear.tga')==sha(previous('mask_v046_wear.tga'));(M/'mask_v046_wear.tga').unlink()
 changed=constrain(c);before,_=inventory(previous);after,shaders=inventory(source);old={r['file']:r for r in before}
 assert {r['file'] for r in before}=={r['file'] for r in after}
 assert sum(r['rgba8_bytes'] for r in before)==sum(r['rgba8_bytes'] for r in after)
 for r in after:
  if r['file']!='v044_route_detail_n.tga':assert r['sha256']==old[r['file']]['sha256'],r['file']
 report=dict(checks_pass=True,version='v060',change='Tighter added grooming in every existing area',requested_spacing_cap_m=.30,random_target_gap_range_m=[.18,.28],
  spacing_checks=c.dense_checks,full_width_face_checks=c.face_checks,all_14_corners_denser=True,all_16_perpendicular_regions_denser=True,all_added_face_tines_denser=True,
  changed_macro_pixels=changed,changes_outside_existing_grooming_envelopes=0,normal_specular_alpha_exact=True,
  retained_source_files=retained,entire_terrain_and_jump_layout_exact_v059=True,all_scenery_exact_v059=True,all_colour_maps_fine_normals_and_masks_exact_v059=True,
  active_terrain_inventory=after,active_shaders=shaders,rgba8_base_level_bytes_before=sum(r['rgba8_bytes'] for r in before),rgba8_base_level_bytes_after=sum(r['rgba8_bytes'] for r in after),
  added_layers=0,added_images=0,normal_atlas_size=[8192,8192],final_compilation_started=False,in_game_verified=False,
  memory_note='Texture source allocation unchanged from v059. Actual game RAM/VRAM and FPS unmeasured.')
 save(O/'surface_validation.json',report);save(S/'surface_validation.json',report)
 print('V060_DENSE_GROOMING_PASS',changed,'pixels;',sum(r['old_line_count'] for r in c.dense_checks),'->',sum(r['new_line_count'] for r in c.dense_checks),'perpendicular lines; max gap',max(r['maximum_3d_spacing_m'] for r in c.dense_checks+c.face_checks),flush=True)

if __name__=='__main__':main()
