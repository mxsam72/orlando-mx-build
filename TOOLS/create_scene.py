"""Run using Blender 4.5 --background --python create_scene.py."""
import bpy, math, json, random
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
NAME='orlandomx_2026_v005'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
q=np.load(ROOT/'01_GIS_AERIAL/route.npz')['q'];spec=json.loads((ROOT/'07_OBJECTS_SOURCE/scene_spec.json').read_text());H=np.load(ROOT/'02_HEIGHTMAP/height_metres.npy');rng=random.Random(94041)
origin=spec['origin'];assets=[];trees=[]
def height(x,z):
    a=np.clip(x/600*2048,0,2048);b=np.clip((600-z)/600*2048,0,2048);i=int(a);j=int(b);ii=min(i+1,2048);jj=min(j+1,2048);u=a-i;v=b-j
    return float(H[j,i]*(1-u)*(1-v)+H[j,ii]*u*(1-v)+H[jj,i]*(1-u)*v+H[jj,ii]*u*v)
def vec(x,y,z):return (x,-z,y)
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.9
    img=bpy.data.images.new(name+'_texture',width=64,height=64);img.generated_color=(*color,1);img.filepath_raw=str(ROOT/'04_TEXTURES'/(name+'.tga'));img.file_format='TARGA';img.save()
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);return m
mats={k:mat(k,c) for k,c in {'bark':(.23,.18,.12),'foliage_dark':(.13,.23,.075),'foliage_mid':(.20,.31,.095),'foliage_light':(.29,.38,.13),'fence_wood':(.43,.36,.24),'marker_white':(.89,.87,.72),'marker_orange':(.85,.26,.03),'metal':(.40,.44,.43),'roof':(.25,.29,.23),'banner':(.025,.07,.08)}.items()}
def finish(obj,name,material,record=True):
    obj.name=name;obj.data.materials.append(mats[material]);
    if record:assets.append(obj)
    return obj
def cube(name,location,dimensions,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.dimensions=dimensions;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(obj,name,material)
def tube(name,a,b,r,material,verts=6):
    va=Vector(a);vb=Vector(b);delta=vb-va;bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=delta.length,location=(va+vb)/2);o=bpy.context.object;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();return finish(o,name,material)
def tree(x,z,i):
    y=height(x,z);h=rng.uniform(8,14);r=rng.uniform(3,4.4);pine=i%3==0;V=[];F=[];MI=[];centers=[]
    def branch(a,b,rad1,rad2,sides=6):
        a=np.array(a,float);b=np.array(b,float);v=(b-a)/np.linalg.norm(b-a);u=np.cross(v,[0,0,1])
        if np.linalg.norm(u)<.1:u=np.cross(v,[0,1,0])
        u/=np.linalg.norm(u);w=np.cross(v,u);start=len(V)
        for c,rad in [(a,rad1),(b,rad2)]:
            for j in range(sides):V.append((c+rad*(u*math.cos(j*math.tau/sides)+w*math.sin(j*math.tau/sides))).tolist())
        for j in range(sides):F.append((start+j,start+(j+1)%sides,start+sides+(j+1)%sides,start+sides+j));MI.append(0)
    branch(vec(x,y,z),vec(x+.14,y+h*.8,z),rng.uniform(.14,.23),.045,7)
    for k in range(9):
        a=k*math.tau/9+rng.random()*.4;rr=r*(.8 if not pine else (1-k*.065));cy=y+h*(.52+k*.042);cx=x+rr*math.cos(a)*.6;cz=z+rr*math.sin(a)*.6;branch(vec(x,y+h*.45,z),vec(cx,cy,cz),.055,.015,5);centers.append((cx,cy,cz,r*.53))
    d=float(np.linalg.norm(q[::4,:2]-[x,z],axis=1).min());count=24 if d<22 else 9
    for cx,cy,cz,rad in centers:
        for j in range(count):
            a=rng.random()*math.tau;zz=rng.uniform(-1,1);rr=rad*rng.random()**.32;c=np.array(vec(cx,cy,cz))+rr*np.array([math.sqrt(1-zz*zz)*math.cos(a),math.sqrt(1-zz*zz)*math.sin(a),zz*.75]);a=rng.random()*math.tau;u=np.array([math.cos(a),math.sin(a),rng.uniform(-.7,.7)]);u/=np.linalg.norm(u);v=np.cross(u,[.1,.2,1]);v/=np.linalg.norm(v);le=rng.uniform(.4,.8);wi=le*rng.uniform(.35,.65)
            for angle in [0,1.8]:
                uu=u*math.cos(angle)+v*math.sin(angle);vv=-u*math.sin(angle)+v*math.cos(angle);b=len(V);V.extend([(c-uu*le).tolist(),(c+vv*wi).tolist(),(c+uu*le).tolist(),(c-vv*wi).tolist(),(c+np.array([0,0,.07])).tolist()]);F.extend([(b,b+1,b+4),(b+1,b+2,b+4),(b+2,b+3,b+4),(b+3,b,b+4)]);MI.extend([1+rng.randrange(3)]*4)
    me=bpy.data.meshes.new('tree_mesh_'+str(i));me.from_pydata(V,[],F);me.update();o=bpy.data.objects.new('tree_'+str(i),me);scene.collection.objects.link(o);finish(o,o.name,'bark')
    for name in ['foliage_mid','foliage_dark','foliage_light']:me.materials.append(mats[name])
    for poly,mi in zip(me.polygons,MI):poly.material_index=mi
    trees.append([x,z,h])
    if i%100==0:print('Trees',i,flush=True)
lo=q[:,:2].min(0);hi=q[:,:2].max(0)
for i in range(16000):
    if len(trees)>=690:break
    x=rng.uniform(max(20,lo[0]-65),min(580,hi[0]+65));z=rng.uniform(max(20,lo[1]-65),min(580,hi[1]+65))
    d=float(np.linalg.norm(q[::3,:2]-[x,z],axis=1).min());outside=x<lo[0]-6 or x>hi[0]+6 or z<lo[1]-6 or z>hi[1]+6
    x1,x2,z1,z2=spec['pit_rectangle'];near_pits=(228<x<352 and 80<z<177)
    if d<11.5 or near_pits or (not outside and rng.random()>.40):continue
    if any((x-t[0])**2+(z-t[1])**2<17 for t in trees):continue
    if height(x,z)<2.5:continue
    tree(x,z,len(trees))
# Trackside poles, placed outside the racing width and away from nearby lanes.
width=np.load(ROOT/'01_GIS_AERIAL/route.npz')['width'];stakes=[]
for s in np.arange(15,spec['model_length'],30):
    i=int(np.searchsorted(q[:,3],s));x,z,th=q[i,:3];normal=np.array([-math.sin(th),math.cos(th)])
    for side in [-1,1]:
        p=np.array([x,z])+normal*side*(width[i]/2+.8)
        if float(np.linalg.norm(q[::3,:2]-p,axis=1).min())<width[i]/2+.2:continue
        y=height(*p);o=tube('SOFTCPLAS_marker_'+str(len(stakes)),vec(p[0],y,p[1]),vec(p[0],y+.6,p[1]),.065,'marker_white',6);stakes.append(p.tolist())
# Paddock shade structures and a small original timing shelter.
for c,zoff in enumerate([4,-29]):
    cx=341+18*c;cz=147
    for dx,dz in [(-4,-3),(-4,3),(4,-3),(4,3)]:
        x=cx+dx;z=cz+dz;y=height(x,z);tube(f'WLLCONC_canopy_post_{c}_{dx}_{dz}',vec(x,y,z),vec(x,y+3.2,z),.065,'metal')
    cube('canopy_roof_'+str(c),vec(cx,height(cx,cz)+3.3,cz),(9,7,.13),'roof')
# Fence follows the spectator straight, with an opening for the start merge.
fence=[]
for ss in np.arange(0,90,3.2):
    if 5<ss<22:continue
    ix=int(np.searchsorted(q[:,3],ss));x,z,th=q[ix,:3];p=np.array([x+8.5*math.sin(th),z-8.5*math.cos(th)]);y=height(*p);j=len(fence);tube('fence_post_'+str(j),vec(p[0],y,p[1]),vec(p[0],y+1.35,p[1]),.055,'metal')
    if fence and ss-fence[-1][0]<4:
        old=fence[-1][1];yy=height(*old)
        for level in [.45,1.1]:tube(f'fence_rail_{j}_{level}',vec(old[0],yy+level,old[1]),vec(p[0],y+level,p[1]),.018,'metal',4)
    fence.append((ss,p))
for i,ss in enumerate([2,38,75]):
    ix=int(np.searchsorted(q[:,3],ss));x,z,th=q[ix,:3];p=np.array([x+12.5*math.sin(th),z-12.5*math.cos(th)]);y=height(*p);tube('utility_pole_'+str(i),vec(p[0],y,p[1]),vec(p[0],y+8.5,p[1]),.13,'fence_wood',8);cube('crossarm_'+str(i),vec(p[0],y+8,p[1]),(2.1,.15,.14),'fence_wood')
# Compact finish markers, with no overhead collision across the racing surface.
info=json.loads((ROOT/'01_GIS_AERIAL/geometry.json').read_text());src=23.;ix=int(np.searchsorted(q[:,3],src));x,z,th=q[ix,:3];n=np.array([-math.sin(th),math.cos(th)])
for side in [-1,1]:
    p=np.array([x,z])+n*side*8.5;y=height(*p);tube('finish_post_'+str(side),vec(p[0],y,p[1]),vec(p[0],y+3.1,p[1]),.12,'metal')
    cube('finish_panel_'+str(side),vec(p[0],y+2.7,p[1]),(.7,.12,.8),'marker_white')
exec((ROOT/'TOOLS/scenery_details.py').read_text())
# Apply transforms, assign a planar UV where needed, and export only scenery.
bpy.ops.object.select_all(action='DESELECT')
for o in assets:o.select_set(True)
bpy.context.view_layer.objects.active=assets[0];bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for o in assets:
    if not o.data.uv_layers:
        uv=o.data.uv_layers.new(name='UVMap')
        for p in o.data.polygons:
            for li in p.loop_indices:
                v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x*.2,v.z*.2)
# Blender Y=-game Z ensures this standard FBX conversion emits positive game Z.
bpy.ops.export_scene.fbx(filepath=str(ROOT/'07_OBJECTS_SOURCE/scenery.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
print('SCENERY_EXPORTED',len(assets),'objects',len(trees),'trees',flush=True)
# A separate ground object is for review. It is excluded from scenery.fbx.
n=513;coords=np.linspace(0,600,n);verts=[];faces=[]
for z in coords:
    for x in coords:verts.append(vec(x,height(x,z),z))
for j in range(n-1):
    for i in range(n-1):
        a=j*n+i;faces.append((a,a+n,a+n+1,a+1))
mesh=bpy.data.meshes.new('Review_terrain');mesh.from_pydata(verts,[],faces);mesh.update();ground=bpy.data.objects.new('TERRAIN_REVIEW_ONLY',mesh);scene.collection.objects.link(ground)
gm=bpy.data.materials.new('Ground_basemap');gm.use_nodes=True;node=gm.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'04_TEXTURES/basemap.tga'));gm.node_tree.links.new(node.outputs['Color'],gm.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);gm.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.96;mesh.materials.append(gm)
uv=mesh.uv_layers.new(name='UVMap')
for p in mesh.polygons:
    p.use_smooth=True
    for li in p.loop_indices:
        v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v.x/600,-v.y/600)
world=bpy.data.worlds.new('Florida_day') if not scene.world else scene.world;scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.69,.83,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(100,-100,200));sun=bpy.context.object;sun.data.energy=2.0;sun.rotation_euler=(.45,-.4,-.4);sun.data.angle=.08
bpy.ops.object.camera_add(location=(477,-564,273));camera=bpy.context.object;target=Vector((295,-292,3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=420;scene.camera=camera
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.render.resolution_x=1600;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'DOCUMENTATION/terrain_preview.png');scene.view_settings.view_transform='AgX'
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
notes=bpy.data.texts.new('BUILD_STATUS');notes.write('Orlando MX v005. Estimated construction from 2026 feature order with width guidance from 2024 footage. Not surveyed. RAW is the native game terrain. Scenery FBX excludes this review terrain. Game compilation and riding status: see DOCUMENTATION/build_status.json.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'07_OBJECTS_SOURCE/OrlandoMX_v005.blend'))
bpy.ops.render.render(write_still=True)
(ROOT/'DOCUMENTATION/scenery_validation.json').write_text(json.dumps(dict(trees=len(trees),objects=len(assets),markers=len(stakes),scenery_vertices=sum(len(o.data.vertices) for o in assets),scenery_polygons=sum(len(o.data.polygons) for o in assets),fbx_axis='Blender X=game X, Blender Y=-game Z, Blender Z=game Y; FBX -Z forward Y up',native_edf_conversion=False),indent=2)+'\n')
print('SCENE_COMPLETE',flush=True)

