"""Export v003 native geometry/sky, then render those same source assets."""
from pathlib import Path
import hashlib,json,math,time,os
import bpy
import numpy as np
from mathutils import Vector,Matrix
V=Path(__file__).resolve().parents[1];B=V/'build';P=V/'previews';G=B/'game'
spec=json.loads((B/'source_validation.json').read_text());design=np.load(B/'design.npz')
HEIGHT=design['height'];ACCESS=design['access'];BYPASSES=design['bypasses']
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
assets=[];probes=[];mats={}

def height(x,y):
    h=HEIGHT;c=np.clip((np.asarray(x)+800)/1600*2048,0,2047.999);r=np.clip((800-np.asarray(y))/1600*2048,0,2047.999)
    i=c.astype(int);j=r.astype(int);u=c-i;v=r-j
    return h[j,i]*(1-u)*(1-v)+h[j,i+1]*u*(1-v)+h[j+1,i]*(1-u)*v+h[j+1,i+1]*u*v

def material(name,unlit=False):
    if name in mats:return mats[name]
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(B/(name+'.tga')),check_existing=True)
    out=n.new('ShaderNodeOutputMaterial')
    shader=n.new('ShaderNodeBsdfPrincipled');shader.inputs['Roughness'].default_value=.96;shader.inputs['Specular IOR Level'].default_value=0
    l.new(tex.outputs['Color'],shader.inputs['Base Color']);l.new(shader.outputs[0],out.inputs[0])
    if unlit:
        # FBX's exporter discovers diffuse textures through Principled BSDF.
        # The NOLIGHTING filename makes the native result unlit.
        l.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
        l.new(tex.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=1
    mats[name]=m;return m

def finish(o,mat):
    o.data.materials.append(material(mat));assets.append(o);o.visible_shadow=False
    return o

def cube(name,pos,dim,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
    return finish(o,mat)

def grid(name,data,step=1,hole=0):
    x=data['x'][::step];y=data['y'][::step];z=data['height'][::step,::step]
    xx,yy=np.meshgrid(x,y);h,w=z.shape;verts=np.stack([xx,yy,z],-1).astype(np.float32).reshape(-1,3)
    a=(np.arange(h-1)[:,None]*w+np.arange(w-1)[None,:]).ravel()
    if hole:
        c=(verts[a,:2]+verts[a+w+1,:2])*.5;a=a[~((abs(c[:,0])<hole)&(abs(c[:,1])<hole))]
        if hole==800:
            edge=((np.isclose(abs(verts[:,0]),800)&(abs(verts[:,1])<=800))|(np.isclose(abs(verts[:,1]),800)&(abs(verts[:,0])<=800)))
            verts[edge,2]=height(verts[edge,0],verts[edge,1])
    faces=np.stack([a,a+w,a+w+1,a+1],1).astype(np.int32);me=bpy.data.meshes.new(name)
    me.vertices.add(len(verts));me.vertices.foreach_set('co',verts.ravel());me.loops.add(faces.size);me.loops.foreach_set('vertex_index',faces.ravel())
    me.polygons.add(len(faces));me.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype=np.int32));me.polygons.foreach_set('loop_total',np.full(len(faces),4,np.int32));me.polygons.foreach_set('use_smooth',np.ones(len(faces),bool));me.update()
    o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
    uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',(verts[faces.ravel(),:2]*.5).ravel());o.visible_shadow=False
    return o

for name,file,hole in [('VIEW_measured_near','mid_preview.npz',800),('VIEW_measured_massifs','context_preview.npz',1680)]:
    o=grid(name,np.load(B/file),hole=hole);finish(o,'v002_context')
xy=design['route_xy'];t=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];norm=np.c_[-t[:,1],t[:,0]]
features=spec['features']+[spec['optional_transfer']]
for i in range(0,len(xy),130):
    p=xy[i];in_gap=False
    for j in spec['features']:
        c=np.array(j['center']);d=np.array(j['direction']);delta=p-c
        if abs(delta@d)<j['gap']/2+4 and abs(delta@np.array([-d[1],d[0]]))<40:in_gap=True
    if in_gap:continue
    for side in [-1,1]:
        q=p+norm[i]*side*19;h=float(height(*q));o=cube('route_beacon',(*q,h+.55),(.22,.22,1.1),'v002_marker_white')
        cube('blue_beacon_cap',(*q,h+1.05),(.27,.27,.18),'v002_marker_blue')
        if len(probes)<20:
            bpy.context.view_layer.update();v=o.matrix_world@o.data.vertices[0].co;probes.append([float(v.x),float(v.z),float(v.y)])
for j in features:
    c=np.array(j['center']);d=np.array(j['direction']);n=np.array([-d[1],d[0]])
    for u in [-j['gap']/2,j['gap']/2+30]:
        for side in [-1,1]:
            q=c+d*u+n*side*28;z=float(height(*q))
            cube('crater_jump_tower',(*q,z+2.3),(.5,.5,4.6),'v002_panel')
            cube('crater_jump_tower_cap',(*q,z+4.5),(.8,.8,.4),'v002_marker_blue')
pit=design['pit'];ph=float(height(*pit))
for dx,dy in [(-7,-4),(-7,4),(7,-4),(7,4)]:cube('lunar_pit_post',(pit[0]+dx,pit[1]+dy,ph+2.2),(.25,.25,4.4),'v002_panel')
cube('lunar_pit_canopy',(pit[0],pit[1],ph+4.5),(15,9,.25),'v002_marker_white')
for i in range(8):cube('pit_charge_panel',(pit[0]-6+i*1.7,pit[1],ph+4.7),(1.5,8,.12),'v002_marker_blue')
# Original angular clasts; keep all running and landing corridors clear.
rng=np.random.default_rng(170003);groups={}
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1);proto=bpy.context.object
rv=np.array([v.co[:] for v in proto.data.vertices]);rf=np.array([p.vertices[:] for p in proto.data.polygons]);bpy.data.objects.remove(proto,do_unlink=True)
for _ in range(1800):
    p=rng.uniform(-760,760,2)
    if np.min(np.sum((xy-p)**2,1))<42**2 or (abs(p[0]-pit[0])<75 and abs(p[1]-pit[1])<48):continue
    if abs(p[1])<40 and -230<p[0]<250:continue
    if np.min(np.sum((ACCESS-p)**2,1))<15**2:continue
    if np.min(np.sum((BYPASSES.reshape(-1,2)-p)**2,1))<13**2:continue
    radius=rng.uniform(.22,1.6);verts=rv*[radius,radius*.8,radius*.65];verts+=np.array([*p,float(height(*p))+radius*.15])
    key=(int((p[0]+800)//400),int((p[1]+800)//400));vv,ff=groups.setdefault(key,([],[]));ff.extend((rf+len(vv)).tolist());vv.extend(verts.tolist())
for key,(vv,ff) in groups.items():
    me=bpy.data.meshes.new('authored_clasts');me.from_pydata(vv,[],ff);me.update();o=bpy.data.objects.new('VIEW_clasts_'+str(key),me);scene.collection.objects.link(o)
    uv=me.uv_layers.new(name='UVMap');finish(o,'v002_rock')

def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
export(B/'scenery.fbx',assets)
scenery_report=dict(checks_pass=True,native_fbx_sha256=hashlib.sha256((B/'scenery.fbx').read_bytes()).hexdigest(),
                    objects=len(assets),triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in assets),
                    native_probe_local_xyz_m=probes,hmf_translation_xyz_m=[800,0,800],no_riding_terrain_in_fbx=True)
(B/'scenery_validation.json').write_text(json.dumps(scenery_report,indent=2)+'\n')
assert scenery_report['triangles']<150000,scenery_report['triangles']

bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=48,radius=1000);sky=bpy.context.object;sky.name='Stars_skydome'
for p in sky.data.polygons:p.flip()
sky.data.materials.append(material('NOLIGHTING_v003_stars',True));sky.visible_shadow=False
direction=Vector((0,math.cos(math.radians(24)),math.sin(math.radians(24))))
right=direction.cross(Vector((0,0,1))).normalized();up=right.cross(direction).normalized()
bpy.ops.mesh.primitive_plane_add(size=2,location=direction*950);earth=bpy.context.object;earth.name='Earth_blue_marble'
earth.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler();r=950*math.tan(math.radians(6));earth.scale=(r,r,1)
earth.data.materials.append(material('NOLIGHTING_v003_earth',True));earth.visible_shadow=False
export(B/'moon_v003_sky.fbx',[sky,earth]);sky.hide_render=True
sky_report=dict(checks_pass=True,native_fbx_sha256=hashlib.sha256((B/'moon_v003_sky.fbx').read_bytes()).hexdigest(),
                stars_texture='NOLIGHTING_v003_stars.tga',earth_texture='NOLIGHTING_v003_earth.tga',earth_angular_diameter_degrees=12)
(B/'sky_validation.json').write_text(json.dumps(sky_report,indent=2)+'\n')
if os.environ.get('V003_EXPORT_ONLY')=='1':
    print('V003_NATIVE_FBX_EXPORT_PASS',flush=True)
    raise SystemExit(0)
for name in ['NOLIGHTING_v003_stars','NOLIGHTING_v003_earth']:
    m=mats[name];shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for link in list(shader.inputs['Base Color'].links):m.node_tree.links.remove(link)
    shader.inputs['Base Color'].default_value=(0,0,0,1)

# Preview the actual native colour/normal/mask files, with the same static shadow mask.
ground=grid('Riding_heightfield_preview',np.load(B/'terrain_preview.npz'))
coords=np.empty(len(ground.data.vertices)*3,np.float32);ground.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
indices=np.empty(len(ground.data.loops),np.int32);ground.data.loops.foreach_get('vertex_index',indices)
ground.data.uv_layers.active.data.foreach_set('uv',((coords[indices,:2]+800)/1600).ravel())
m=bpy.data.materials.new('Native_v003_terrain_layers');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
bs.inputs['Roughness'].default_value=.96;bs.inputs['Specular IOR Level'].default_value=0
coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=800;l.new(coord.outputs['UV'],mapping.inputs[0])
def texture(file,tiled=False,noncolor=False):
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(B/file),check_existing=True)
    if noncolor:t.image.colorspace_settings.name='Non-Color'
    l.new(mapping.outputs[0] if tiled else coord.outputs['UV'],t.inputs['Vector']);return t
base=texture('v003_terrain_color.tga');route=texture('v002_route.tga');rm=texture('mask_v003_route.tga');mix=n.new('ShaderNodeMixRGB');l.new(rm.outputs['Alpha'],mix.inputs[0]);l.new(base.outputs[0],mix.inputs[1]);l.new(route.outputs[0],mix.inputs[2])
fine=texture('v002_fine.tga',True);fm=texture('mask_v003_bypass.tga');mix2=n.new('ShaderNodeMixRGB');l.new(fm.outputs['Alpha'],mix2.inputs[0]);l.new(mix.outputs[0],mix2.inputs[1]);l.new(fine.outputs[0],mix2.inputs[2])
micro=texture('v002_regolith.tga',True);mm=texture('mask_v003_micro.tga');mixm=n.new('ShaderNodeMixRGB');l.new(mm.outputs['Alpha'],mixm.inputs[0]);l.new(mix2.outputs[0],mixm.inputs[1]);l.new(micro.outputs[0],mixm.inputs[2])
shadow=texture('v003_shadow_tile.tga',True);sm=texture('v003_shadow_mask.tga');mix3=n.new('ShaderNodeMixRGB');l.new(sm.outputs['Alpha'],mix3.inputs[0]);l.new(mixm.outputs[0],mix3.inputs[1]);l.new(shadow.outputs[0],mix3.inputs[2]);l.new(mix3.outputs[0],bs.inputs['Base Color'])
normal=texture('v002_regolith_n.tga',True,True);nm=n.new('ShaderNodeNormalMap');l.new(normal.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal']);ground.data.materials.append(m)
world=bpy.data.worlds.new('Stars_and_soft_fill');world.use_nodes=True;scene.world=world;wn=world.node_tree.nodes;wl=world.node_tree.links;wn.clear()
out=wn.new('ShaderNodeOutputWorld');env=wn.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(B/'NOLIGHTING_v003_stars.tga'),check_existing=True)
starbg=wn.new('ShaderNodeBackground');wl.new(env.outputs['Color'],starbg.inputs['Color']);starbg.inputs['Strength'].default_value=1
fill=wn.new('ShaderNodeBackground');fill.inputs['Color'].default_value=(.19,.19,.19,1);fill.inputs['Strength'].default_value=.7
ray=wn.new('ShaderNodeLightPath');mixw=wn.new('ShaderNodeMixShader');wl.new(ray.outputs['Is Camera Ray'],mixw.inputs[0]);wl.new(fill.outputs[0],mixw.inputs[1]);wl.new(starbg.outputs[0],mixw.inputs[2]);wl.new(mixw.outputs[0],out.inputs[0])
sun=bpy.data.lights.new('Native_sun','SUN');sun.energy=2.7;sun.angle=math.radians(.53);o=bpy.data.objects.new('Native_sun',sun);scene.collection.objects.link(o);o.rotation_euler=(-Vector((-8,-6,4)).normalized()).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Source_preview');cam=bpy.data.objects.new('Source_preview',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.clip_end=60000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.max_bounces=3
scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.3
shots=[
 dict(name='01_crater_arena',eye=[-1150,-1050,1080],target=[30,0,70],lens=28),
 dict(name='02_first_contact_earth',eye=[-550,-319,float(height(-550,-319))+3],target=[-540,-70,float(height(-550,-319))+1],lens=18),
 dict(name='03_event_horizon',eye=[450,375,float(height(450,375))+55],target=[540,210,float(height(540,210))+4],lens=22),
 dict(name='04_shorty_transfer',eye=[-285,-240,float(height(-285,-240))+80],target=[30,30,float(height(30,30))+25],lens=25),
]
rows=[]
for shot in shots:
    cam.location=shot['eye'];cam.rotation_euler=(Vector(shot['target'])-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=shot['lens']
    earth.scale=(30000/950,)*3;earth.location=cam.location
    scene.render.filepath=str(P/(shot['name']+'.png'));start=time.time();bpy.ops.render.render(write_still=True)
    rows.append(dict(shot,seconds=round(time.time()-start,1)))
    (P/'renders.json').write_text(json.dumps(dict(offline_source_previews=True,in_game_capture=False,native_colour_normal_and_shadow_mask_files=True,renders=rows),indent=2)+'\n')
print('V003_SCENE_AND_PREVIEWS_PASS',json.dumps(scenery_report),flush=True)
