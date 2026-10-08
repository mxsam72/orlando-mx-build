"""Move only start-clearance fixtures and corner boundary markers."""
from pathlib import Path
import json,numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v027_scenery import parse,encode,geometry_records,vertices,child,values,fingerprint
from rebind_scenery import encoded_array
from v033_common import atomic,save,sha
R=Path(__file__).resolve().parents[1];BASE=R/'V033_OUTPUT';O=R/'V034_OUTPUT'
def main():
 before=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(before);assert encode(nodes,tail)==before
 records=geometry_records(nodes);objects=next(n for n in nodes if n['name']==b'Objects');original={values(n)[0]:fingerprint(n) for n in objects['children']};conn=fingerprint(next(n for n in nodes if n['name']==b'Connections'))
 old=np.load(BASE/'route.npz')['q'];r=np.load(O/'route.npz');q=r['q'];mapping=r['old_to_new_v033_station'];tree=cKDTree(old[:,:2]);cfg=json.loads((R/'V034_SOURCE/holeshot_spec.json').read_text());a,b=cfg['main_connector_old_station_bounds_m'];oldH=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18;newH=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
 ground=lambda H,xz:float(map_coordinates(H,[[(600-xz[1])/600*2048],[xz[0]/600*2048]],order=1,mode='nearest')[0])
 explicit={'v028_practice_wood_left_timber':12,'v028_practice_barrier_left_alloy':20,'v028_practice_barrier_right_alloy':20,'tree_287':12,'tree_368':14}
 for name in records:
  if name.startswith('v028_practice_oak_03_'):explicit[name]=22
 changedids=set();changes=[];probes=[]
 for name,(g,mid) in records.items():
  v=vertices(g);low=v[v[:,1]<v[:,1].min()+.3];anchor=low[:,[0,2]].mean(0);newanchor=anchor.copy();reason=None
  if name.startswith('SOFTCPLAS_marker_'):
   dd,i=tree.query(anchor);st=old[i,3]
   if a<st<b:
    ns=np.interp(st,old[:,3],mapping);p=np.array([np.interp(ns,q[:,3],q[:,k]) for k in [0,1,2]]);dv=anchor-old[i,:2];lat=float(dv@np.array([-np.sin(old[i,2]),np.cos(old[i,2])]));newanchor=p[:2]+lat*np.array([-np.sin(p[2]),np.cos(p[2])]);reason='Follow shifted T05 boundary at the same lateral offset'
  if name in explicit:newanchor=anchor+[explicit[name],0];reason='Clear widened holeshot lane and relocated practice gate'
  dy=ground(newH,newanchor)-ground(oldH,anchor)
  # Ground all remaining boundary markers affected by the old-corner retirement.
  if reason is None and name.startswith('SOFTCPLAS_marker_') and abs(dy)>.001:reason='Reground marker at unchanged anchor'
  if reason:
   delta=np.array([newanchor[0]-anchor[0],dy,newanchor[1]-anchor[1]]);vv=v+delta;child(g,b'Vertices')['props']=encoded_array(vv*[100,100,-100]);changedids.add(values(g)[0]);changes.append(dict(model=name,reason=reason,old_anchor_xz_m=anchor.tolist(),new_anchor_xz_m=newanchor.tolist(),translation_xyz_m=delta.tolist(),vertices=len(v)))
   probes.extend(vv[[0,len(vv)//2,-1]].tolist())
 output=encode(nodes,tail);atomic(O/'scenery.fbx',output);check,_=parse(output);after={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']}
 assert {k:v for k,v in after.items() if k not in changedids}=={k:v for k,v in original.items() if k not in changedids};assert fingerprint(next(n for n in check if n['name']==b'Connections'))==conn
 rec=geometry_records(check);mainprobes=[vertices(g)[0].tolist() for name,(g,mid) in rec.items() if name.startswith('SOFTCPLAS_marker_')][:40];save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=mainprobes));save(O/'holeshot_native_probes.json',dict(expected_xyz_metres=probes))
 save(O/'holeshot_scenery_validation.json',dict(checks_pass=True,source_sha256=sha(BASE/'scenery.fbx'),output_sha256=sha(O/'scenery.fbx'),modified_geometry_records=len(changes),all_other_object_records_byte_exact=True,all_connections_byte_exact=True,memorial_entry_and_Qwikchute_signs_byte_exact=True,changes=changes))
 print('Scenery clearance:',len(changes),'local markers/fixtures moved; all other records exact',flush=True)
if __name__=='__main__':main()
