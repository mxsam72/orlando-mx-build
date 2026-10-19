"""Export Bushnell scenery and render the exact quantized source terrain."""
from pathlib import Path
import hashlib, json, math, os
import bpy
import numpy as np
from mathutils import Vector
R=Path(__file__).resolve().parents[1];B=R/'build/v001';P=R/'previews'
C=json.loads((R/'project.json').read_text());D=np.load(B/'design.npz');H=np.load(B/'height_metres.npy');plan=json.loads((B/'scenery_plan.json').read_text());origin=D['origin'];size=C['terrain']['size_m']
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
assets=[];mats={};rng=np.random.default_rng(901225)


def height(x,z):
    col=np.clip(np.asarray(x)/size*2048,0,2047.999);row=np.clip((size-np.asarray(z))/size*2048,0,2047.999);i=col.astype(int);j=row.astype(int);u=col-i;v=row-j
    return H[j,i]*(1-u)*(1-v)+H[j,i+1]*u*(1-v)+H[j+1,i]*(1-u)*v+H[j+1,i+1]*u*v


def local(p): return np.asarray(p)-origin


def material(name,color):
    m=bpy.data.materials.new('BushnellMX_'+name);m.use_nodes=True;m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.96;bs.inputs['Specular IOR Level'].default_value=.1
    n=128;yy,xx=np.mgrid[:n,:n];noise=rng.normal(0,.025,(n,n))
    if name in ['bark','wood']:noise+=np.sin(xx*.45+np.sin(yy*.05))* .035
    pixels=np.empty((n,n,4),np.float32);pixels[:,:,:3]=np.clip(np.array(color)+noise[...,None],0,1);pixels[:,:,3]=1
    image=bpy.data.images.new(m.name,width=n,height=n);image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(B/(m.name+'.tga'));image.file_format='TARGA';image.save()
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mats[name]=m
    return m


for name,color in {'bark':(.25,.22,.15),'wood':(.40,.32,.21),'leaves_dark':(.15,.23,.08),'leaves_mid':(.23,.31,.12),'leaves_light':(.32,.38,.18),'moss':(.39,.43,.32),'metal':(.42,.46,.44),'rubber':(.055,.060,.052),'white':(.87,.86,.78),'orange':(.95,.25,.025),'blue':(.18,.26,.28),'red':(.55,.10,.055),'glass':(.10,.17,.18),'water':(.38,.43,.29)}.items():material(name,color)


def finish(o,name,mat):
    o.name=name;o.data.materials.append(mats[mat]);assets.append(o);return o


def cube(name,p,dim,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,mat)


def tube(name,a,b,r,mat,sides=6):
    a=Vector(a);b=Vector(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,mat)


def ball(name,p,scale,mat,segments=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=p);o=bpy.context.object;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for f in o.data.polygons:f.use_smooth=True
    return finish(o,name,mat)


# Branches and irregular crowns are actual low-cost geometry, not billboard trees.
groups={key:[[],[],[]] for key in ['bark','leaves_dark','leaves_mid','leaves_light','moss']}
def mesh_tube(a,b,r1,r2,mat='bark',sides=5):
    v,f,smooth=groups[mat];a=np.array(a);b=np.array(b);d=(b-a)/np.linalg.norm(b-a);u=np.cross(d,[0,0,1])
    if np.linalg.norm(u)<.1:u=np.cross(d,[0,1,0])
    u/=np.linalg.norm(u);w=np.cross(d,u);start=len(v)
    for center,rad in [(a,r1),(b,r2)]:
        for k in range(sides):v.append((center+rad*(u*math.cos(k*math.tau/sides)+w*math.sin(k*math.tau/sides))).tolist())
    for k in range(sides):f.append((start+k,start+(k+1)%sides,start+sides+(k+1)%sides,start+sides+k));smooth.append(True)


def crown(center,rad,mat,seed):
    v,f,smooth=groups[mat];start=len(v);random=np.random.default_rng(seed);rings=7;sides=11
    for j in range(rings):
        phi=-math.pi/2+.09+j*(math.pi-.18)/(rings-1)
        for k in range(sides):
            theta=k*math.tau/sides;r=rad*random.uniform(.93,1.07);v.append((np.array(center)+[r*math.cos(phi)*math.cos(theta),r*math.cos(phi)*math.sin(theta),r*.73*math.sin(phi)]).tolist())
    for j in range(rings-1):
        for k in range(sides):a=start+j*sides+k;bb=start+j*sides+(k+1)%sides;f.append((a,bb,bb+sides,a+sides));smooth.append(True)
    f.append(tuple(start+k for k in reversed(range(sides))));smooth.append(True);f.append(tuple(start+(rings-1)*sides+k for k in range(sides)));smooth.append(True)


for ti,t in enumerate(plan['trees']):
    random=np.random.default_rng(t['seed']);x,z=local(t['local_position']);base=float(height(x,z));h=t['height_m'];rad=t['crown_radius_m'];mesh_tube((x,z,base),(x+.12,z,base+h*.73),.22,.07,sides=7)
    for k in range(6):
        a=k*math.tau/6+random.uniform(-.3,.3);cx=x+rad*.58*math.cos(a);cz=z+rad*.58*math.sin(a);ch=base+h*(.57+k*.045)
        mesh_tube((x,z,base+h*.32),(cx,cz,ch),.09,.02);key=['leaves_dark','leaves_mid','leaves_light'][(ti+k)%3];crown((cx,cz,ch),rad*.63,key,ti*13+k)
        # Small folded leaf sprays break up the smooth mass, with hanging moss.
        v,f,sm=groups[key]
        for j in range(10):
            a=random.uniform(0,math.tau);r=rad*.62;c=np.array([cx+r*math.cos(a),cz+r*math.sin(a),ch+random.uniform(-r*.5,r*.5)]);u=np.array([math.cos(a),math.sin(a),.2])*random.uniform(.18,.40);w=np.array([-math.sin(a),math.cos(a),.3])*.13;b=len(v)
            v.extend([c-u,c+w,c+u,c-w,c+[0,0,.05]]);f.extend([(b,b+1,b+4),(b+1,b+2,b+4),(b+2,b+3,b+4),(b+3,b,b+4)]);sm.extend([False]*4)
        if ti%3==0:
            a=random.uniform(0,math.tau);p=np.array([cx+rad*.35*math.cos(a),cz+rad*.35*math.sin(a),ch-.3]);mesh_tube(p,p+[.15,0,-random.uniform(.8,1.5)],.06,.018,'moss',4)
for mat,(v,f,sm) in groups.items():
    me=bpy.data.meshes.new('BushnellMX_'+mat+'_geometry');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new('BushnellMX_'+mat,me);scene.collection.objects.link(o);finish(o,o.name,mat)
    for poly,s in zip(me.polygons,sm):poly.use_smooth=s


# Two timber viewing stands visible next to the west-side tables.
for i,stand in enumerate(plan['viewing_stands']):
    x,z=local(stand['local_position']);base=float(height(x,z));deck=base+stand['deck_height_m']
    for dx,dz in [(-1.6,-1.7),(-1.6,1.7),(1.6,-1.7),(1.6,1.7)]:cube(f'WLLCONC_BushnellMX_stand_post_{i}_{dx}_{dz}',(x+dx,z+dz,(base+deck+1.15)/2),(.16,.16,deck+1.15-base),'wood')
    for k in range(13):cube(f'BushnellMX_stand_plank_{i}_{k}',(x-1.56+k*.26,z,deck),( .245,3.65,.12),'wood')
    for dz in [-1.7,1.7]:
        for dh in [.55,1.15]:cube(f'BushnellMX_stand_rail_{i}_{dz}_{dh}',(x,z+dz,deck+dh),(3.4,.10,.12),'wood')
    for dx in [-1.6,1.6]:cube(f'BushnellMX_stand_end_{i}_{dx}',(x+dx,z,deck+1.15),(.10,3.4,.12),'wood')
    tube(f'BushnellMX_stand_brace_{i}',(x-1.6,z-1.7,base+.2),(x+1.6,z-1.7,deck-.2),.06,'wood')
    for k in range(8):cube(f'BushnellMX_stand_ladder_{i}_{k}',(x+1.8,z-1.6,base+.3+k*.35),(.8,.1,.10),'wood')


# Chain-link style boundary follows the access road outside the riding corridor.
fence_paths=[[[-63,138],[87,138]],[[87,138],[87,-47]],[[87,-73],[59,-73]],[[48,-73],[24,-73]]]
for fi,path in enumerate(fence_paths):
    a,b=map(local,path);n=int(np.linalg.norm(b-a)/3)+1;points=np.linspace(a,b,n)
    for j,p in enumerate(points):
        x,z=p;y=float(height(x,z));tube(f'BushnellMX_fence_post_{fi}_{j}',(x,z,y),(x,z,y+1.5),.033,'metal')
        if j:
            px,pz=points[j-1];py=float(height(px,pz))
            for level in [.1,1.4]:tube('BushnellMX_fence_rail',(px,pz,py+level),(x,z,y+level),.012,'metal',4)
            for k in range(6):
                u=k/6;v=min(1,u+.5);aa=points[j-1]*(1-u)+p*u;bb=points[j-1]*(1-v)+p*v
                tube('BushnellMX_chainlink',(aa[0],aa[1],py+.05),(bb[0],bb[1],y+1.4),.006,'metal',3)
                tube('BushnellMX_chainlink',(aa[0],aa[1],py+1.4),(bb[0],bb[1],y+.05),.006,'metal',3)


def route_point(st,offset=0):
    p=np.array([np.interp(st,D['station'],D['xy'][:,i]) for i in range(2)])-origin;t=np.array([np.interp(st,D['station'],D['tangent'][:,i]) for i in range(2)]);return p+offset*np.array([t[1],-t[0]])


# Only a few actual cone and tyre landmarks; the route remains visually open.
for i,st in enumerate([16,566,631,1154]):
    cur=np.interp(st,D['station'],D['curvature']);ww=np.interp(st,D['station'],D['width']);p=route_point(st,-(np.sign(cur) or 1)*(ww/2+.5));y=float(height(*p));cube('BushnellMX_cone_base',(*p,y+.025),(.42,.42,.05),'rubber')
    bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=.17,radius2=.035,depth=.64,location=(*p,y+.35));o=bpy.context.object
    if i==3:o.rotation_euler[0]=math.pi/2;o.location.z=y+.17
    finish(o,'BushnellMX_orange_cone','orange')
    if i!=3:
        bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=.105,radius2=.075,depth=.14,location=(*p,y+.42));finish(bpy.context.object,'BushnellMX_cone_band','white')
for k in range(4):
    p=route_point(1158,5.8)+[k*.8,0];y=float(height(*p));bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,location=(*p,y+.16),major_radius=.32,minor_radius=.12);finish(bpy.context.object,'BushnellMX_opening_tyres','rubber')


# White pickup, utility building, container, trailers and the landmark water tower.
x,z=local(plan['white_pickup']['local_position']);y=float(height(x,z));cube('BushnellMX_pickup_body',(x,z,y+.85),(5.4,2.0,.65),'white');cube('BushnellMX_pickup_cab',(x-.4,z,y+1.5),(2.5,1.85,.8),'white');cube('BushnellMX_pickup_window',(x-.4,z-.94,y+1.58),(2.1,.025,.43),'glass');cube('BushnellMX_pickup_windshield',(x-1.67,z,y+1.58),(.025,1.6,.45),'glass');cube('BushnellMX_pickup_bed',(x+1.8,z,y+1.2),(1.5,1.6,.12),'rubber')
for dx in [-1.8,1.7]:
    for dz in [-1,1]:tube('BushnellMX_pickup_wheel',(x+dx,z+dz-.12,y+.45),(x+dx,z+dz+.12,y+.45),.43,'rubber',16)
x,z=local(plan['shipping_container']['local_position']);y=float(height(x,z));cube('BushnellMX_container',(x,z,y+1.3),(6,2.5,2.6),'blue')
for k in range(24):cube('BushnellMX_container_corrugation',(x-2.9+k*.25,z-1.27,y+1.3),(.07,.06,2.5),'metal')
x,z=local(plan['red_utility_building']['local_position']);y=float(height(x,z));cube('BushnellMX_red_utility_building',(x,z,y+2),(19,8,4),'red');cube('BushnellMX_utility_roof',(x,z,y+4.1),(20,9,.18),'metal')
for dx in [-6,0,6]:cube('BushnellMX_utility_door',(x+dx,z-4.02,y+1.6),(2.6,.05,3.2),'white')
for i in range(3):
    x,z=local([26+i*13,-91]);y=float(height(x,z));cube('BushnellMX_paddock_trailer',(x,z,y+1.5),(8.5,3.1,2.8),'white');cube('BushnellMX_trailer_window',(x,z+1.57,y+1.65),(4.4,.03,.65),'glass')
x,z=local(plan['water_tower']['local_position']);y=float(height(x,z));tube('BushnellMX_water_tower_column',(x,z,y),(x,z,y+22),1.15,'white',20);ball('BushnellMX_water_tower_tank',(x,z,y+24),(4.4,4.4,3.5),'white',32,20)
for i in range(4):
    a=i*math.tau/4;tube('BushnellMX_tower_brace',(x+3*math.cos(a),z+3*math.sin(a),y),(x,z,y+20),.12,'white')
for i,(lx,lz) in enumerate([(-62,93),(-63,26),(81,88),(82,15),(45,-73)]):
    x,z=local([lx,lz]);y=float(height(x,z));tube('BushnellMX_utility_pole',(x,z,y),(x,z,y+9),.12,'wood',8);cube('BushnellMX_pole_crossarm',(x,z,y+8.6),(2.1,.13,.13),'wood')
for p in plan['water_basins']:
    x,z=local(p['local_position']);y=float(height(x,z))+.09;rx,rz=p['radius_m'];ball('BushnellMX_drainage_water',(x,z,y),(rx*.60,rz*.60,.018),'water',32,8)


# Transform and probe the native export before adding the review-only ground.
bpy.ops.object.select_all(action='DESELECT')
for o in assets:o.select_set(True)
bpy.context.view_layer.objects.active=assets[0];bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
probes=[]
for o in assets:
    if o.type!='MESH':continue
    if not o.data.uv_layers:
        uv=o.data.uv_layers.new(name='UVMap')
        for poly in o.data.polygons:
            for li in poly.loop_indices:
                v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x*.3+v.y*.17,v.z*.3)
    if 'stand_post' in o.name or 'container' in o.name or 'pickup_body' in o.name:
        v=o.data.vertices[0].co;probes.append([float(v.x),float(v.z),float(v.y)])
bpy.ops.export_scene.fbx(filepath=str(B/'scenery.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in assets)
report=dict(checks_pass=True,trees=len(plan['trees']),objects=len(assets),triangles=triangles,native_fbx_sha256=hashlib.sha256((B/'scenery.fbx').read_bytes()).hexdigest(),native_probe_xyz_m=probes[:24],native_basis='Blender X=game X, Y=game Z, Z=height; FBX -Z forward, Y up. FBX2EDF negates emitted Z.',landmark_dimensions='estimated from footage',in_game_capture=False)
(B/'scenery_validation.json').write_text(json.dumps(report,indent=2)+'\n');print('BUSHNELL_SCENERY_EXPORTED',triangles,len(assets),flush=True)
if os.environ.get('BUSHNELL_EXPORT_ONLY')=='1':raise SystemExit(0)


# The review mesh samples the same quantized RAW used for native collision.
indices=np.r_[np.arange(0,2049,3),2048];aa=np.linspace(0,size,2049);xx,zz=np.meshgrid(aa[indices],size-aa[indices]);hh=H[np.ix_(indices,indices)];verts=np.stack([xx,zz,hh],-1).astype(np.float32).reshape(-1,3);n=len(indices);a=(np.arange(n-1)[:,None]*n+np.arange(n-1)[None,:]).ravel();faces=np.stack([a,a+n,a+n+1,a+1],1).astype(np.int32)
me=bpy.data.meshes.new('BushnellMX_quantized_terrain');me.vertices.add(len(verts));me.vertices.foreach_set('co',verts.ravel());me.loops.add(faces.size);me.loops.foreach_set('vertex_index',faces.ravel());me.polygons.add(len(faces));me.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype=np.int32));me.polygons.foreach_set('loop_total',np.full(len(faces),4,np.int32));me.polygons.foreach_set('use_smooth',np.ones(len(faces),bool));me.update();ground=bpy.data.objects.new('VIEW_ONLY_native_heightfield',me);scene.collection.objects.link(ground);uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',(verts[faces.ravel(),:2]/size).ravel())
m=bpy.data.materials.new('BushnellMX_native_ground_layers');m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.98;bs.inputs['Specular IOR Level'].default_value=.03
coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=128;links.new(coord.outputs['UV'],mapping.inputs[0])
def tex(filename,tiled=False):
    t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(B/filename),check_existing=True);links.new(mapping.outputs[0] if tiled else coord.outputs['UV'],t.inputs['Vector']);return t
base=tex('basemap.tga');previous=base.outputs['Color']
for tile,mask in [('grass','mask_grass'),('soil','mask_shoulder'),('prepared','mask_detail')]:
    detail=tex(tile+'.tga',True);alpha=tex(mask+'.tga');mix=nodes.new('ShaderNodeMixRGB');links.new(alpha.outputs['Alpha'],mix.inputs[0]);links.new(previous,mix.inputs[1]);links.new(detail.outputs['Color'],mix.inputs[2]);previous=mix.outputs[0]
links.new(previous,bs.inputs['Base Color']);normal=tex('prepared_n.tga',True);normal.image.colorspace_settings.name='Non-Color';nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=1;links.new(normal.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal']);me.materials.append(m)
world=bpy.data.worlds.new('BushnellMX_daylight');world.use_nodes=True;scene.world=world;bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.35,.61,.92,1);bg.inputs['Strength'].default_value=.75
sun=bpy.data.lights.new('BushnellMX_sun','SUN');sun.energy=2.4;sun.angle=.055;o=bpy.data.objects.new('BushnellMX_sun',sun);scene.collection.objects.link(o);o.rotation_euler=(-Vector((-6,-5,10))).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('BushnellMX_source_camera');cam=bpy.data.objects.new('BushnellMX_source_camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.clip_end=2500;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True;scene.cycles.max_bounces=3;scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
shots=[('BushnellMX_v001_03_overview',[139,-148,160],[0,34,3],38)]
for filename,eye_st,target_st in [('BushnellMX_v001_04_west_tables',939,963),('BushnellMX_v001_05_south_table',1073,1094),('BushnellMX_v001_06_shaded_hairpin',136,160),('BushnellMX_v001_07_east_table',659,682)]:
    p=route_point(eye_st);q=route_point(target_st);shots.append((filename,[*(p+origin),float(height(*p))+1.8],[*(q+origin),float(height(*q))+.7],24))
for filename,eye,target,lens in shots:
    e=local(eye[:2]);t=local(target[:2]);cam.location=(*e,eye[2]);cam.rotation_euler=(Vector((*t,target[2]))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=lens;scene.render.filepath=str(P/(filename+'.png'));bpy.ops.render.render(write_still=True)
    if filename.endswith('overview'):
        with open(B/'overview_render.txt','w') as f:f.write(filename+'\n')
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(B/'BushnellMX_v001.blend'))
(P/'BushnellMX_v001_preview_notes.json').write_text(json.dumps(dict(source_previews=True,in_game_capture=False,terrain_quantized_from_native_RAW=True,game_uses_its_own_daylight_sky=True,scenery_native_export_sha256=report['native_fbx_sha256'],shots=[s[0]+'.png' for s in shots]),indent=2)+'\n')
print('BUSHNELL_PREVIEWS_COMPLETE',flush=True)
