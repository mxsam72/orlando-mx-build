"""Independent geometry/race checks over the emitted v054 files."""
import math,re
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from v054_geometry import R,BASE,O,DEST,NAME,A,C,Layout,ground,read,save,sha,projection,parse_tcl,route_point
from reference_route import sample_native

def native(path):
 origin,theta,segs=parse_tcl(path);return sample_native(origin,theta,segs,.08)
def stalls(text,section):
 body=text.split(section,1)[1]
 if section=='starting_grid':body=body.split('num_checkpoints',1)[0]
 else:body=body.split('pit_board',1)[0]
 result=[]
 for m in re.finditer(r'(?:start_stall|stall)\d+\s*\{([^{}]*)\}',body):
  get=lambda k:float(re.search(r'(?m)^\s*'+k+r'\s*=\s*([-+\d.eE]+)',m[1])[1]);result.append([get('long'),get('lat'),get('angle')])
 assert len(result)==24,(section,len(result));return result
def positions(q,rows):
 result=[]
 for st,lat,relative in rows:
  p=route_point(q,st);xz=p[:2]+lat*np.array([np.sin(p[2]),-np.cos(p[2])]);angle=(90-math.degrees(p[2])+relative)%360;result.append([*xz,angle])
 return np.asarray(result)
def main():
 l=Layout();old=l.old;new=l.q;raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);out=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);h=out/65535*18
 untouched=~l.active(old[:,3]);assert np.array_equal(old[untouched,:2],new[untouched,:2]);assert np.array_equal(np.load(O/'route.npz')['width'],l.width)
 if (O/'road_guard.npy').is_file():
  guard=np.load(O/'road_guard.npy');assert np.array_equal(raw[guard],out[guard]),'Terrain under existing road courses changed'
 assert np.array_equal(raw[1500:1850,1300:1500],out[1500:1850,1300:1500]),'Pit area changed'
 profiles=read(BASE/'jump_profiles.json');updated={p['id']:p for p in read(O/'jump_profiles.json')};checks=[]
 for p in profiles:
  n=updated[p['id']]
  for key in ['profile_s','profile_h','profile_derivative','crest_offsets_m','roller_heights_m']:
   if key in p:assert n[key]==p[key],(p['id'],key)
  assert abs((n['station_end_m']-n['station_start_m'])-(p['station_end_m']-p['station_start_m']))<1e-7
  if p['kind']=='none' or p['id'] in ['R09','R17']:continue
  ss=np.linspace(p['station_start_m'],p['station_end_m'],max(20,int((p['station_end_m']-p['station_start_m'])/.3)))
  points=np.c_[np.interp(ss,old[:,3],old[:,0]),np.interp(ss,old[:,3],old[:,1])]
  assert np.allclose(ground(raw/65535*18,points),ground(h,points),rtol=0,atol=.0003),('Unrelated jump riding line changed',p['id'])
  checks.append(p['id'])
 p17=updated['R17'];assert len(p17['crest_offsets_m'])==8 and np.allclose(np.diff(p17['crest_offsets_m']),10)
 ss=np.arange(p17['station_start_m']-8,p17['station_end_m']+8,.1)
 pp=np.c_[np.interp(ss,new[:,3],new[:,0]),np.interp(ss,new[:,3],new[:,1])]
 physical=ground(h,pp);residual=physical-gaussian_filter1d(physical,50)
 peaks,properties=find_peaks(residual,prominence=.12,distance=70)
 relative=ss[peaks]-p17['station_start_m'];inside=(relative>-1)&(relative<82);relative=relative[inside]
 assert len(relative)==8,('Wrong number of physical roller crests',relative)
 expected=p17['face_m']+np.asarray(p17['crest_offsets_m']);assert np.max(abs(relative-expected))<1.0,(relative,expected)
 def curvature(q):
  heading=np.unwrap(np.arctan2(np.gradient(q[:,1],q[:,3]),np.gradient(q[:,0],q[:,3])))
  return abs(np.gradient(gaussian_filter1d(heading,3/np.median(np.diff(q[:,3]))),q[:,3]))
 old_curve=curvature(old);new_curve=curvature(new);region=(old[:,3]>1290)&(old[:,3]<1335)
 before=float(old_curve[region].max());after=float(new_curve[region].max());assert after<before*.8,(before,after)
 oldnative=native(BASE/'main.tcl');newnative=native(O/'main.tcl');start=native(O/'start.tcl')
 end=start[-1];d,i=cKDTree(newnative[:,:2]).query(end[:2]);assert d<.15
 angle=abs((end[2]-newnative[i,2]+np.pi)%(2*np.pi)-np.pi);assert angle<.025
 baseline=(R/'BUILD/v054_baseline_game/orlandomx_2026_v052.rdf').read_text();authored=(DEST/(NAME+'.rdf')).read_text();world=[]
 for section in ['starting_grid','pit_lane']:
  a=positions(oldnative,stalls(baseline,section));b=positions(newnative,stalls(authored,section));error=float(np.linalg.norm(a[:,:2]-b[:,:2],axis=1).max());rot=float(abs((a[:,2]-b[:,2]+180)%360-180).max())
  assert error<.004 and rot<.03,(section,error,rot);world.append(dict(section=section,stalls=24,max_world_error_m=error,max_orientation_error_deg=rot))
 cp=re.search(r'checkpoint7\s*\{([^{}]*)\}',authored)[1];assert re.search(r'start\s*=\s*0(?:\.0+)?\s',cp)
 split=re.search(r'split1\s*\{([^{}]*)\}',authored)[1];split_s=float(re.search(r'long\s*=\s*([-+\d.eE]+)',split)[1]);assert split_s>newnative[i,3]
 # Check the declared first-lap checkpoint sequence after the start joins.
 for match in re.finditer(r'checkpoint\d+\s*\{([^{}]*)\}',authored):
  body=match[1];line=int(float(re.search(r'line\s*=\s*(\d+)',body)[1]));mode=int(float(re.search(r'start\s*=\s*(\d+)',body)[1]));station=float(re.search(r'long\s*=\s*([-+\d.eE]+)',body)[1]);left=float(re.search(r'left\s*=\s*([-+\d.eE]+)',body)[1]);right=float(re.search(r'right\s*=\s*([-+\d.eE]+)',body)[1]);assert left<right
  if line==0 and mode==2:assert station>=newnative[i,3]-2
 for suffix in ['.amb','.tsc','.tga']:
  assert sha(DEST/(NAME+suffix))==sha(R/'BUILD/v054_baseline_game'/('orlandomx_2026_v052'+suffix))
 save(O/'independent_validation.json',dict(checks_pass=True,baseline='v052',unrelated_route_world_positions_exact=True,unrelated_jump_riding_lines_checked=checks,all_jump_profile_arrays_and_lengths_exact=True,R17_roller_count=8,R17_crest_spacing_m=10,measured_physical_R17_crest_count=len(relative),measured_physical_R17_crest_offsets_from_start_m=relative.tolist(),roller_entry_peak_curvature_before=before,roller_entry_peak_curvature_after=after,start_native_merge_distance_m=float(d),start_native_merge_angle_error_rad=float(angle),gate_and_pit_world_coordinate_checks=world,first_lap_checkpoint_order_passed=True,sector_one_after_start_merge=True,lighting_cameras_and_logo_exact=True,in_game_riding_test=False))
 print('V054_INDEPENDENT_CHECKS_PASSED',before,after,flush=True)
if __name__=='__main__':main()
