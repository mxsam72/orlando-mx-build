"""Export Moon v002 actual native scenery/sky and preview the same asset inputs."""
from pathlib import Path
import json,math,hashlib,time
import bpy
import numpy as np
from mathutils import Vector
R=Path(__file__).resolve().parents[1];B=R/'build';P=R/'previews_v002';NAME='taurus_littrow_mx_v002'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
terrain=np.load(B/'terrain_preview.npz');z=terrain['height'];xy=terrain['route_xy'];x=terrain['x'];y=terrain['y'];assets=[];probes=[]
def height(px,py):
 col=np.clip((np.asarray(px)+800)/1600*(len(x)-1),0,len(x)-1.001);row=np.clip((800-np.asarray(py))/1600*(len(y)-1),0,len(y)-1.001);i=col.astype(int);j=row.astype(int);u=col-i;v=row-j
 return z[j,i]*(1-u)*(1-v)+z[j,i+1]*u*(1-v)+z[j+1,i]*(1-u)*v+z[j+1,i+1]*u*v

def mat(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.96;p.inputs['Specular IOR Level'].default_value=.1
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(B/(name+'.tga')),check_existing=True);m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);return m
mats={n:mat(n) for n in ['v002_regolith','v002_marker_white','v002_marker_blue','v002_rock','v002_panel','NOLIGHTING_moon_black']}

def finish(o,name,material):
 o.name=name;o.data.materials.append(mats[material]);assets.append(o)
 if not o.data.uv_layers:
  uv=o.data.uv_layers.new(name='UVMap')
  for loop in o.data.loops:
   v=o.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x*.5,v.y*.5)
 return o

def cube(name,pos,dim,material):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,material)

def mesh_grid(name,data,step=1,hole=0):
 coordsx=data['x'][::step];coordsy=data['y'][::step];zz=data['height'][::step,::step];xx,yy=np.meshgrid(coordsx,coordsy);h,w=zz.shape;verts=np.stack([xx,yy,zz],-1).astype(np.float32).reshape(-1,3)
 a=(np.arange(h-1)[:,None]*w+np.arange(w-1)[None,:]).ravel()
 if hole:
  c=(verts[a,:2]+verts[a+w+1,:2])*.5;a=a[~((abs(c[:,0])<hole)&(abs(c[:,1])<hole))]
  if hole==800:
   edge=((np.isclose(abs(verts[:,0]),800)&(abs(verts[:,1])<=800))|(np.isclose(abs(verts[:,1]),800)&(abs(verts[:,0])<=800)));verts[edge,2]=height(verts[edge,0],verts[edge,1])
 faces=np.stack([a,a+w,a+w+1,a+1],1).astype(np.int32);me=bpy.data.meshes.new(name);me.vertices.add(len(verts));me.vertices.foreach_set('co',verts.ravel());me.loops.add(faces.size);me.loops.foreach_set('vertex_index',faces.ravel());me.polygons.add(len(faces));me.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype=np.int32));me.polygons.foreach_set('loop_total',np.full(len(faces),4,np.int32));me.polygons.foreach_set('use_smooth',np.ones(len(faces),bool));me.update()
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',(verts[faces.ravel(),:2]*.5).ravel());return o

# Native scenery excludes the riding height field. Mesh coordinates are local
# around Shorty; the HMF applies the +800,+800 game-world translation.
o=mesh_grid('SHAD_measured_near',np.load(B/'mid_preview.npz'),2,800);o.data.materials.append(mats['v002_regolith']);assets.append(o)
# Align the 80 m context grid with the 1760 m near-terrain edge. Split
# the remote scenery into bounded patches for native lightmap allocation.
context=np.load(B/'context_preview.npz');context={k:context[k][1::2] if k in ['x','y'] else context[k][1::2,1::2] for k in ['x','y','height']}
for row in range(0,len(context['y'])-1,75):
 for col in range(0,len(context['x'])-1,75):
  rr=slice(row,min(row+76,len(context['y'])));cc=slice(col,min(col+76,len(context['x'])))
  tile=dict(x=context['x'][cc],y=context['y'][rr],height=context['height'][rr,cc])
  o=mesh_grid(f'SHAD_massif_patch_{row}_{col}',tile,1,1760);o.data.materials.append(mats['v002_regolith']);assets.append(o)
tangent=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None];norm=np.c_[-tangent[:,1],tangent[:,0]]
for i in range(0,len(xy),90):
 for side in [-1,1]:
  p=xy[i]+norm[i]*side*10.5;h=float(height(*p));o=cube('SOFTCPLAS_route_marker',(*p,h+.32),(.12,.12,.64),'v002_marker_white');o.rotation_euler.z=math.atan2(tangent[i,1],tangent[i,0]);cube('route_marker_blue',(*p,h+.57),(.125,.125,.13),'v002_marker_blue')
  if len(probes)<16 and p[0]>50:
   bpy.context.view_layer.update();v=o.matrix_world@o.data.vertices[0].co;probes.append([float(v.x),float(v.z),float(v.y)])
facility=np.load(B/'v002_facility.npz');pc=facility['pit'];h=float(height(*pc))
# A small original lunar service canopy and panels mark the pit apron.
for dx,dy in [(-5,-3),(-5,3),(5,-3),(5,3)]:cube('pit_service_post',(pc[0]+dx,pc[1]+dy,h+1.7),(.12,.12,3.4),'v002_panel')
cube('pit_service_roof',(pc[0],pc[1],h+3.5),(11,7,.2),'v002_marker_white')
for i in range(8):cube('pit_solar_panel',(pc[0]-4.6+i*1.3,pc[1],h+3.63),(1.2,6.3,.06),'v002_marker_blue')
# Sparse individual angular clasts are fictional detailing; kept off the race.
rng=np.random.default_rng(170020);rockverts=[];rockfaces=[]
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1);tmp=bpy.context.object;rv=np.array([v.co[:] for v in tmp.data.vertices]);rf=np.array([p.vertices[:] for p in tmp.data.polygons]);bpy.data.objects.remove(tmp,do_unlink=True)
for _ in range(1700):
 px,py=rng.uniform(-740,740,2)
 if np.min(np.sum((xy-[px,py])**2,axis=1))<15**2 or (abs(px-pc[0])<55 and abs(py-pc[1])<35):continue
 lane=facility['access']
 if np.min(np.sum((lane-[px,py])**2,axis=1))<10**2:continue
 r=float(rng.uniform(.10,.6));v=rv*(rng.uniform(.85,1.15,size=(len(rv),1)))*[r,r*.8,r*.6];v+=np.array([px,py,float(height(px,py))+r*.12]);rockfaces.extend((rf+len(rockverts)).tolist());rockverts.extend(v.tolist())
me=bpy.data.meshes.new('Lunar clasts');me.from_pydata(rockverts,[],rockfaces);me.update();o=bpy.data.objects.new('SHAD_illustrative_clasts',me);scene.collection.objects.link(o);finish(o,o.name,'v002_rock')
# No grass, trees, water, clouds or Earth scenery are imported.
def export(path,objects):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
export(B/'scenery.fbx',assets)
# Custom unlit black sky is compiled separately and referenced without '*'.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=1000);sky=bpy.context.object;sky.name='Moon_black_sky'
for p in sky.data.polygons:p.flip()
sky.data.materials.append(mats['NOLIGHTING_moon_black']);export(B/'moon_sky.fbx',[sky]);bpy.data.objects.remove(sky,do_unlink=True)
(B/'scenery_source_validation.json').write_text(json.dumps(dict(checks_pass=True,objects=len(assets),triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in assets),illustrative_rocks=len(rockverts)//len(rv),native_probe_local_xyz_m=probes,hmf_translation_xyz_m=[800,0,800],native_fbx_sha256=hashlib.sha256((B/'scenery.fbx').read_bytes()).hexdigest(),no_riding_terrain_in_fbx=True),indent=2)+'\n')

# Preview uses the actual native color, mask and normal maps just authored.
ground=mesh_grid('Riding terrain preview only',terrain)
m=bpy.data.materials.new('Native layered regolith inputs');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=.96;bs.inputs['Specular IOR Level'].default_value=.1
uv=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=800;l.new(uv.outputs['UV'],mapping.inputs[0])
def texture(filename,tiled=False,noncolor=False):
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(B/filename),check_existing=True)
 if noncolor:t.image.colorspace_settings.name='Non-Color'
 l.new(mapping.outputs[0] if tiled else uv.outputs['UV'],t.inputs['Vector']);return t
# Replace the mesh's world-space tiled UVs by the native global UVs.
for loop in ground.data.loops:
 v=ground.data.vertices[loop.vertex_index].co;ground.data.uv_layers.active.data[loop.index].uv=((v.x+800)/1600,(v.y+800)/1600)
a=texture('v002_regolith.tga',True);b=texture('v002_route.tga');mask=texture('mask_v002_route.tga');mix=n.new('ShaderNodeMixRGB');l.new(mask.outputs['Alpha'],mix.inputs[0]);l.new(a.outputs['Color'],mix.inputs[1]);l.new(b.outputs['Color'],mix.inputs[2]);fine=texture('v002_fine.tga',True);fine_mask=texture('mask_v002_grain.tga');mix2=n.new('ShaderNodeMixRGB');l.new(fine_mask.outputs['Alpha'],mix2.inputs[0]);l.new(mix.outputs[0],mix2.inputs[1]);l.new(fine.outputs['Color'],mix2.inputs[2]);l.new(mix2.outputs[0],bs.inputs['Base Color'])
a=texture('v002_regolith_n.tga',True,True);b=texture('v002_route_n.tga',False,True);nm=n.new('ShaderNodeMixRGB');l.new(mask.outputs['Alpha'],nm.inputs[0]);l.new(a.outputs['Color'],nm.inputs[1]);l.new(b.outputs['Color'],nm.inputs[2]);node=n.new('ShaderNodeNormalMap');l.new(nm.outputs[0],node.inputs['Color']);l.new(node.outputs['Normal'],bs.inputs['Normal']);ground.data.materials.append(m)
scene.world=bpy.data.worlds.new('Moon vacuum');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
sun=bpy.data.lights.new('Native synchronized sun','SUN');sun.energy=3.2;sun.angle=math.radians(.53);o=bpy.data.objects.new('Native synchronized sun',sun);scene.collection.objects.link(o);direction=Vector((-6,-6.6666667,10)).normalized();o.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.clip_end=60000
scene.render.engine='CYCLES';scene.cycles.samples=36;scene.cycles.use_denoising=True;scene.cycles.max_bounces=4;scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.5
shots=[dict(name='01_full_loop',eye=[-900,-1250,810],target=[-20,30,55],lens=43),dict(name='02_regolith_and_markers',eye=[-345,-310,float(height(-345,-310))+1.8],target=[-265,-319,float(height(-265,-319))+1.4],lens=27),dict(name='03_pits_and_entry',eye=[-530,-500,h+35],target=[-380,-370,h+2],lens=30)]
rows=[]
for shot in shots:
 cam.location=shot['eye'];cam.rotation_euler=(Vector(shot['target'])-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=shot['lens'];scene.render.filepath=str(P/(shot['name']+'.png'));start=time.time();bpy.ops.render.render(write_still=True);rows.append(dict(shot,seconds=round(time.time()-start,1)))
 (P/'renders.json').write_text(json.dumps(dict(version='moon-v002',offline_source_renders=True,in_game_capture=False,native_color_and_normal_files_used=True,scenery_fbx_sha256=hashlib.sha256((B/'scenery.fbx').read_bytes()).hexdigest(),renders=rows),indent=2)+'\n')
print('MOON_V002_SCENE_AND_PREVIEWS_COMPLETE',flush=True)
