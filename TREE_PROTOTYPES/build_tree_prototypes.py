"""Build and render review-only 3D tree assets. No track source is modified."""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

R=Path(__file__).resolve().parent
T=R/'textures'; O=R/'output'; O.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40
scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=64
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=2
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False

def material(name,texture=None,color=None,alpha=False,normal=None):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF')
    p.inputs['Roughness'].default_value=.93;p.inputs['Specular IOR Level'].default_value=.035
    if color:p.inputs['Base Color'].default_value=(*color,1)
    if texture:
        im=bpy.data.images.load(str(T/texture),check_existing=True)
        tex=nodes.new('ShaderNodeTexImage');tex.image=im
        links.new(tex.outputs['Color'],p.inputs['Base Color'])
        if alpha:
            # Cutout opacity, matching the intended native CK_ texture behavior.
            clip=nodes.new('ShaderNodeMath');clip.operation='GREATER_THAN';clip.inputs[1].default_value=.45
            links.new(tex.outputs['Alpha'],clip.inputs[0]);links.new(clip.outputs[0],p.inputs['Alpha'])
            m.surface_render_method='DITHERED';m.use_backface_culling=False
    if normal:
        im=bpy.data.images.load(str(T/normal),check_existing=True);im.colorspace_settings.name='Non-Color'
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;n=nodes.new('ShaderNodeNormalMap')
        n.inputs['Strength'].default_value=.65;links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],p.inputs['Normal'])
    return m

bark=material('pine_bark','pine_bark.tga',normal='pine_bark_n.tga')
pine_leaf=material('CK_pine_foliage','CK_pine_foliage.tga',alpha=True)
wood_leaf=material('CK_woodland_foliage','CK_woodland_foliage.tga',alpha=True)

class Mesh:
    def __init__(self):self.v=[];self.f=[];self.uv=[];self.norm=[]
    def face(self,ids,uv):self.f.append(tuple(ids));self.uv.append(uv)
    def tube(self,points,radii,sides=8):
        points=[Vector(p) for p in points];base=len(self.v);length=0;dist=[0]
        for a,b in zip(points,points[1:]):length+=(b-a).length;dist.append(length)
        for k,(p,r) in enumerate(zip(points,radii)):
            tangent=(points[min(k+1,len(points)-1)]-points[max(k-1,0)]).normalized()
            u=tangent.cross(Vector((0,0,1)))
            if u.length<.1:u=tangent.cross(Vector((0,1,0)))
            u.normalize();w=tangent.cross(u).normalized()
            for i in range(sides):
                d=u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides)
                self.v.append(tuple(p+d*r));self.norm.append(tuple(d))
        for k in range(len(points)-1):
            for i in range(sides):
                j=(i+1)%sides;u=i/sides;v=(i+1)/sides
                self.face((base+k*sides+i,base+k*sides+j,base+(k+1)*sides+j,base+(k+1)*sides+i),[(u,dist[k]/.85),(v,dist[k]/.85),(v,dist[k+1]/.85),(u,dist[k+1]/.85)])
    def spray(self,c,d,width,length,tile,rng,center):
        c=Vector(c);d=Vector(d).normalized()
        side=d.cross(Vector((0,0,1)))
        if side.length<.1:side=d.cross(Vector((0,1,0)))
        side.normalize();up=d.cross(side).normalized();twist=rng.uniform(-1.25,1.25)
        side=(side*math.cos(twist)+up*math.sin(twist)).normalized();up=d.cross(side).normalized()
        a=c-d*length*.38;b=c+d*length*.62
        points=[a-side*width/2,a+side*width/2,b+side*width/2,b-side*width/2,(a+b)/2+up*.055*width]
        x=(tile%2)*.5;y=(tile//2)*.5;pad=.005
        uvs=[(x+pad,y+pad),(x+.5-pad,y+pad),(x+.5-pad,y+.5-pad),(x+pad,y+.5-pad),(x+.25,y+.25)]
        radial=(c-Vector(center)).normalized();normal=(up*.80+radial*.35).normalized()
        # Explicit front and back geometry is retained in the exported FBX.
        for sign in [1,-1]:
            start=len(self.v);self.v.extend(tuple(p) for p in points);self.norm.extend([tuple(normal*sign)]*5)
            for i,j in [(0,1),(1,2),(2,3),(3,0)]:
                ids=[start+j,start+i,start+4];uv=[uvs[j],uvs[i],uvs[4]]
                if sign<0:ids.reverse();uv.reverse()
                self.face(ids,uv)
    def object(self,name,mat):
        if mat.name.startswith('CK_'):
            for face in self.f:
                a,b,c=[Vector(self.v[i]) for i in face[:3]]
                assert (b-a).cross(c-a).normalized().dot(Vector(self.norm[face[0]]))>.10,'Foliage shading normal faces through its own surface'
        me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(self.v,[],self.f);me.update();me.materials.append(mat)
        layer=me.uv_layers.new(name='UVMap')
        for polygon,uv in zip(me.polygons,self.uv):
            polygon.use_smooth=True
            for index,value in zip(polygon.loop_indices,uv):layer.data[index].uv=value
        me.normals_split_custom_set_from_vertices(self.norm)
        ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);return ob

def build_pine(seed=4701):
    rng=random.Random(seed);wood=Mesh();leaves=Mesh();H=11.1;RADIUS=3.05
    trunk=[(.13*math.sin(i*.7),.10*math.sin(i*.8+.3),H*i/12) for i in range(13)]
    wood.tube(trunk,[.26*(1-i/13)**1.1+.017 for i in range(13)],10)
    for angle in [0.2,1.7,3.3,4.6,5.6]:
        wood.tube([(0,0,.14),(.55*math.cos(angle),.55*math.sin(angle),.03),(1.05*math.cos(angle),1.05*math.sin(angle),.005)],[.13,.07,.007],7)
    for level,fraction in enumerate([.31,.39,.48,.57,.65,.73,.80,.86,.92]):
        count=[3,4,5,5,5,4,4,3,3][level]
        radius=RADIUS*math.sin(math.pi*((fraction-.20)/.84))**.85
        for j in range(count):
            angle=j*math.tau/count+level*1.917+rng.uniform(-.23,.23);z=H*fraction+rng.uniform(-.20,.20)
            length=radius*rng.uniform(.74,1.12);a=Vector((.10*math.sin(level),.06,z))
            tip=Vector((length*math.cos(angle),length*math.sin(angle),z+rng.uniform(.12,.65)))
            mid=a.lerp(tip,.56);mid.z-=.13
            wood.tube([a,mid,tip],[.047*(1-fraction)+.018,.022,.004],7)
            for t in [.36,.54,.71,.86,1.]:
                pos=a.lerp(tip,t);pos.z-=.06
                for side in [-1,1]:
                    aa=angle+side*rng.uniform(.35,.95)
                    reach=rng.uniform(.30,.56)*(1.1-.45*fraction)
                    end=pos+Vector((reach*math.cos(aa),reach*math.sin(aa),rng.uniform(.10,.38)))
                    wood.tube([pos,end],[.012,.0035],5)
                    for f in [.50,.90]:
                        c=pos.lerp(end,f)
                        leaves.spray(c,(end-pos)+Vector((rng.uniform(-.2,.2),rng.uniform(-.2,.2),.15)),rng.uniform(.65,1.05),rng.uniform(.75,1.15),rng.randrange(4),rng,(0,0,H*.66))
    for i in range(12):
        angle=rng.random()*math.tau;c=Vector((rng.uniform(.1,.4)*math.cos(angle),rng.uniform(.1,.4)*math.sin(angle),H-rng.uniform(.1,.8)))
        leaves.spray(c,(math.cos(angle)*.25,math.sin(angle)*.25,1),.65,.8,rng.randrange(4),rng,(0,0,H*.66))
    return [wood.object('A_Airy_Pine_Wood',bark),leaves.object('A_Airy_Pine_Foliage',pine_leaf)]

def build_woodland(seed=4702):
    rng=random.Random(seed);wood=Mesh();leaves=Mesh();H=8.8
    trunk=[(0,0,0),(.05,.02,1.2),(.18,-.08,2.6),(.20,-.13,3.5)]
    wood.tube(trunk,[.31,.27,.22,.17],11)
    for j in range(5):
        angle=j*math.tau/5+.35;wood.tube([(0,0,.16),(.65*math.cos(angle),.65*math.sin(angle),.07),(1.0*math.cos(angle),1.0*math.sin(angle),.015)],[.15,.075,.008],7)
    for limb in range(9):
        angle=limb*2.399+rng.uniform(-.3,.3);base=Vector((.15,-.08,rng.uniform(2.25,3.25)))
        tip=Vector((rng.uniform(1.0,2.1)*math.cos(angle),rng.uniform(1.0,2.1)*math.sin(angle),rng.uniform(5.5,7.8)))
        mid=base.lerp(tip,.48);mid+=Vector((-.15*math.sin(angle),.15*math.cos(angle),.20))
        wood.tube([base,mid,tip],[rng.uniform(.10,.15),.075,.018],9)
        for branch in range(7):
            t=.34+branch*.09;start=mid.lerp(tip,t)
            aa=angle+rng.uniform(-1.4,1.4);spread=rng.uniform(.70,1.55)
            end=start+Vector((spread*math.cos(aa),spread*math.sin(aa),rng.uniform(.25,1.15)))
            if end.z>H:end.z=H-rng.uniform(.05,.3)
            middle=start.lerp(end,.55);middle.z+=.10
            wood.tube([start,middle,end],[.033,.017,.004],7)
            for shoot in range(5):
                tt=.25+shoot*.18;pos=start.lerp(end,tt);a=aa+rng.uniform(-1.8,1.8)
                direction=Vector((math.cos(a),math.sin(a),rng.uniform(.20,.75)))
                c=pos+direction*rng.uniform(.12,.42)
                wood.tube([pos,c],[.006,.002],5)
                for twist in [0,1]:
                    delta=Vector((rng.uniform(-.18,.18),rng.uniform(-.18,.18),rng.uniform(-.12,.18)))
                    leaves.spray(c+delta,direction+delta,rng.uniform(.62,1.0),rng.uniform(.65,1.0),rng.randrange(4),rng,(0,0,6.4))
    return [wood.object('B_Dense_Woodland_Wood',bark),leaves.object('B_Dense_Woodland_Foliage',wood_leaf)]

groups={'A':build_pine(),'B':build_woodland()}

# Reconstruct the unmodified original generic geometry from its existing builder.
source=(R.parent/'TOOLS/create_scene.py').read_text();start=source.index('def tree(');end=source.index('\nlo=q',start)
rng=random.Random(94041);q=np.array([[0.,0.]])
def height(x,z):return 0.
def vec(x,y,z):return (x,z,y)
mats={k:material('old_'+k,color=c) for k,c in {'bark':(.23,.20,.15),'foliage_dark':(.11,.18,.065),'foliage_mid':(.17,.25,.10),'foliage_light':(.25,.31,.14)}.items()}
assets=[];trees=[]
def finish(obj,name,mat):obj.name=name;obj.data.materials.append(mats[mat]);assets.append(obj);return obj
exec(source[start:end],globals());tree(0,0,0);groups['OLD']=assets.copy()

def show(which):
    for key,obs in groups.items():
        for ob in obs:ob.hide_render=key!=which;ob.hide_set(key!=which)
def export(which):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in groups[which]:ob.hide_set(False);ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(O/('Tree_'+which+'_LOD0.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
    stats={}
    for ob in groups[which]:
        ob.data.calc_loop_triangles();stats[ob.name]=dict(vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles),material=ob.data.materials[0].name)
        assert all(math.isfinite(c) for v in ob.data.vertices for c in v.co)
        assert len(ob.data.uv_layers)>0
    return stats

stats={key:export(key) for key in ['A','B']}
groundmat=material('review_soil','review_soil.tga')
bpy.ops.mesh.primitive_plane_add(size=200);ground=bpy.context.object;ground.name='REVIEW_GROUND';ground.data.materials.append(groundmat)
for loop in ground.data.uv_layers.active.data:loop.uv*=100
world=bpy.data.worlds.new('Clear daylight review environment');scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;links=world.node_tree.links;sky=nodes.new('ShaderNodeTexSky');sky.sky_type='NISHITA'
sky.sun_elevation=math.radians(43);sky.sun_rotation=math.radians(128);sky.sun_disc=False
links.new(sky.outputs['Color'],nodes.get('Background').inputs['Color']);nodes.get('Background').inputs['Strength'].default_value=.30
bpy.ops.object.light_add(type='SUN',location=(8,-10,16));sun=bpy.context.object;sun.name='Review sun';sun.data.energy=2.4;sun.data.angle=math.radians(3)
sun.rotation_euler=(Vector((0,0,0))-sun.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.lens=46

def render(name,location,target,size=(1100,864),samples=16):
    camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=size[0];scene.render.resolution_y=size[1];scene.cycles.samples=min(samples,16)
    scene.render.filepath=str(O/(name+'.png'));print('RENDER',name,flush=True);bpy.ops.render.render(write_still=True)

for key in ['OLD','A','B']:
    show(key);render(key+'_front',(16,-21,7.2),(0,0,5.4))
    if key!='OLD':render(key+'_detail',(5.8,-7.5,5.8),(0,0,5.6),(1100,786),16)
    if key!='OLD':render(key+'_side',(-17,-18,6.5),(0,0,5.0),(900,900),16)

# Bike-height woodland comparison: three varied instances, using the same assets.
single=groups.copy();context=[]
for key in ['A','B']:
    for ob in list(scene.objects):
        if ob.name.startswith('CONTEXT_'):bpy.data.objects.remove(ob,do_unlink=True)
    show(key)
    for ob in groups[key]:ob.hide_render=True
    for i,(x,y,scale,angle) in enumerate([(-4.3,1.6,.86,.7),(.3,2.,1.05,2.1),(4.7,3.4,.94,4.5)]):
        for original in groups[key]:
            ob=original.copy();ob.data=original.data;ob.name='CONTEXT_'+key+str(i)+original.name;scene.collection.objects.link(ob)
            ob.hide_render=False;ob.hide_set(False);ob.location=(x,y,0);ob.scale=(scale,scale,scale);ob.rotation_euler.z=angle
    render(key+'_woodline',(0,-20,1.75),(0,2.0,4.6),(1440,800),16)
for ob in list(scene.objects):
    if ob.name.startswith('CONTEXT_'):bpy.data.objects.remove(ob,do_unlink=True)

# A short orbit uses the exact meshes and textures shown in the still renders.
for key in ['A','B']:
    show(key)
    for i in range(12):
        a=math.tau*i/12;render(key+'_orbit_'+str(i).zfill(3),(24*math.sin(a),-24*math.cos(a),6.8),(0,0,5.2),(640,480),4)

show('A');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Orlando_Tree_Prototypes.blend'))
report=dict(review_only=True,track_modified=False,in_game_test=False,renderer='Blender 4.5.3 Cycles CPU',foliage_source='Generated botanical texture atlases',foliage_alpha_test=.45,foliage_normals_align_with_front_and_back_faces=True,styles={'A':'Airy pine','B':'Dense evergreen woodland'},models=stats,pending=['User style selection','Native MX Bikes material, motion, scale and performance validation before replacement'])
(O/'prototype_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('TREE_PROTOTYPES_COMPLETE',json.dumps(stats),flush=True)
