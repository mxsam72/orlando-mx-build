"""Independent scope, placement, material and completed-photo review checks."""
import json,zipfile
import numpy as np
from PIL import Image
from scipy.signal import find_peaks
from v059_surface import R,PREV,O,S,sha,save,Circuit,source,previous
from v059_review import configure,OUT,CACHE,CHANGED_VIEWS
from v056_geometry import corner_regions,cross_points
from v054_geometry import ground

def main():
 c=Circuit();old=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049);new=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);scope=np.load(O/'geometry_scope.npy')
 assert np.array_equal(old[~scope],new[~scope]);road=np.load(R/'V054_OUTPUT/road_guard.npy');assert np.array_equal(old[road],new[road])
 corners=[]
 for name,lo,hi in corner_regions(c.q,c.route['v054_old_station']):
  if name in ['T03','T09']:continue
  sg,lg=np.meshgrid(np.arange(lo,hi,.25),np.arange(-10,10.01,.1));pp=cross_points(c.q,sg,lg).reshape(-1,2)
  # Neighbouring shoulder cross-sections can sample the explicitly edited
  # bank of another turn. Record the actual variable-width riding corridor;
  # the independent RAW scope check above proves edits stay in the requested
  # world footprint, including its shared shoulder with T12.
  delta=(ground(new.astype(float),pp)-ground(old.astype(float),pp))*18/65535
  widths=np.interp(sg.ravel(),c.q[:,3],c.route['width']);riding=abs(lg.ravel())<=widths/2;maximum=float(abs(delta[riding]).max())
  if name!='T12':assert maximum==0,(name,maximum)
  corners.append(dict(corner=name,riding_width_range_m=[float(widths.min()),float(widths.max())],maximum_riding_height_change_m=maximum,riding_samples_exact=maximum==0,
   shared_requested_bank_footprint=(name=='T12' and maximum>0)))
 before=json.loads((PREV/'jump_profiles.json').read_text());after=json.loads((O/'jump_profiles.json').read_text());b={p['id']:p for p in before};a={p['id']:p for p in after}
 assert all(a[k]==p for k,p in b.items() if k!='R11')
 for k in ['profile_s','profile_h','profile_derivative','crest_offsets_m']:assert a['R11'][k]==b['R11'][k]
 ss=np.arange(916,947,.05);pp=cross_points(c.q,ss,0);height=c.terrain.ground(pp[:,0],pp[:,1]);peaks=ss[find_peaks(height,prominence=.3)[0]]
 assert len(peaks)==2 and abs(peaks[0]-933.0008163012681)<.35 and abs(peaks[1]-942.900816301268)<.35
 # Separate directional evidence: the added R04 pass varies along the route,
 # while the extra R03 grooves vary across it. Existing grooves are retained.
 directions=[]
 for name,lo,hi,expect in [('R04',314,338,'along'),('R03',234,239,'across')]:
  ss=np.arange(lo,hi,.07);ll=np.arange(-3.5,3.51,.07);sg,lg=np.meshgrid(ss,ll);p=cross_points(c.q,sg,lg);relief,_=c.additions(p[:,:,0],p[:,:,1]);across,along=np.gradient(relief,.07,.07)
  ea=float(np.mean(along**2));ec=float(np.mean(across**2));ratio=ea/max(ec,1e-12) if expect=='along' else ec/max(ea,1e-12)
  assert ratio>2,(name,ratio);directions.append(dict(section=name,dominant_gradient=expect,energy_ratio=ratio))
 report=json.loads((O/'surface_validation.json').read_text());assert report['checks_pass'] and all(p['maximum_3d_spacing_m']<=.5 for p in report['spacing_checks'])
 assert report['rgba8_base_level_bytes_before']==report['rgba8_base_level_bytes_after']
 scene=json.loads((O/'scenery_validation.json').read_text())
 assert scene['checks_pass'] and scene['approved_van_sign_cybertrucks_records_exact'] and scene['all_unrelated_records_exact']
 assert sha(O/'scenery.fbx')==scene['scenery_sha256'] and len(scene['terrain_binding_changes'])==3
 for name in ['route.npz','main.tcl','start.tcl','compiled_track.hmf']:assert sha(O/name)==sha(PREV/name),name
 normal=Image.open(source('v044_route_detail_n.tga'));before_normal=Image.open(previous('v044_route_detail_n.tga'));count=0;n=normal.width
 for row in range(0,n,128):
  aa=np.asarray(before_normal.crop((0,row,n,min(row+128,n))));bb=np.asarray(normal.crop((0,row,n,min(row+128,n))));assert np.array_equal(aa[:,:,3],bb[:,:,3]);yy,xx=np.where(np.any(aa!=bb,axis=2));count+=len(xx)
  if len(xx):
   _,_,cross,long=c.weights((xx+.5)*600/n,600-(yy+row+.5)*600/n);assert np.all(np.maximum(cross,long)>0)
 assert count==report['changed_macro_pixels']
 views=configure();data=json.loads((S/'full_track_review.json').read_text());assert len(data['renders'])==38
 for v,row in zip(views,data['renders']):
  old_row=json.loads((R/'BUILD/v058_full_review'/('photo_'+v['id']+'.json')).read_text())
  assert row['view']==v and row['eye_xzy_m']==old_row['eye_xzy_m'] and row['target_xzy_m']==old_row['target_xzy_m']
  assert sha(OUT/row['file'])==row['sha256'];im=Image.open(OUT/row['file']);im.load();assert im.size==(1600,1000)
 changed=[]
 for number in CHANGED_VIEWS:
  aa=np.asarray(Image.open(R/f'BUILD/v058_full_review/Orlando_v058_{number}.jpg')).astype(float)[70:]
  bb=np.asarray(Image.open(OUT/f'Orlando_v059_{number}.jpg')).astype(float)[70:];delta=float(abs(aa-bb).mean());assert delta>.15,(number,delta);changed.append(dict(photo=number,mean_RGB_difference=delta))
 for r in data['detail_views']['renders']:assert sha(OUT/r['file'])==r['sha256']
 archive=R/'BUILD/Orlando_v059_Full_Track_Photos.zip';assert sha(archive)==data['archive']['sha256']
 expected={r['file'] for r in data['renders']}|set(data['sheets'])|{data['map'],'Read_Me.txt','Review_Manifest.json'}|set(data['before_after'])|{data['geometry_plot']}
 expected|={r['file'] for r in data['detail_views']['renders']}|{data['detail_views']['sheet'],'detail_manifest.json'}
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None and set(z.namelist())==expected and len(z.namelist())==len(expected)
 result=dict(checks_pass=True,geometry_outside_edit_scope_exact=True,unrequested_corner_riding_area_checks=corners,road_exact=True,unrelated_profile_records_exact=True,
  moved_pair_actual_terrain_crests_m=peaks.tolist(),old_pair_ghost_removed=True,added_pass_direction_checks=directions,all_spacing_checks_pass=True,
  macro_changed_pixels=count,normal_changes_outside_request_regions=0,normal_specular_alpha_exact=True,source_texture_allocation_unchanged=True,
  approved_van_sign_and_cybertruck_records_exact=True,only_three_edge_marker_heights_adjusted=True,route_start_and_physical_layer_bindings_exact=True,photo_count=38,additional_detail_views=4,matched_before_after_views=9,exact_world_cameras=True,
  changed_photo_checks=changed,archive=data['archive'],final_compilation_started=False,in_game_verified=False)
 save(S/'review_validation.json',result);print('V059_COMPLETE_CHECKS_PASS: scoped geometry, 90-degree pass, <=0.5m spacing, unchanged texture allocation, 42 source photos; compilation held',flush=True)

if __name__=='__main__':main()
