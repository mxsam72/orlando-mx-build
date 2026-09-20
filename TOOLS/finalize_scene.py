import bpy,json
import numpy as np
from pathlib import Path
from mathutils import Vector
from matplotlib.path import Path as Polygon
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'07_OBJECTS_SOURCE/OrlandoMX_v006.blend'))
spec=json.loads((ROOT/'07_OBJECTS_SOURCE/scene_spec.json').read_text());ponds=[Polygon(p) for p in spec['pond_polygons']];removed=[]
for ob in list(bpy.data.objects):
 if ob.name.startswith('tree_') and ob.type=='MESH':
  base=np.mean([list(v.co) for v in list(ob.data.vertices)[:7]],axis=0)
  if any(p.contains_point(base[:2],radius=1.0) for p in ponds):removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
print('Removed trees overlapping ponds:',removed,flush=True)
assets=[o for o in bpy.data.objects if o.type=='MESH' and o.name!='TERRAIN_REVIEW_ONLY']
bpy.ops.object.select_all(action='DESELECT')
for ob in assets:ob.select_set(True)
bpy.context.view_layer.objects.active=assets[0]
bpy.ops.export_scene.fbx(filepath=str(ROOT/'07_OBJECTS_SOURCE/scenery.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True)
qa=json.loads((ROOT/'DOCUMENTATION/scenery_validation.json').read_text());qa.update(trees=sum(o.name.startswith('tree_') for o in assets),objects=len(assets),scenery_vertices=sum(len(o.data.vertices) for o in assets),scenery_polygons=sum(len(o.data.polygons) for o in assets),pond_tree_overlap_fixed=len(removed));(ROOT/'DOCUMENTATION/scenery_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
bpy.data.texts['BUILD_STATUS'].clear();bpy.data.texts['BUILD_STATUS'].write('Orlando MX v006: user-confirmed lap; estimated dimensions. Scenery export corrected for native compiler Z flip. Native build validation and game riding status recorded separately.')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'07_OBJECTS_SOURCE/OrlandoMX_v006.blend'))
scene=bpy.context.scene;scene.render.filepath=str(ROOT/'DOCUMENTATION/terrain_preview.png');bpy.ops.render.render(write_still=True)
r=np.load(ROOT/'01_GIS_AERIAL/route.npz');q=r['q'];H=np.load(ROOT/'02_HEIGHTMAP/height_metres.npy')
def point(s):
 x=np.interp(s,q[:,3],q[:,0]);z=np.interp(s,q[:,3],q[:,1]);i=int(x/600*2048);j=int((600-z)/600*2048);return Vector((x,z,float(H[j,i])+1.8))
cam=scene.camera;cam.data.type='PERSP';cam.data.lens=23;scene.render.resolution_x=1400;scene.render.resolution_y=788
for tag,s,end in [('spectator_straight',20,58),('wooded_return',700,744)]:
 cam.location=point(s);cam.rotation_euler=(point(end)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/f'DOCUMENTATION/{tag}.png');bpy.ops.render.render(write_still=True)


