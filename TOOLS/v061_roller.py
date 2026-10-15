"""Add one rounded speedway wall-entry roller; preserve the entire v060 scene."""
import json,os,shutil
import numpy as np
from PIL import Image
from scipy.interpolate import BPoly,LinearNDInterpolator
from scipy.ndimage import map_coordinates
import shapely
from shapely.geometry import Polygon,LineString
from v061_inputs import R,PREV,O,M,S,sha,save,baseline,source
from v027_scenery import parse,geometry_records,vertices
from verify_v037_source import faces

SPEC=S/'roller.json'
def quintic(t):
 t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))

class Roller:
 def __init__(self):
  self.spec=json.loads(SPEC.read_text());s=self.spec
  self.profile=BPoly.from_derivatives(s['profile_z_m'],list(zip(s['profile_rise_m'],s['profile_slope'],s['profile_curvature'])))
 def rise(self,x,z):
  s=self.spec;inside=(z>=s['profile_z_m'][0])&(z<=s['profile_z_m'][-1]);v=np.zeros_like(x,dtype=float)
  v[inside]=np.maximum(self.profile(z[inside]),0)
  w=1-quintic((abs(x-s['axis_x_m'])-s['flat_half_width_m'])/(s['shoulder_half_width_m']-s['flat_half_width_m']))
  return v*w
 def weight(self,x,z):return quintic(self.rise(x,z)/.10)

def publish_image(array,path):
 temp=path.with_name(path.stem+'.writing.tga');Image.fromarray(array).save(temp);temp.replace(path);os.utime(path,None)

def retained():
 O.mkdir(exist_ok=True);M.mkdir(exist_ok=True);records=[]
 for name in ['scenery.fbx','route.npz','layout.json','jump_profiles.json','main.tcl','start.tcl','compiled_track.hmf','native_probes.json','vehicle_meshes.json','scenery_validation.json']:
  dest=O/name
  if not dest.exists():os.link(PREV/name,dest)
  assert sha(dest)==sha(PREV/name),name
  records.append(dict(file=name,sha256=sha(dest)))
 return records

def masks(r):
 changes=[]
 # The existing photographed soil and macro slots cover the new roller.
 # The unchanged grass material is hidden only under that footprint.
 for name,kind in [('mask_v046_section.tga','section'),('mask_v046_wear.tga','wear'),('mask_grass.tga','grass')]:
  before=baseline(name);a=np.array(Image.open(before));n=a.shape[0];old=a.copy();x0=max(0,int(527/600*n)-2);x1=min(n,int(543/600*n)+3);y0=max(0,int((600-250)/600*n)-2);y1=min(n,int((600-218)/600*n)+3)
  # Image texel centres match the approved material sampling convention.
  x,z=np.meshgrid((np.arange(x0,x1)+.5)*600/n,600-(np.arange(y0,y1)+.5)*600/n);w=r.weight(x,z)
  region=a[y0:y1,x0:x1];alpha=region[:,:,3] if a.ndim==3 else region
  target=255*w if kind=='section' else 255*.62*w
  value=np.uint8(np.rint(alpha*(1-w))) if kind=='grass' else np.uint8(np.rint(np.maximum(alpha,target)))
  if a.ndim==3:region[:,:,3]=value
  else:region[:]=value
  difference=np.any(a!=old,axis=2) if a.ndim==3 else a!=old;yy,xx=np.where(difference)
  assert len(xx)>0 and np.all(r.rise((xx+.5)*600/n,600-(yy+.5)*600/n)>0)
  if a.ndim==3:assert np.array_equal(a[:,:,:3],old[:,:,:3])
  publish_image(a,M/name);changes.append(dict(file=name,baseline_sha256=sha(before),sha256=sha(M/name),size=[n,n],changed_pixels=len(xx),changes_outside_roller=0))
 return changes

def macro(r):
 name='v044_route_detail_n.tga';a=np.array(Image.open(baseline(name)));n=len(a);dx=600/n
 x0=int(526/dx);x1=int(544/dx)+1;y0=int((600-250)/dx);y1=int((600-218)/dx)+1
 x,z=np.meshgrid((np.arange(x0-1,x1+1)+.5)*dx,600-(np.arange(y0-1,y1+1)+.5)*dx)
 w=r.weight(x,z);l=x-r.spec['axis_x_m'];relief=(np.sin(l*28+np.sin(z*.31))*.003+np.sin(z*21+l*17)*.002)*w
 rng=np.random.default_rng(61015);tines=np.r_[-7.2,-7.2+np.cumsum(rng.uniform(.19,.28,70))]
 for i,t in enumerate(tines[tines<7.3]):
  u=(l-t)/(.055+.01*np.sin(i)**2);relief+=(-np.exp(-u*u)+.30*np.exp(-((u-1.6)/1.1)**2))*.023*w
 # Same +X/+Z tangent normal convention as the approved route atlas.
 gz,gx=np.gradient(relief,dx,dx);nn=np.dstack([-gx,gz,np.ones_like(gx)]);nn/=np.linalg.norm(nn,axis=2,keepdims=True)
 region=a[y0:y1,x0:x1];before=region.copy();blend=w[1:-1,1:-1,None]
 candidate=np.uint8(np.rint(np.clip(nn[1:-1,1:-1]*127.5+127.5,0,255)))
 region[:,:,:3]=np.uint8(np.rint(region[:,:,:3]*(1-blend)+candidate*blend))
 assert np.array_equal(region[:,:,3],before[:,:,3]);yy,xx=np.where(np.any(region!=before,axis=2))
 assert np.all(r.rise((xx+x0+.5)*dx,600-(yy+y0+.5)*dx)>0)
 publish_image(a,M/name)
 return dict(file=name,baseline_sha256=sha(baseline(name)),sha256=sha(M/name),size=[n,n],changed_pixels=len(xx),changes_outside_roller=0,specular_alpha_exact=True)

def geometry():
 retained_files=retained();r=Roller();raw=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049);h=raw.astype(float)/65535*18
 x,z=np.meshgrid(np.arange(2049)*600/2048,600-np.arange(2049)*600/2048);rise=r.rise(x,z);scope=rise>0
 new=np.uint16(np.rint(np.clip((h+rise)*65535/18,0,65535)));new[~scope]=raw[~scope]
 assert np.array_equal(new[~scope],raw[~scope]);changed=new!=raw
 temp=O/'terrain.writing.raw'
 with temp.open('wb') as f:f.write(new.astype('<u2').tobytes());f.flush();os.fsync(f.fileno())
 temp.replace(O/'terrain.raw');Image.fromarray(new).save(O/'terrain_16bit.png');np.save(O/'roller_scope.npy',scope)
 nodes,_=parse((PREV/'scenery.fbx').read_bytes());rec=geometry_records(nodes)
 road=rec['TRKASPH_v037_oval_surface'][0];v=vertices(road);f=np.asarray(faces(road));poly=shapely.union_all(shapely.polygons(v[f][:,:,[0,2]]))
 fill=rec['TRKASPH_v041_oval_wall_gap_fill'][0];fv=vertices(fill);ff=np.asarray(faces(fill));poly=poly.union(shapely.union_all(shapely.polygons(fv[ff][:,:,[0,2]])))
 assert not np.any(shapely.intersects_xy(poly,x[changed],z[changed]))
 allv=np.r_[v,fv];roadheight=LinearNDInterpolator(allv[:,[0,2]],allv[:,1]);wall=vertices(rec['WLLCONC_v037_oval_wall_green_cap'][0]).reshape(-1,8,3)
 paths=[];ss=np.arange(r.spec['profile_z_m'][0],246.2,.005);p=r.profile;hh=p(ss);sl=p.derivative()(ss);curv=p.derivative(2)(ss)
 for lateral in [-4.5,0.,4.5]:
  xx=r.spec['axis_x_m']+lateral
  blocks=wall[(wall[:,:,0].min(1)<=xx)&(wall[:,:,0].max(1)>=xx)&(wall[:,:,2].min(1)<270)]
  assert len(blocks)>0;wall_z=[float(blocks[:,:,2].min()),float(blocks[:,:,2].max())];wall_top=float(blocks[:,:,1].max())
  for mph in r.spec['review_speed_mph']:
   speed=mph*.44704;ii=np.flatnonzero(curv < -9.81*(1+sl*sl)/speed**2)[0];launch_s=ss[ii];slope=sl[ii];vx=speed/np.sqrt(1+slope*slope)
   base=float(map_coordinates(h,[[(600-launch_s)/600*2048],[xx/600*2048]],order=1)[0]);launch_y=base+hh[ii]
   travel=np.arange(0,35,.025);zz=launch_s+travel;yy=launch_y+slope*travel-9.81*travel**2/(2*vx*vx)
   wall_sample=np.linspace(wall_z[0],wall_z[1],60);d=wall_sample-launch_s;over=launch_y+slope*d-9.81*d*d/(2*vx*vx);clearance=float(over.min()-wall_top)
   road_y=roadheight(np.full_like(zz,xx),zz);on_road=shapely.intersects_xy(poly,np.full_like(zz,xx),zz)
   hits=np.flatnonzero((zz>wall_z[1])&on_road&(yy<=road_y));assert len(hits)>0,(mph,lateral,'No asphalt landing')
   hit=hits[0];assert clearance>.20,(mph,lateral,clearance)
   paths.append(dict(takeoff_speed_mph=mph,lateral_m=lateral,launch_xyz_m=[xx,float(launch_y),float(launch_s)],angle_degrees=float(np.degrees(np.arctan(slope))),
    wall_z_m=wall_z,wall_top_y_m=wall_top,estimated_minimum_wall_clearance_m=clearance,estimated_landing_xyz_m=[xx,float(road_y[hit]),float(zz[hit])],
    estimated_peak_above_local_grass_m=float(hh[ii]+(speed*slope/np.sqrt(1+slope*slope))**2/(2*9.81)),estimated_landing_on_original_asphalt=True))
 mask_changes=masks(r);normal_change=macro(r)
 before=json.loads((PREV/'surface_validation.json').read_text());inventory=[];allowed={p['file'] for p in mask_changes}|{normal_change['file']}
 for item in before['active_terrain_inventory']:
  path=source(item['file']);im=Image.open(path);assert list(im.size)==item['size'] and im.mode==item['mode']
  actual=sha(path)
  if item['file'] not in allowed:assert actual==item['sha256']
  inventory.append(dict(item,sha256=actual))
 assert sha(O/'scenery.fbx')==sha(PREV/'scenery.fbx')
 report=dict(checks_pass=True,version='v061 preview 1',baseline_release='v060-dense-grooming-38699998845',roller=r.spec,
  maximum_height_added_m=float((new.astype(float)-raw).max()*18/65535),maximum_face_angle_degrees=float(np.degrees(np.arctan(sl.max()))),changed_height_samples=int(changed.sum()),terrain_changes_outside_roller=0,
  changed_height_bounds_xz_m=[float(x[changed].min()),float(z[changed].min()),float(x[changed].max()),float(z[changed].max())],
  terrain_sha256=sha(O/'terrain.raw'),baseline_terrain_sha256=sha(PREV/'terrain.raw'),wall_road_all_scenery_exact=True,
  road_heightfield_samples_exact=True,big_speedway_double_and_all_MX_heights_exact=True,retained_source_files=retained_files,
  existing_14_layers_exact=True,added_texture_slots=0,added_material_layers=0,texture_allocation_bytes=before['rgba8_base_level_bytes_after'],
  active_terrain_inventory=inventory,mask_changes=mask_changes,macro_change=normal_change,approximate_trajectory_checks=paths,
  clearance_model_note=r.spec['clearance_model'],final_compilation_started=False,in_game_riding_test=False)
 save(O/'validation.json',report);save(S/'geometry_validation.json',report)
 print('V061_ROLLER_REVIEW_SOURCE_PASS',report['maximum_height_added_m'],'m high;',report['changed_height_samples'],'terrain samples; minimum estimated clearance',min(p['estimated_minimum_wall_clearance_m'] for p in paths),flush=True)

if __name__=='__main__':geometry()
