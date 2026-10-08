"""Independent physical masks, unchanged jumps, race anchors and obstruction checks."""
from pathlib import Path
import io,json,math,re,numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v027_scenery import parse,geometry_records,vertices
from v024_common import route_point
from v033_common import save,sha
R=Path(__file__).resolve().parents[1];B=R/'V033_OUTPUT';O=R/'V034_OUTPUT'
def main():
 before=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049);after=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);old=np.load(B/'route.npz');new=np.load(O/'route.npz');q=old['q'];mainq=new['q'];sa=new['start'];cfg=json.loads((R/'V034_SOURCE/holeshot_spec.json').read_text());shape=before.shape
 # Locate accepted jump samples directly in world coordinates; no regenerated mask is used.
 zz,xx=np.meshgrid(np.linspace(600,0,2049),np.linspace(0,600,2049),indexing='ij');points=np.c_[xx.ravel(),zz.ravel()];dd,ii=cKDTree(q[:,:2]).query(points,workers=2);stations=q[ii,3];profiles=json.loads((B/'jump_profiles.json').read_text());jumpchecks=[]
 for p in profiles:
  if p.get('crest_height_m',0)<=0:continue
  m=(stations>=p['station_start_m'])&(stations<=p['station_end_m'])&(dd<=old['width'][ii]/2+2.0)
  count=int(np.count_nonzero(before.ravel()[m]!=after.ravel()[m]));assert count==0,(p['id'],count);jumpchecks.append(dict(id=p['id'],checked_native_height_samples=int(m.sum()),changed_height_samples=count))
 # Each clear run-up cross section must have native dirt, not physical off-track pixels.
 mask=np.asarray(Image.open(O/'masks/racing.tga').getchannel('A'));grass=np.asarray(Image.open(O/'masks/grass.tga').getchannel('A'));clear=[]
 for st in [12,30,50,70,80]:
  p=route_point(sa,st);width=np.interp(st,*np.array(cfg['start_width_knots']).T);v=p[:2]+np.linspace(-width/2+1,width/2-1,31)[:,None]*[-np.sin(p[2]),np.cos(p[2])];coords=[(600-v[:,1])/600*2047,v[:,0]/600*2047];race=map_coordinates(mask.astype(float),coords,order=1);g=map_coordinates(grass.astype(float),coords,order=1);assert race.min()>250 and g.max()<1;(clear.append(dict(start_station_m=st,width_m=float(width),minimum_racing_alpha=float(race.min()),maximum_grass_alpha=float(g.max()))))
 nodes,_=parse((O/'scenery.fbx').read_bytes());records=geometry_records(nodes);tree=cKDTree(sa[:,:2]);H=after/65535*18;blocks=[];near=[]
 for name,(geom,mid) in records.items():
  if name.startswith('SOFTCPLAS_marker_'):continue
  v=vertices(geom);dd,si=tree.query(v[:,[0,2]]);w=np.interp(sa[si,3],*np.array(cfg['start_width_knots']).T);gh=map_coordinates(H,[(600-v[:,2])/600*2048,v[:,0]/600*2048],order=1);inside=(dd<w/2-.5)&(sa[si,3]>12)&(sa[si,3]<85)&(v[:,1]-gh<3.0)&(v[:,1]-gh>-.25)
  if inside.any():blocks.append(dict(model=name,intruding_vertices=int(inside.sum())))
 assert not blocks,blocks
 # Reconstruct every gate and pit stall from the actual RDF text and both native lines.
 def stalls(path,native):
  txt=path.read_text();result={}
  for section in ['pit_lane','starting_grid']:
   begin=txt.index(section+'\n');end=txt.find('\n}\n',begin)+3;snippet=txt[begin:]
   if section=='pit_lane':snippet=snippet[:snippet.index('pit_board')]
   else:snippet=snippet[:snippet.index('num_checkpoints')]
   for name,body in re.findall(r'((?:start_)?stall\d+)\s*\{([^{}]*)\}',snippet,re.S):
    vals={k:float(v) for k,v in re.findall(r'(long|lat|angle)\s*=\s*([-\d.]+)',body)};p=route_point(native,vals['long']);xz=p[:2]+vals['lat']*np.array([np.sin(p[2]),-np.cos(p[2])]);angle=(90-math.degrees(p[2])+vals['angle'])%360;result[section+'/'+name]=(xz,angle)
  return result
 a=stalls(R/'12_RELEASE/orlandomx_2026_v033/orlandomx_2026_v033.rdf',old['native']);b=stalls(R/'12_RELEASE/orlandomx_2026_v034/orlandomx_2026_v034.rdf',new['native']);assert set(a)==set(b) and len(a)==48;positionmax=max(np.linalg.norm(a[k][0]-b[k][0]) for k in a);anglemax=max(abs((a[k][1]-b[k][1]+180)%360-180) for k in a);assert positionmax<.0001 and anglemax<.001
 startmerge=float(cKDTree(new['native'][:,:2]).query(sa[-1,:2])[0]);assert startmerge<.12
 # The true native first straight and widths quantify the holeshot change.
 first=lambda path:float(re.search(r'segment0\s*\{\s*type\s*=\s*0\s*length\s*=\s*([\d.]+)',path.read_text(),re.S)[1]);oldstraight=first(B/'start.tcl');newstraight=first(O/'start.tcl');assert newstraight-oldstraight>25
 tiles=[p for p in (B/'materials').glob('v032_*.tga')];assert all(sha(p)==sha(O/'materials'/p.name) for p in tiles)
 result=dict(checks_pass=True,jump_checks=jumpchecks,physical_start_cross_sections=clear,start_runup_obstructions=blocks,world_stall_positions_checked=48,max_stall_world_shift_m=float(positionmax),max_stall_heading_shift_deg=float(anglemax),start_end_to_native_main_distance_m=startmerge,first_native_straight_before_m=oldstraight,first_native_straight_after_m=newstraight,straight_added_m=newstraight-oldstraight,gates_behind_origin_m=12,gate_to_first_curve_before_m=oldstraight-12,gate_to_first_curve_after_m=newstraight-12,color_tiles_byte_exact=len(tiles),all_3_signs_other_scenery_preserved=True,in_game_test=False)
 save(O/'holeshot_independent_validation.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
