"""Ground-bind and clear only scenery touched by the new A/B/C corridors."""
import re
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from v054_geometry import R,BASE,PREV,O,Layout,ground,read,sha,save,projection,unit
from v027_scenery import parse,encode,values,vertices,child,geometry_records,fingerprint
from rebind_scenery import encoded_array,array

def main():
 layout=Layout();oldh=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18;newh=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
 before=(PREV/'scenery.fbx').read_bytes();nodes,tail=parse(before);assert encode(nodes,tail)==before
 objects=next(n for n in nodes if n['name']==b'Objects');original={values(n)[0]:fingerprint(n) for n in objects['children']};links=fingerprint(next(n for n in nodes if n['name']==b'Connections'))
 rec=geometry_records(nodes);groups={}
 for name,(g,mid) in rec.items():
  match=re.match(r'(v047_tree_[AB]_\d+)_',name);key=match[1] if match else name;groups.setdefault(key,[]).append((name,g,mid))
 changes=[];changed=set();probes=[];bounds=[]
 def near(p):return ((p[:,0]>185)&(p[:,0]<445)&(p[:,1]>225)&(p[:,1]<392))|((p[:,0]>185)&(p[:,0]<272)&(p[:,1]>184)&(p[:,1]<333))
 def clearance(v):
  xz=v[:,[0,2]];d,i=layout.newtree.query(xz,workers=2);labels=layout.old_s[i];width=layout.width[i]
  md=layout.active(labels)&(d<width/2+1.2)
  bd,bi,bs,bl=projection(layout.start,xz);bw=np.interp(bs,*np.asarray(layout.knots).T)
  start=(bs>56)&(bs<layout.start[-1,3]+1)&(bd<bw/2+1.2)
  low=v[:,1]-ground(newh,xz)<2.7
  return near(xz)&low&(md|start)
 for key,parts in groups.items():
  verts=[vertices(g) for _,g,_ in parts];vv=np.concatenate(verts);low=vv[vv[:,1]<vv[:,1].min()+.17];anchor=low[:,[0,2]].mean(0)
  if not near(vv[:,[0,2]]).any():continue
  foliage=key.startswith(('v047_tree_','tree_','scrub_','SKIDS_v052_grass'))
  marker=key.startswith(('SOFTCPLAS_marker_','SOFTPLAS_marker_'))
  fence=any(t in key.lower() for t in ['start_fence','start_barrier','holeshot_fence','holeshot_barrier'])
  delta=np.zeros(3);yaw=0.;reason=[]
  if marker:
   target=layout.forward(anchor[None])[0];delta[[0,2]]=target-anchor
   if np.linalg.norm(delta[[0,2]])>.001:reason.append('Follow updated main corridor')
  if fence:
   d,i,s,lat=projection(layout.oldstart,anchor[None])
   if 57<float(s[0])<100 and d[0]<32:
    ns=57+(float(s[0])-57)/(layout.oldstart[-1,3]-57)*(layout.start[-1,3]-57);p=np.array([np.interp(ns,layout.start[:,3],layout.start[:,k]) for k in range(3)])
    target=p[:2]+np.array([-np.sin(p[2]),np.cos(p[2])])*float(lat[0]);delta[[0,2]]=target-anchor;yaw=float(p[2]-layout.oldstart[i[0],2]);reason.append('Follow changed start-side barrier')
  trial=vv.copy();trial[:,[0,2]]+=delta[[0,2]]
  if foliage and clearance(trial).any():
   # Preserve complete grass batches and tree prototypes: translate them as
   # rigid groups, retaining UVs, vertex count, density and matte materials.
   selected=None
   for radius in [3,6,10,15,22,30,40]:
    for angle in np.linspace(0,2*np.pi,24,endpoint=False):
     shift=np.array([np.cos(angle),np.sin(angle)])*radius;candidate=vv.copy();candidate[:,[0,2]]+=shift
     candidate[:,1]+=ground(newh,(anchor+shift)[None])[0]-ground(oldh,anchor[None])[0]
     if not clearance(candidate).any():selected=shift;break
    if selected is not None:break
   assert selected is not None,('Cannot clear vegetation from new track',key)
   delta[[0,2]]=selected;reason.append('Clear vegetation from new riding corridor')
  if foliage or marker or fence:
   dy=float(ground(newh,(anchor+delta[[0,2]])[None])[0]-ground(oldh,anchor[None])[0]);delta[1]=dy
   if abs(dy)>.005:reason.append('Bind roots/base to local edited terrain')
  grass=key.startswith('SKIDS_v052_grass');grass_adjustment=None
  if grass:
   g=parts[0][1];v=verts[0];idx=array(child(g,b'PolygonVertexIndex')).reshape(-1,3).copy();idx[idx<0]=-idx[idx<0]-1
   row=idx.ravel();col=np.roll(idx,1,axis=1).ravel();graph=coo_matrix((np.ones(len(row),bool),(row,col)),shape=(len(v),len(v))).tocsr();count,labels=connected_components(graph,directed=False)
   grass_adjustment=np.zeros(len(v))
   for component in range(count):
    ids=np.flatnonzero(labels==component);part=v[ids];roots=part[part[:,1]<part[:,1].min()+.03];root=roots[:,[0,2]].mean(0)
    dy=float(ground(newh,(root+delta[[0,2]])[None])[0]-ground(oldh,root[None])[0]);grass_adjustment[ids]=dy
   if np.max(abs(grass_adjustment))>.005 and 'Bind roots/base to local edited terrain' not in reason:reason.append('Bind each disconnected grass blade to edited terrain')
  if not reason or (np.linalg.norm(delta)<.001 and (grass_adjustment is None or np.max(abs(grass_adjustment))<.001)):continue
  if not (foliage or marker or fence):continue
  for (name,g,mid),v in zip(parts,verts):
   new=v.copy()
   if abs(yaw)>1e-8:
    c,s=np.cos(yaw),np.sin(yaw);rot=np.array([[c,0,-s],[0,1,0],[s,0,c]]);new=(new-[anchor[0],0,anchor[1]])@rot.T+[anchor[0],0,anchor[1]]
    layer=child(g,b'LayerElementNormal')
    if layer is not None:
     normal=array(child(layer,b'Normals')).reshape(-1,3)*[1,1,-1];normal=normal@rot.T;child(layer,b'Normals')['props']=encoded_array(normal*[1,1,-1])
   if grass:
    new[:,[0,2]]+=delta[[0,2]];new[:,1]+=grass_adjustment
   else:new+=delta
   child(g,b'Vertices')['props']=encoded_array(new*[100,100,-100]);changed.add(values(g)[0]);probes.extend(dict(geometry=name,expected_xyz_m=new[j].tolist()) for j in sorted(set([0,len(new)//2,len(new)-1])))
  changes.append(dict(group=key,objects=[p[0] for p in parts],translation_xyz_m=delta.tolist(),rotation_y_rad=yaw,reason=reason))
  if grass:changes[-1]['per_blade_vertical_shift_m']=[float(grass_adjustment.min()),float(grass_adjustment.max())];changes[-1]['grass_components_ground_bound']=int(count)
 # Guard every fixed collision object in the new main/start footprints.
 blocks=[]
 for name,(g,mid) in rec.items():
  if name.startswith(('TRK','SKIDS','v047_tree_','tree_','scrub_')):continue
  if not name.startswith(('WLL','SOFT','gate','start_gate')):continue
  if 'marker_' in name:continue
  v=vertices(g)
  if not near(v[:,[0,2]]).any():continue
  bad=clearance(v)
  if bad.any():blocks.append(dict(object=name,unsafe_vertices=int(bad.sum())))
 assert not blocks,('Fixed objects intersect new lanes',blocks)
 after=encode(nodes,tail);(O/'scenery.fbx').write_bytes(after);check,_=parse(after);final={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']}
 assert {k:v for k,v in original.items() if k not in changed}=={k:v for k,v in final.items() if k not in changed}
 assert fingerprint(next(n for n in check if n['name']==b'Connections'))==links
 preserved_roads=[name for name in rec if name.startswith(('TRKASPH','TRKCONC')) or any(t in name.lower() for t in ['practice_barrier','practice_wood','oval_wall','figure8_wall'])]
 updated=geometry_records(check)
 assert all(fingerprint(rec[name][0])==fingerprint(updated[name][0]) for name in preserved_roads),'Existing road-course geometry or barriers moved'
 retained=[]
 for name,(g,mid) in geometry_records(check).items():
  v=vertices(g)
  if values(g)[0] not in changed:retained.extend(dict(geometry=name,expected_xyz_m=v[j].tolist()) for j in sorted(set([0,len(v)//2,len(v)-1])))
 save(O/'scenery_validation.json',dict(checks_pass=True,baseline='v052',baseline_scenery_sha256=sha(PREV/'scenery.fbx'),scenery_sha256=sha(O/'scenery.fbx'),modified_geometry_records=len(changed),changes=changes,unrelated_objects_and_all_material_media_records_exact=True,all_connections_exact=True,vegetation_counts_and_prototypes_preserved=True,grass_blades_individually_ground_bound=True,unchanged_road_course_and_barrier_records=len(preserved_roads),fixed_collision_obstructions=blocks))
 save(O/'native_probes.json',dict(retained_geometry=retained,changed_geometry=probes))
 print('V054_SCENERY_PASSED',len(changed),'changed records; all other records and textures exact.',flush=True)
if __name__=='__main__':main()
