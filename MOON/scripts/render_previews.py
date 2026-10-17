"""Blender 4.5 actual-source previews, not MX Bikes screenshots."""
from pathlib import Path
import json,math,time,hashlib
import bpy
import numpy as np
from mathutils import Vector
R=Path(__file__).resolve().parents[1];B=R/'build';P=R/'previews'
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.cycles.max_bounces=5
s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.exposure=1.0
s.world=bpy.data.worlds.new('Vacuum');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0

def material(name,image=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
 bs.inputs['Roughness'].default_value=.94;bs.inputs['Specular IOR Level'].default_value=.15;bs.inputs['Base Color'].default_value=(.179,.174,.168,1)
 geo=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.8;l.new(geo.outputs['Position'],noise.inputs['Vector'])
 fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=95;fine.inputs['Detail'].default_value=2;l.new(geo.outputs['Position'],fine.inputs['Vector'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.38;bump.inputs['Distance'].default_value=.018;l.new(noise.outputs['Fac'],bump.inputs['Height'])
 grain=n.new('ShaderNodeBump');grain.inputs['Strength'].default_value=.25;grain.inputs['Distance'].default_value=.002;l.new(fine.outputs['Fac'],grain.inputs['Height']);l.new(bump.outputs['Normal'],grain.inputs['Normal']);l.new(grain.outputs['Normal'],bs.inputs['Normal'])
 if image:
  tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(image));tex.extension='EXTEND';l.new(tex.outputs['Color'],bs.inputs['Base Color'])
 return m
terrain=np.load(B/'terrain_preview.npz');z=terrain['height'];x=terrain['x'];y=terrain['y']
def height(px,py):
 col=np.clip((np.asarray(px)+800)/1600*(len(x)-1),0,len(x)-1.001);row=np.clip((800-np.asarray(py))/1600*(len(y)-1),0,len(y)-1.001)
 i=col.astype(int);j=row.astype(int);u=col-i;v=row-j
 return z[j,i]*(1-u)*(1-v)+z[j,i+1]*u*(1-v)+z[j+1,i]*(1-u)*v+z[j+1,i+1]*u*v

def grid(name,data,mat,cut=False,hole=800):
 xx,yy=np.meshgrid(data['x'],data['y']);zz=data['height'];h,w=zz.shape;v=np.stack([xx,yy,zz],axis=-1).astype(np.float32).reshape(-1,3)
 a=(np.arange(h-1)[:,None]*w+np.arange(w-1)[None,:]).ravel()
 if cut:
  c=(v[a,:2]+v[a+w+1,:2])*.5;a=a[~((abs(c[:,0])<hole)&(abs(c[:,1])<hole))]
  edge=(np.isclose(abs(v[:,0]),800)&(abs(v[:,1])<=800))|(np.isclose(abs(v[:,1]),800)&(abs(v[:,0])<=800))
  if hole==800:v[edge,2]=height(v[edge,0],v[edge,1])
 faces=np.stack([a,a+w,a+w+1,a+1],axis=1).astype(np.int32);mesh=bpy.data.meshes.new(name)
 mesh.vertices.add(len(v));mesh.vertices.foreach_set('co',v.ravel());mesh.loops.add(faces.size);mesh.loops.foreach_set('vertex_index',faces.ravel())
 mesh.polygons.add(len(faces));mesh.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype=np.int32));mesh.polygons.foreach_set('loop_total',np.full(len(faces),4,np.int32));mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),bool));mesh.update()
 if not cut:
  uv=np.stack([(v[:,0]+800)/1600,(v[:,1]+800)/1600],axis=1);mesh.uv_layers.new(name='Terrain UV').data.foreach_set('uv',uv[faces.ravel()].ravel())
 o=bpy.data.objects.new(name,mesh);s.collection.objects.link(o);o.data.materials.append(mat)

grid('Measured terrain + fictional course',terrain,material('Regolith',B/'basemap.png'))
grid('Measured surroundings',np.load(B/'mid_preview.npz'),material('Surrounding regolith'),True)
grid('Taurus Littrow massifs',np.load(B/'context_preview.npz'),material('Context regolith'),True,1760)
rng=np.random.default_rng(17017);xy=terrain['route_xy'];bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1);proto=bpy.context.object;rock=proto.data
for v in rock.vertices:v.co*=float(rng.uniform(.7,1.25))
rock.materials.append(material('Illustrative angular clasts'));bpy.data.objects.remove(proto,do_unlink=True)
for i in range(3000):
 px,py=rng.uniform(-750,750,2)
 if np.min(np.sum((xy-[px,py])**2,axis=1))<12**2:continue
 r=float(rng.uniform(.12,.65));o=bpy.data.objects.new('Illustrative clast',rock);s.collection.objects.link(o);o.location=(px,py,float(height(px,py))+r*.12);o.scale=(r,r*.75,r*.6);o.rotation_euler=(rng.random(),rng.random(),rng.random()*6.28)
sun=bpy.data.lights.new('Lunar sun','SUN');sun.energy=3.2;sun.angle=math.radians(.53);o=bpy.data.objects.new('Lunar sun',sun);s.collection.objects.link(o)
direction=Vector((-.45,-.5,.75)).normalized();o.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camera);s.collection.objects.link(cam);s.camera=cam;camera.clip_end=60000
cameras=[dict(name='02_valley_overview',eye=[-900,-1250,810],target=[-20,30,65],lens=43),dict(name='03_shorty_trackside',eye=[-160,-130,float(height(-160,-130))+35],target=[0,35,float(height(0,35))+3],lens=32),dict(name='04_first_straight',eye=[-350,-317,float(height(-350,-317))+1.8],target=[-100,-310,float(height(-100,-310))+4],lens=30)]
rows=[]
for c in cameras:
 cam.location=c['eye'];cam.rotation_euler=(Vector(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=c['lens'];s.render.filepath=str(P/(c['name']+'.png'));start=time.time();print('RENDER_START',c['name'],flush=True)
 bpy.ops.render.render(write_still=True);rows.append(dict(c,seconds=round(time.time()-start,2)));(P/'renders.json').write_text(json.dumps(dict(offline_source_renders=True,in_game_capture=False,vertical_exaggeration=1,procedural_microdetail=True,sun_direction=list(direction),exposure=s.view_settings.exposure,render_inputs_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in B.glob("*_preview.npz")},renders=rows),indent=2)+'\n');print('RENDER_SAVED',c['name'],flush=True)
