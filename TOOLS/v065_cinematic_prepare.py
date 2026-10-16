"""Prepare the actual v065 terrain and retained FBX for Cycles source renders.

No invented scenery or raster replacement. Native vertices, polygons, UVs and
split normals are copied from the authenticated source. Presentation lighting
is independent of MX Bikes; the deliverables explicitly identify source renders.
"""
from pathlib import Path
import collections,gc,io,json,re
import numpy as np
from PIL import Image
from v027_scenery import parse,values,child,vertices,geometry_records
from rebind_scenery import array
from scene_texture_bindings_v044 import actual_diffuse_bindings
from v032_common import layer_blocks
from v065_start import R,BASE,O,S,source,sha,save,TERRAIN_SHA,SCENERY_SHA

W=R/'BUILD/v065_cinematic';T=W/'textures'
IMAGE_CACHE={}

def image_file(path,kind='color',limit=2048):
 path=Path(path);digest=sha(path);key=(digest,kind,limit)
 if key in IMAGE_CACHE:return IMAGE_CACHE[key]
 name=digest[:20]+'_'+kind+f'_{limit}.png';dest=T/name
 if not dest.exists():
  with Image.open(path) as im:
   if kind=='mask':im=im.getchannel('A')
   elif kind=='normal':im=im.convert('RGB')
   else:im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
   if max(im.size)>limit:
    im.thumbnail((limit,limit),Image.Resampling.LANCZOS if kind=='color' else Image.Resampling.BOX)
   im.save(dest)
 IMAGE_CACHE[key]=dest.as_posix();return dest.as_posix()

def material_layers():
 result=[]
 for index,_,block in layer_blocks((O/'compiled_track.hmf').read_text()):
  if index==0:continue # Fully covered by unmasked layer 1.
  name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1]
  rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
  mask=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
  item=dict(index=index,name=name,color=image_file(source(name)),repetitions=rep)
  if mask:item['mask']=image_file(source(mask[1]),'mask')
  shader=source(name).with_suffix('.shd')
  # An image override can live separately from its unchanged shader.
  try:shader=source(Path(name).stem+'.shd')
  except FileNotFoundError:pass
  if shader.is_file():
   bump=re.search(r'\bbump\s*\{([^}]+)\}',shader.read_text())
   if bump:
    normal=re.search(r'map\s*=\s*(\S+)',bump[1])[1]
    reps=re.search(r'repetitions\s*=\s*([\d.]+)',bump[1])
    nr=float(reps[1]) if reps else rep
    if nr==0:nr=rep
    item.update(normal=image_file(source(normal),'normal',8192 if normal=='v044_route_detail_n.tga' else 2048),normal_repetitions=nr)
  result.append(item)
 return result

def scenery():
 nodes,_=parse((O/'scenery.fbx').read_bytes())
 objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
 links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
 records=geometry_records(nodes);model_ids={mid for _,mid in records.values()}
 model_mats=collections.defaultdict(list);mat_texture={};texture_video={}
 for link in links:
  if link[2] in model_ids and objects.get(link[1],{}).get('name')==b'Material':model_mats[link[2]].append(link[1])
  if objects.get(link[1],{}).get('name')==b'Texture' and objects.get(link[2],{}).get('name')==b'Material' and (len(link)<4 or link[3]==b'DiffuseColor'):mat_texture[link[2]]=link[1]
  if objects.get(link[1],{}).get('name')==b'Video' and objects.get(link[2],{}).get('name')==b'Texture':texture_video[link[2]]=link[1]
 names={b['texture_id']:b['texture'] for b in actual_diffuse_bindings(nodes)['bindings']}
 grouped=collections.defaultdict(lambda:dict(v=[],uv=[],normal=[],length=[],count=0,names=[]));bounds={}
 for i,(name,(g,mid)) in enumerate(records.items()):
  v=vertices(g)[:,[0,2,1]].astype(np.float32);bounds[name]=[v.min(0).tolist(),v.max(0).tolist()]
  pi=array(child(g,b'PolygonVertexIndex')).astype(np.int64);indices=np.where(pi<0,-pi-1,pi)
  ends=np.flatnonzero(pi<0);lengths=np.diff(np.r_[-1,ends]).astype(np.int32)
  pv=v[indices];uv_layer=next((n for n in g['children'] if n['name']==b'LayerElementUV'),None)
  if uv_layer:
   direct=array(child(uv_layer,b'UV')).reshape(-1,2)
   ref=values(child(uv_layer,b'ReferenceInformationType'))[0]
   uv=direct[array(child(uv_layer,b'UVIndex')).astype(int)] if ref==b'IndexToDirect' else direct
   assert len(uv)==len(pi),(name,len(uv),len(pi))
  else:uv=np.zeros((len(pi),2),np.float32)
  nl=next((n for n in g['children'] if n['name']==b'LayerElementNormal'),None)
  if nl:
   nv=array(child(nl,b'Normals')).reshape(-1,3)
   if len(nv)==len(v):nv=nv[indices]
   assert len(nv)==len(pi),(name,'normals')
   nv=nv[:,[0,2,1]]*np.array([1,-1,1])
  else:
   starts=ends-lengths+1
   face_norm=np.cross(pv[starts+1]-pv[starts],pv[starts+2]-pv[starts]);face_norm/=np.maximum(np.linalg.norm(face_norm,axis=1,keepdims=True),1e-8)
   nv=np.repeat(face_norm,lengths,axis=0)
  ml=next((n for n in g['children'] if n['name']==b'LayerElementMaterial'),None)
  mi=array(child(ml,b'Materials')).astype(int) if ml else np.array([0])
  mapping=values(child(ml,b'MappingInformationType'))[0] if ml else b'AllSame'
  slots=mi if mapping==b'ByPolygon' else np.full(len(ends),mi[0],np.int32)
  for slot in np.unique(slots):
   face_use=slots==slot;use=np.repeat(face_use,lengths);mats=model_mats[mid];mat=mats[int(slot)] if mats else None
   group=grouped[mat];group['v'].append(pv[use]);group['uv'].append(uv[use].astype(np.float32));group['normal'].append(nv[use].astype(np.float32))
   group['length'].append(lengths[face_use]);group['count']+=int(use.sum());group['names'].append(name)
  if i%250==0:print('SCENE_MODELS',i,'/',len(records),flush=True)
 materials=[]
 for i,(mid,group) in enumerate(grouped.items()):
  node=objects[mid] if mid else None;name=values(node)[1].split(b'\0')[0].decode() if node else 'unassigned'
  p=next((n for n in node['children'] if n['name']==b'Properties70'),None) if node else None
  color=next((values(q)[4:7] for q in p['children'] if values(q)[0]==b'DiffuseColor'),[.65,.65,.65]) if p else [.65,.65,.65]
  item=dict(id=i,name=name,color=list(color),models=group['names'],file=f'scene_{i:03}.npz')
  tid=mat_texture.get(mid)
  if tid in names:
   filename=names[tid]
   try:path=source(filename)
   except FileNotFoundError:
    content=values(child(objects[texture_video[tid]],b'Content'))[0]
    path=W/('embedded_'+filename);path.write_bytes(content)
   item.update(texture=image_file(path),texture_name=filename)
  np.savez(W/item['file'],v=np.concatenate(group['v']),uv=np.concatenate(group['uv']),normal=np.concatenate(group['normal']),length=np.concatenate(group['length']))
  materials.append(item)
  group.clear()
 save(W/'scene_materials.json',materials);save(W/'scene_bounds.json',bounds)
 print('REAL_SCENE_READY',len(records),'models',len(materials),'material groups',flush=True)
 del nodes,objects,links,records,grouped;gc.collect()
 return dict(models=len(bounds),materials=len(materials))

def terrain():
 h=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
 # Keep every native sample around the entire course/facility and speedway.
 # Outer terrain uses a matching 4-sample grid; no covered coplanar surfaces.
 def grid(c0,c1,r0,r1,step,cut=False):
  cs=np.arange(c0,c1+1,step);rs=np.arange(r0,r1+1,step);xx,zz=np.meshgrid(cs/2048*600,600-rs/2048*600)
  v=np.stack([xx,zz,h[np.ix_(rs,cs)]],axis=-1).reshape(-1,3).astype(np.float32)
  uv=np.c_[v[:,0]/600,v[:,1]/600];w=len(cs)
  a=(np.arange(len(rs)-1)[:,None]*w+np.arange(w-1)[None,:]).ravel()
  if cut:
   center=v[a,:2]+np.array([600/2048*step/2,-600/2048*step/2])
   use=~((center[:,0]>624/2048*600)&(center[:,0]<600)&(center[:,1]>(600-1560/2048*600))&(center[:,1]<(600-508/2048*600)))
   a=a[use]
  faces=np.stack([a,a+w,a+w+1,a+1],axis=1).astype(np.int32)
  return v,uv,faces
 for name,args in [('course',(624,2048,508,1560,1,False)),('outer',(0,2048,0,2048,4,True))]:
  v,uv,faces=grid(*args);np.savez(W/('terrain_'+name+'.npz'),v=v,uv=uv,faces=faces)
  print('TERRAIN_GRID',name,len(v),'vertices',len(faces),'quads',flush=True)

def main():
 W.mkdir(parents=True,exist_ok=True);T.mkdir(exist_ok=True)
 assert sha(O/'terrain.raw')==TERRAIN_SHA and sha(O/'scenery.fbx')==SCENERY_SHA
 surface=json.loads((O/'surface_validation.json').read_text());assert surface['checks_pass']
 save(W/'terrain_layers.json',material_layers());scene=scenery();terrain()
 save(W/'preparation.json',dict(source_render=True,in_game_capture=False,source_version='v065',terrain_sha256=TERRAIN_SHA,
  scenery_sha256=SCENERY_SHA,material_validation_sha256=sha(O/'surface_validation.json'),**scene))
 print('V065_CINEMATIC_SOURCE_PREPARED',flush=True)
if __name__=='__main__':main()
