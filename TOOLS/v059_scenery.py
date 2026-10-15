"""Seat the three affected edge markers on the edited terrain; retain every other record."""
import gc,json,os
import numpy as np
from v059_geometry import R,PREV,O,S,sha,save
from v054_previews import Terrain
from v027_scenery import parse,geometry_records,vertices,child,values,fingerprint
from v056_geometry import encode
from rebind_scenery import encoded_array

NAMES={'SOFTCPLAS_marker_18','SOFTCPLAS_marker_56','SOFTCPLAS_marker_79'}

def main():
 src=PREV/'scenery.fbx';pin=sha(src);assert pin=='59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604'
 data=src.read_bytes();nodes,tail=parse(data);del data
 objects=next(n for n in nodes if n['name']==b'Objects');original={values(n)[0]:fingerprint(n) for n in objects['children']};metadata={n['name']:fingerprint(n) for n in nodes if n['name']!=b'Objects'}
 old=Terrain(PREV/'terrain.raw');new=Terrain(O/'terrain.raw');records=geometry_records(nodes);changes=[];ids=set();shifts={}
 for name in sorted(NAMES):
  g,_=records[name];v=vertices(g);root=v[v[:,1]<v[:,1].min()+.17][:,[0,2]].mean(0);delta=float(new.ground(root[0:1],root[1:2])[0]-old.ground(root[0:1],root[1:2])[0]);assert .01<abs(delta)<.20
  moved=v.copy();moved[:,1]+=delta;assert np.array_equal(moved[:,[0,2]],v[:,[0,2]])
  child(g,b'Vertices')['props']=encoded_array(moved*[100,100,-100]);ids.add(values(g)[0]);shifts[name]=delta
  clearance_before=float(v[:,1].min()-old.ground(root[0:1],root[1:2])[0]);clearance_after=float(moved[:,1].min()-new.ground(root[0:1],root[1:2])[0]);assert abs(clearance_before-clearance_after)<1e-7
  changes.append(dict(object=name,vertical_shift_m=delta,anchor_xz_m=root.tolist(),original_ground_clearance_retained=True))
 result=encode(nodes,tail);temp=O/'scenery_rebinding.fbx'
 with temp.open('wb') as f:f.write(result);f.flush();os.fsync(f.fileno())
 check,_=parse(result);actual={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']}
 assert {k:v for k,v in original.items() if k not in ids}=={k:v for k,v in actual.items() if k not in ids}
 assert metadata=={n['name']:fingerprint(n) for n in check if n['name']!=b'Objects'}
 # Atomic replacement breaks the read-only shared input link; v058 stays exact.
 temp.replace(O/'scenery.fbx');os.utime(O/'scenery.fbx',None);assert sha(src)==pin
 probes=json.loads((PREV/'native_probes.json').read_text())
 for items in probes.values():
  for item in items:
   if item['geometry'] in shifts:item['expected_xyz_m'][1]+=shifts[item['geometry']]
 save(O/'native_probes.json',probes)
 base=json.loads((PREV/'scenery_validation.json').read_text());base.update(checks_pass=True,scenery_sha256=sha(O/'scenery.fbx'),baseline_sha256=pin,scenery_unchanged=False,
  approved_van_sign_cybertrucks_records_exact=True,approved_v057_preserved=False,all_physical_scene_geometry_exact=False,all_road_vehicle_and_unrelated_physics_exact=True,
  all_unrelated_records_exact=True,all_connections_materials_textures_exact=True,
  terrain_binding_changes=changes,requires_new_native_scenery_compile=True,reuse_saved_v057_edf=False,final_compilation_started=False)
 save(O/'scenery_validation.json',base);save(S/'scenery_grounding_validation.json',base)
 print('V059_EDGE_MARKERS_GROUNDED: 3 vertical-only corrections; all other records exact; native compilation held',flush=True)

if __name__=='__main__':main()
