"""Scoped v059 corner transitions and the user-requested R11 pair translation."""
import copy,json,os,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates
from scipy.signal import find_peaks
from v058_inputs import R,sha,save
from v058_surface import Circuit as PreviousCircuit
from v056_geometry import cross_points,corner_regions
from v054_geometry import raster_points,projection,smooth,ground
from refine_jumps import supports
from jump_v024 import envelope

PREV=R/'V058_OUTPUT';O=R/'V059_OUTPUT';M=O/'materials';S=R/'V059_SOURCE'

def retain():
 O.mkdir(exist_ok=True);M.mkdir(exist_ok=True);S.mkdir(exist_ok=True)
 for name in ['route.npz','layout.json','main.tcl','start.tcl','compiled_track.hmf','native_probes.json','vehicle_meshes.json','scenery_validation.json']:
  shutil.copy2(PREV/name,O/name);assert sha(PREV/name)==sha(O/name)
 # Immutable approved scenery can share storage; no rewrite or duplicated mesh.
 if not (O/'scenery.fbx').exists() or sha(O/'scenery.fbx')!=sha(PREV/'scenery.fbx'):
  temp=O/'scenery_input_link.fbx';temp.unlink(missing_ok=True);os.link(PREV/'scenery.fbx',temp);temp.replace(O/'scenery.fbx')
 assert sha(O/'scenery.fbx')==sha(PREV/'scenery.fbx')=='59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604'
 shutil.copytree(PREV/'facility_textures',O/'facility_textures',dirs_exist_ok=True)

def main():
 retain();c=PreviousCircuit();raw=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049);h=raw.astype(float)/65535*18
 target=h.copy();scope=np.zeros(h.shape,bool);road=np.load(R/'V054_OUTPUT/road_guard.npy');corners=dict((n,(lo,hi)) for n,lo,hi in corner_regions(c.q,c.route['v054_old_station']))
 # A 1.8m terrain filter rounds the inner drop and crest together; a broad
 # smooth blend confines it to the two requested banks and their entry joins.
 softened=gaussian_filter(h,1.8/(600/2048),mode='nearest');corner_reports=[]
 for name in ['T03','T09']:
  lo,hi=corners[name];stations=np.linspace(lo-2,hi+2,300);p=cross_points(c.q,stations,0);a=p.min(0)-13;b=p.max(0)+13
  rr,cc,pts=raster_points(2049,[a[0],a[1],b[0],b[1]]);_,_,s,l=projection(c.q,pts)
  w=smooth((s-lo)/4)*(1-smooth((s-hi+4)/4))*(1-smooth((abs(l)-8.0)/3.0))
  # Hairpin route projections switch to an adjacent lane at their Voronoi
  # boundary. Blur the edit mask in world space so that switch cannot form a
  # new height step on the outer bank or the adjacent flat.
  w=gaussian_filter(w.reshape(len(rr),len(cc)),1.2/(600/2048)).ravel();w[w<.002]=0
  old=target[np.ix_(rr,cc)].ravel();desired=softened[np.ix_(rr,cc)].ravel();local=old+(desired-old)*w
  local_road=road[np.ix_(rr,cc)].ravel();local[local_road]=old[local_road]
  target[np.ix_(rr,cc)]=local.reshape(len(rr),len(cc));scope[np.ix_(rr,cc)]|=((w>0)&~local_road).reshape(len(rr),len(cc))
  ss=np.arange(lo+5,hi-5,.4);ll=np.arange(-8,8.01,.1);sg,lg=np.meshgrid(ss,ll);pp=cross_points(c.q,sg,lg).reshape(-1,2)
  before=ground(h,pp).reshape(sg.shape);after=ground(target,pp).reshape(sg.shape)
  gb=np.gradient(before,.1,axis=0);ga=np.gradient(after,.1,axis=0)
  cb=np.gradient(gb,.1,axis=0);ca=np.gradient(ga,.1,axis=0)
  corner_reports.append(dict(corner=name,station_m=[lo,hi],maximum_cross_grade_before=float(abs(gb).max()),maximum_cross_grade_after=float(abs(ga).max()),
   cross_curvature_rms_before=float(np.sqrt(np.mean(cb*cb))),cross_curvature_rms_after=float(np.sqrt(np.mean(ca*ca))),maximum_height_edit_m=float(abs(after-before).max())))
 profiles=json.loads((PREV/'jump_profiles.json').read_text());old=next(p for p in profiles if p['id']=='R11');moved=copy.deepcopy(old)
 shift=float(np.diff(old['crest_offsets_m'])[0]);assert abs(shift-9.9)<1e-7
 for key in ['station_start_m','station_end_m','lip_s']:moved[key]+=shift
 moved['v059_shift_m']=shift;moved['notes']='v059: translate the second/third visible mounds together; first moved crest occupies the old third crest; spacing remains 9.9m.'
 p=cross_points(c.q,np.linspace(old['station_start_m']-2,moved['station_end_m']+2,300),0);a=p.min(0)-15;b=p.max(0)+15
 rr,cc,pts=raster_points(2049,[a[0],a[1],b[0],b[1]]);_,_,ss,ll=projection(c.q,pts)
 before=envelope(pts,supports([old],c.q,c.route['width'])).reshape(len(rr),len(cc))
 after=envelope(pts,supports([moved],c.q,c.route['width'])).reshape(len(rr),len(cc))
 delta=gaussian_filter(after-before,.65).ravel()
 # Preserve R12's first crest and all later rollers. Only the very end of the
 # moved landing blends into the existing approach; no other crest is moved.
 r12=next(p for p in profiles if p['id']=='R12');guard_start=r12['lip_s']-.8
 w=smooth((ss-old['station_start_m']+1)/1)*(1-smooth((ss-guard_start+1)/1))
 w*=1-smooth((abs(ll)-11)/2);w[road[np.ix_(rr,cc)].ravel()]=0
 target[np.ix_(rr,cc)]+=(delta*w).reshape(len(rr),len(cc));scope[np.ix_(rr,cc)]|=(w>0).reshape(len(rr),len(cc))
 profiles=[moved if p['id']=='R11' else p for p in profiles]
 out=np.uint16(np.rint(np.clip(target/18*65535,0,65535)));out[~scope]=raw[~scope]
 assert np.array_equal(out[~scope],raw[~scope]) and np.array_equal(out[road],raw[road])
 (O/'terrain.raw').write_bytes(out.astype('<u2').tobytes());Image.fromarray(out).save(O/'terrain_16bit.png');np.save(O/'geometry_scope.npy',scope);save(O/'jump_profiles.json',profiles)
 after_h=out.astype(float)/65535*18;retained=[]
 for p in profiles:
  if p['id']=='R11' or p['kind']=='none':continue
  centers=np.asarray(p['crest_offsets_m'])+p['lip_s'];pp=cross_points(c.q,centers,p.get('lateral_offset_m',0.))
  change=float(abs(ground(after_h,pp)-ground(h,pp)).max());assert change<1e-7,(p['id'],change)
  retained.append(dict(feature=p['id'],crest_stations_m=centers.tolist(),crest_heights_exact=True))
 for r in corner_reports:
  assert r['maximum_cross_grade_after']<r['maximum_cross_grade_before']*.88,r
  assert r['cross_curvature_rms_after']<r['cross_curvature_rms_before']*.8,r
 old_crests=np.asarray(old['crest_offsets_m'])+old['lip_s'];new_crests=np.asarray(moved['crest_offsets_m'])+moved['lip_s']
 assert abs(new_crests[0]-old_crests[1])<1e-7 and abs(np.diff(new_crests)[0]-shift)<1e-7
 report=dict(checks_pass=True,version='v059',source_terrain_sha256=sha(PREV/'terrain.raw'),terrain_sha256=sha(O/'terrain.raw'),changed_raw_samples=int((out!=raw).sum()),
  geometry_edits_only_inside_scope=True,road_terrain_exact=True,corner_smoothing=corner_reports,unrelated_jump_crests_exact=retained,
  moved_pair=dict(feature='R11',shift_forward_m=shift,old_crest_stations_m=old_crests.tolist(),new_crest_stations_m=new_crests.tolist(),crest_spacing_m=shift,first_new_crest_at_old_second_crest=True,profile_arrays_exact=True),
  route_and_start_byte_exact=True,approved_van_sign_trucks_byte_exact=True,scenery_sha256=sha(O/'scenery.fbx'),final_compilation_started=False)
 save(O/'terrain_validation.json',report);save(S/'geometry_validation.json',report)
 print('V059_GEOMETRY_PASS',json.dumps(dict(corners=corner_reports,pair=report['moved_pair'])),flush=True)

if __name__=='__main__':main()
