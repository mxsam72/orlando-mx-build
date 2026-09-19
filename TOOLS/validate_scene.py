import bpy,json
from pathlib import Path
import numpy as np
from io_scene_fbx import parse_fbx as parse
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'07_OBJECTS_SOURCE/OrlandoMX_v005.blend'))
root,version=parse.parse(str(ROOT/'07_OBJECTS_SOURCE/scenery.fbx'))
vertices=[];props=[]
for child in root.elems:
    if child.id==b'Objects':
        for obj in child.elems:
            if obj.id==b'Geometry':
                for el in obj.elems:
                    if el.id==b'Vertices':vertices.append(np.asarray(el.props[0]).reshape(-1,3))
    if child.id==b'GlobalSettings':
        for child2 in child.elems:
            if child2.id==b'Properties70':
                for prop in child2.elems:
                    props.append([p.decode(errors='replace') if isinstance(p,bytes) else p for p in prop.props])
v=np.concatenate(vertices)
unit_cm=float(next(p[-1] for p in props if p[0]=='UnitScaleFactor'))
result={'blender_reopen':True,'fbx_version':version,'fbx_vertices':len(v),'fbx_raw_vertex_bounds_xyz':[v.min(0).tolist(),v.max(0).tolist()],'fbx_global_settings':props,'native_edf_validation':False,'fbx_unit_centimetres':unit_cm}
v=v*(unit_cm/100.)
result['fbx_physical_bounds_xyz_metres']=[v.min(0).tolist(),v.max(0).tolist()]
assert np.isfinite(v).all()
assert v[:,0].min()>0 and v[:,0].max()<600
assert v[:,2].min()>0 and v[:,2].max()<600
assert v[:,1].min()>0 and v[:,1].max()<30
assert 'TERRAIN_REVIEW_ONLY' in bpy.data.objects
result['fbx_axes_and_physical_dimensions_match_game_metres']=True
(ROOT/'DOCUMENTATION/fbx_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
