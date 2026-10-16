"""Cycles renders of genuine Orlando MX source, with cinematic presentation.

Run in the isolated Python 3.11 environment with bpy 4.5.3. The source prepare
step uses the main authoring Python. Render lighting is not an in-game preview.
"""
from pathlib import Path
import argparse,gc,json,math,time
import numpy as np
import bpy
from mathutils import Vector

R=Path(__file__).resolve().parents[1];W=R/'BUILD/v065_cinematic'
OUT=R/'DOCUMENTATION/v065_cinematic';B=R/'V065_OUTPUT'
IMAGE_CACHE={}

def log(*x):print(*x,flush=True)
def read(p):return json.loads(Path(p).read_text())
def image(path,noncolor=False):
 key=(path,noncolor)
 if key not in IMAGE_CACHE:
  im=bpy.data.images.load(path,check_existing=False)
  if noncolor:im.colorspace_settings.name='Non-Color'
  IMAGE_CACHE[key]=im
 return IMAGE_CACHE[key]
def texture(nodes,links,path,uv,repetitions=1,noncolor=False):
 node=nodes.new('ShaderNodeTexImage');node.image=image(path,noncolor);node.interpolation='Linear';node.extension='REPEAT'
 if repetitions!=1:
  scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=repetitions
  links.new(uv,scale.inputs[0]);uv=scale.outputs[0]
 links.new(uv,node.inputs['Vector']);return node
def mix(nodes,links,a,b,factor):
 m=nodes.new('ShaderNodeMixRGB');m.blend_type='MIX'
 if isinstance(a,(tuple,list)):m.inputs[1].default_value=(*a,1)
 else:links.new(a,m.inputs[1])
 if isinstance(b,(tuple,list)):m.inputs[2].default_value=(*b,1)
 else:links.new(b,m.inputs[2])
 if isinstance(factor,(int,float)):m.inputs[0].default_value=factor
 else:links.new(factor,m.inputs[0])
 return m.outputs[0]

def terrain_material():
 mat=bpy.data.materials.new('Actual accepted B/C terrain, with corrected C start');mat.use_nodes=True
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
 uv=nodes.new('ShaderNodeTexCoord').outputs['UV'];color=(.2,.17,.12);normal=(.5,.5,1)
 for row in read(W/'terrain_layers.json'):
  tex=texture(nodes,links,row['color'],uv,row['repetitions'])
  factor=texture(nodes,links,row['mask'],uv,1,True).outputs['Color'] if row.get('mask') else 1
  nn=texture(nodes,links,row['normal'],uv,row['normal_repetitions'],True).outputs['Color'] if row.get('normal') else (.5,.5,1)
  color=mix(nodes,links,color,tex.outputs['Color'],factor);normal=mix(nodes,links,normal,nn,factor)
 p=nodes.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=.94;p.inputs['Specular IOR Level'].default_value=.12
 links.new(color,p.inputs['Base Color'])
 n=nodes.new('ShaderNodeNormalMap');n.space='TANGENT';n.inputs['Strength'].default_value=1
 links.new(normal,n.inputs['Color']);links.new(n.outputs['Normal'],p.inputs['Normal'])
 out=nodes.new('ShaderNodeOutputMaterial');links.new(p.outputs['BSDF'],out.inputs['Surface'])
 return mat

def scene_material(row):
 mat=bpy.data.materials.new(row['name']);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
 p=nodes.get('Principled BSDF');name=(row['name']+' '+row.get('texture_name','')).lower()
 p.inputs['Base Color'].default_value=(*row['color'][:3],1);p.inputs['Roughness'].default_value=.78;p.inputs['Specular IOR Level'].default_value=.25
 if any(x in name for x in ['steel','alloy','chrome','rim','cyber_silver']):
  p.inputs['Metallic'].default_value=.82;p.inputs['Roughness'].default_value=.29
 if any(x in name for x in ['paint','cyber_black']):
  p.inputs['Roughness'].default_value=.31;p.inputs['Coat Weight'].default_value=.32
 if 'glass' in name:
  p.inputs['Metallic'].default_value=.27;p.inputs['Roughness'].default_value=.13;p.inputs['Coat Weight'].default_value=.4
 if any(x in name for x in ['rubber','tire','tread']):p.inputs['Roughness'].default_value=.94
 if any(x in name for x in ['leaf','leaves','foliage','grass']):
  p.inputs['Roughness'].default_value=.95;p.inputs['Specular IOR Level'].default_value=.1
 if row.get('texture'):
  uv=nodes.new('ShaderNodeTexCoord').outputs['UV'];tx=texture(nodes,links,row['texture'],uv)
  links.new(tx.outputs['Color'],p.inputs['Base Color'])
  if tx.image.channels==4:
   links.new(tx.outputs['Alpha'],p.inputs['Alpha'])
 # These source boards contain front and rear coplanar artwork. Render the
 # facing artwork only, as the native/previous review renderer does.
 if any(x in name for x in ['entry_sign','v032_memorial','v033_qwikchute_logo']):
  geom=nodes.new('ShaderNodeNewGeometry');subtract=nodes.new('ShaderNodeMath');subtract.operation='SUBTRACT';subtract.inputs[0].default_value=1
  links.new(geom.outputs['Backfacing'],subtract.inputs[1]);links.new(subtract.outputs[0],p.inputs['Alpha'])
 return mat

def mesh(name,v,uv,faces=None,length=None,normal=None,material=None):
 m=bpy.data.meshes.new(name)
 m.vertices.add(len(v));m.vertices.foreach_set('co',np.asarray(v,np.float32).ravel())
 if faces is not None:
  loops=np.asarray(faces,np.int32).ravel();sizes=np.full(len(faces),faces.shape[1],np.int32)
 else:loops=np.arange(len(v),dtype=np.int32);sizes=np.asarray(length,np.int32)
 starts=np.r_[0,np.cumsum(sizes[:-1],dtype=np.int32)].astype(np.int32)
 m.loops.add(len(loops));m.loops.foreach_set('vertex_index',loops)
 m.polygons.add(len(sizes));m.polygons.foreach_set('loop_start',starts);m.polygons.foreach_set('loop_total',sizes)
 u=m.uv_layers.new(name='UVMap');u.data.foreach_set('uv',np.asarray(uv[loops],np.float32).ravel())
 m.polygons.foreach_set('use_smooth',np.ones(len(sizes),bool));m.update()
 if normal is not None:m.normals_split_custom_set(np.asarray(normal,np.float32))
 obj=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(obj)
 if material:m.materials.append(material)
 return obj

def load_scene():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 tm=terrain_material()
 for name in ['course','outer']:
  with np.load(W/('terrain_'+name+'.npz')) as d:mesh('Native terrain '+name,d['v'],d['uv'],faces=d['faces'],material=tm)
  gc.collect()
 for row in read(W/'scene_materials.json'):
  with np.load(W/row['file']) as d:mesh(row['name'],d['v'],d['uv'],length=d['length'],normal=d['normal'],material=scene_material(row))
  if row['id']%12==0:log('CYCLES_SCENE_MATERIAL',row['id'],row['name'])
  gc.collect()
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
 scene.render.threads_mode='FIXED';scene.render.threads=8
 scene.cycles.use_adaptive_sampling=True;scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
 scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transmission_bounces=2;scene.cycles.transparent_max_bounces=12
 scene.render.use_persistent_data=True
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
 world=bpy.data.worlds.new('Late afternoon Florida daylight');world.use_nodes=True;scene.world=world
 nodes=world.node_tree.nodes;links=world.node_tree.links;nodes.clear();sky=nodes.new('ShaderNodeTexSky');sky.sky_type='NISHITA'
 az=math.radians(220);el=math.radians(25)
 sky.sun_elevation=el;sky.sun_rotation=az;sky.sun_disc=False;sky.air_density=1;sky.dust_density=.35;sky.ozone_density=1
 bg=nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.35;links.new(sky.outputs['Color'],bg.inputs['Color'])
 output=nodes.new('ShaderNodeOutputWorld');links.new(bg.outputs[0],output.inputs[0])
 sun=bpy.data.lights.new('Presentation sun','SUN');sun.energy=3;sun.angle=math.radians(2);sun.color=(1,.95,.86)
 ob=bpy.data.objects.new('Presentation sun',sun);scene.collection.objects.link(ob)
 direction=Vector((math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)))
 ob.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
 camera=bpy.data.cameras.new('Cinematic camera');cam=bpy.data.objects.new('Cinematic camera',camera);scene.collection.objects.link(cam);scene.camera=cam
 camera.clip_start=.08;camera.clip_end=2000;camera.sensor_width=36;camera.dof.aperture_fstop=9;camera.dof.aperture_blades=8
 scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
 scene.render.resolution_percentage=100
 return scene

def cameras():
 raw=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18;route=np.load(B/'route.npz')['q']
 def ground(x,z):
  c=np.clip(x/600*2048,0,2047.999);r=np.clip((600-z)/600*2048,0,2047.999);i,j=int(r),int(c);fr,fc=r-i,c-j
  return float((1-fr)*((1-fc)*raw[i,j]+fc*raw[i,j+1])+fr*((1-fc)*raw[i+1,j]+fc*raw[i+1,j+1]))
 def loc(x,z,h):return [float(x),float(z),ground(x,z)+h]
 def at(s,l,h):
  x,z,t=[np.interp(s,route[:,3],route[:,i]) for i in [0,1,2]]
  return loc(x-math.sin(t)*l,z+math.cos(t)*l,h)
 return [
  dict(name='01_orlando_hero',eye=loc(460,135,112),target=loc(315,302,2),lens=32),
  dict(name='02_flowing_corner',eye=at(72,-13,5),target=at(103,0,.55),lens=34),
  dict(name='03_tabletop',eye=at(780,-6,2.4),target=at(816,0,.7),lens=33),
  dict(name='04_rhythm_section',eye=at(1373,-27,12),target=at(1397,0,.65),lens=35),
  dict(name='05_speedway_double',eye=loc(597,224,59),target=[529,331,5],lens=29),
  dict(name='06_start_straight',eye=loc(439,144,9),target=loc(411,209,.8),lens=33),
  dict(name='07_c_dirt_start_detail',eye=loc(418,177,1.55),target=loc(413,216,.65),lens=29),
  dict(name='08_express_and_sign',eye=loc(352,143,2.8),target=loc(343,152,1.1),lens=36),
 ]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--draft',action='store_true');ap.add_argument('--shots',default='all');args=ap.parse_args()
 OUT.mkdir(parents=True,exist_ok=True);scene=load_scene();cams=cameras()
 if args.shots!='all':cams=[c for c in cams if c['name'].split('_')[0] in args.shots.split(',')]
 folder=OUT/'drafts' if args.draft else OUT;folder.mkdir(exist_ok=True)
 scene.render.resolution_x=1200 if args.draft else 3200;scene.render.resolution_y=675 if args.draft else 1800
 scene.cycles.samples=20 if args.draft else 72;scene.cycles.adaptive_min_samples=8 if args.draft else 16;scene.cycles.adaptive_threshold=.10 if args.draft else .035
 rows=[]
 for cam in cams:
  start=time.time();obj=scene.camera;obj.location=cam['eye'];direction=Vector(cam['target'])-obj.location
  obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();obj.data.lens=cam['lens'];obj.data.dof.use_dof=not args.draft
  obj.data.dof.focus_distance=direction.length;path=folder/(cam['name']+'.png');scene.render.filepath=path.as_posix()
  log('CINEMATIC_RENDER_START',cam['name']);bpy.ops.render.render(write_still=True)
  rows.append(dict(cam,file=path.name,render_seconds=round(time.time()-start,1)))
  (folder/'renders.json').write_text(json.dumps(dict(source_only=True,in_game_capture=False,version='v065',presentation_lighting=True,renders=rows),indent=2)+'\n')
  log('CINEMATIC_RENDER_SAVED',path.as_posix(),round(time.time()-start,1),'s')
 log('CINEMATIC_RENDER_COMPLETE')
if __name__=='__main__':main()
