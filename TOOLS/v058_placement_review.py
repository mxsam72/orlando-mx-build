"""Placement-only view from saved FBX geometry and UVs; do not edit scene."""
import sys, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'TOOLS'))
from v027_scenery import parse,values,child,vertices,geometry_records
from rebind_scenery import array
from v057_inputs import BASE,PREV,O,sha,save
from scene_texture_bindings_v044 import actual_diffuse_bindings
from v054_previews import Terrain
from v056_surface import source
from v049_previews import font
from vehicle_textures_v022 import NATIVE_U_MIRROR_FIX

OUT=R/'BUILD/v058_review'
OUT.mkdir(parents=True,exist_ok=True)
PIN='59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604'
assert sha(O/'scenery.fbx')==PIN
nodes,_=parse((O/'scenery.fbx').read_bytes());rec=geometry_records(nodes)
objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
bindings={b['texture_id']:b['texture'] for b in actual_diffuse_bindings(nodes)['bindings']}
material_texture={v[2]:v[1] for v in links if v[1] in bindings and (v[0]!=b'OP' or v[3]==b'DiffuseColor')}
model_material={v[2]:v[1] for v in links if objects.get(v[1],{}).get('name')==b'Material'}
textures={}
anchor=np.array([343.8,2.9,153.8]);t=np.deg2rad(186)
rot=np.array([[np.cos(t),0,np.sin(t)],[0,1,0],[-np.sin(t),0,np.cos(t)]])

def transform(v): return (v-anchor)@rot

def image_texture(im):
    a=np.ascontiguousarray(np.asarray(im)[::-1])
    image=vtk.vtkImageData();image.SetDimensions(im.width,im.height,1)
    image.GetPointData().SetScalars(numpy_to_vtk(a.reshape(-1,a.shape[2]),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR))
    tex=vtk.vtkTexture();tex.SetInputData(image);tex.InterpolateOn();tex.RepeatOn()
    return tex

def texture(tid):
    if tid not in textures:
        name=bindings[tid]
        folders=[O/'facility_textures',R/'V052_OUTPUT/facility_textures',R/'V047_OUTPUT/facility_textures',BASE/'facility_textures',BASE/'materials',BASE]
        p=next((p/name for p in folders if (p/name).is_file()),None)
        if p: im=Image.open(p)
        else:
            video=next(objects[v[1]] for v in links if v[2]==tid and objects.get(v[1],{}).get('name')==b'Video')
            raw=child(video,b'Content')['props'];assert raw[:1]==b'R';im=Image.open(io.BytesIO(raw[5:]))
        im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
        textures[tid]=image_texture(im)
    return textures[tid]

renderer=vtk.vtkRenderer();renderer.SetBackground(.74,.80,.86);renderer.SetBackground2(.88,.91,.93);renderer.GradientBackgroundOn()
rendered=[]
for name,(g,mid) in rec.items():
    world=vertices(g);centre=(world.min(0)+world.max(0))/2
    if np.linalg.norm(centre[[0,2]]-anchor[[0,2]])>23:continue
    raw=array(child(g,b'PolygonVertexIndex'));indices=np.where(raw<0,-raw-1,raw)
    # Every source polygon stores its own UV/normal corners. Reverse winding
    # after the FBX-to-world handedness conversion, retaining that corner data.
    polygons=[];start=0
    for end in np.flatnonzero(raw<0):
        corners=list(range(start,end+1))[::-1]
        polygons.extend([[corners[0],corners[k],corners[k+1]] for k in range(1,len(corners)-1)])
        start=end+1
    corners=np.asarray(polygons);ind=indices[corners]
    v=transform(world)[ind].reshape(-1,3)
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(v,deep=True))
    polys=vtk.vtkCellArray();triples=np.arange(len(v)).reshape(-1,3)
    cells=np.column_stack([np.full(len(triples),3),triples]).ravel().astype(np.int64)
    polys.SetCells(len(triples),numpy_to_vtk(cells,deep=True,array_type=vtk.VTK_ID_TYPE))
    data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(polys)
    normals=next((n for n in g['children'] if n['name']==b'LayerElementNormal'),None)
    if normals:
        normal=array(child(normals,b'Normals')).reshape(-1,3)
        if len(normal)==len(raw): normal=normal[corners].reshape(-1,3)
        else: normal=normal[ind].reshape(-1,3)
        normal=(normal*[1,1,-1])@rot
        data.GetPointData().SetNormals(numpy_to_vtk(normal,deep=True))
    uvnode=next((n for n in g['children'] if n['name']==b'LayerElementUV'),None)
    tid=material_texture.get(model_material.get(mid))
    if uvnode:
        uv=array(child(uvnode,b'UV')).reshape(-1,2);indexnode=next((n for n in uvnode['children'] if n['name']==b'UVIndex'),None)
        if indexnode:uv=uv[array(indexnode)]
        uv=uv[corners].reshape(-1,2) if len(uv)==len(raw) else uv[ind].reshape(-1,2)
        # The old vehicle art is intentionally pre-flipped for the native
        # importer. The earlier placement-only CPU preview missed this
        # compensation, showing those existing numbers and logos backwards.
        texture_name=bindings.get(tid,'')
        art=Path(texture_name).stem.removeprefix('v024_vehicle_')
        if art in NATIVE_U_MIRROR_FIX:
            uv=uv.copy();uv[:,0]=1-uv[:,0]
        data.GetPointData().SetTCoords(numpy_to_vtk(uv,deep=True))
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(data)
    actor=vtk.vtkActor();actor.SetMapper(mapper);p=actor.GetProperty();p.SetAmbient(.31);p.SetDiffuse(.69);p.SetSpecular(.07);p.SetSpecularPower(24)
    if tid: actor.SetTexture(texture(tid));p.SetColor(1,1,1)
    else: p.SetColor(.24,.23,.20)
    if name=='van_shane_van_paint':p.SetSpecular(.42);p.SetSpecularPower(45)
    if 'glass' in name:p.SetSpecular(.6);p.SetSpecularPower(80)
    if name.startswith('v057_cardboard_sign'):p.SetAmbient(.46);p.SetDiffuse(.54);p.SetSpecular(0)
    renderer.AddActor(actor);rendered.append(name)
print('Placed saved meshes',len(rendered),flush=True)

# The accepted terrain provides the ground under the unchanged saved props.
terrain=Terrain(PREV/'terrain.raw')
import v049_previews as ground_render
ground_render.BOX=(312.,130.,373.,181.);ground_render.O=PREV
ground_render.source=lambda name,version:source(name)
col,_=ground_render.composite('v049',n=1600)
groundtex=image_texture(Image.fromarray(col))
n=140;x,z=np.meshgrid(np.linspace(312.,373.,n),np.linspace(181.,130.,n))
y=terrain.ground(x,z);verts=transform(np.stack([x,y,z],2).reshape(-1,3))
ids=np.arange(n*n).reshape(n,n);faces=np.stack([ids[:-1,:-1],ids[1:,:-1],ids[1:,1:],ids[:-1,1:]],2).reshape(-1,4)
points=vtk.vtkPoints();points.SetData(numpy_to_vtk(verts,deep=True));cells=vtk.vtkCellArray()
cells.SetCells(len(faces),numpy_to_vtk(np.column_stack([np.full(len(faces),4),faces]).ravel().astype(np.int64),deep=True,array_type=vtk.VTK_ID_TYPE))
data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(cells)
uv=np.stack([(x-312.)/61.,(z-130.)/51.],2).reshape(-1,2)
data.GetPointData().SetTCoords(numpy_to_vtk(uv,deep=True));mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(data)
actor=vtk.vtkActor();actor.SetMapper(mapper);actor.SetTexture(groundtex);actor.GetProperty().SetAmbient(.48);actor.GetProperty().SetDiffuse(.52);renderer.AddActor(actor)
for pos,intensity in [((-7,12,10),.85),((9,7,2),.48),((0,6,-12),.35)]:
    light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(*pos);light.SetFocalPoint(0,1,2);light.SetIntensity(intensity);renderer.AddLight(light)

camera=renderer.GetActiveCamera();camera.SetPosition(-10.5,5.2,14.5);camera.SetFocalPoint(0,.9,1.7);camera.SetViewUp(0,1,0);camera.ParallelProjectionOn();camera.SetParallelScale(5.5)
from v058_scene_software import render as software_render
a=software_render(renderer,1800,1100)
im=Image.fromarray(a);draw=ImageDraw.Draw(im)
draw.rectangle((0,0,1800,82),fill=(22,25,29));draw.text((24,12),'Chevrolet Express + sign | Current saved placement',font=font(28),fill='white')
draw.text((24,48),'Approved sign position | Legacy decal preview compensation corrected | Source-scene preview',font=font(21),fill=(212,221,227))
target=OUT/'Van_Sign_Current_Placement.jpg';im.save(target,quality=97,subsampling=0)
assert sha(O/'scenery.fbx')==PIN
save(OUT/'van_sign_placement_review.json',dict(source_scenery_sha256=PIN,source_unchanged=True,actual_serialized_geometry_and_uv=True,legacy_native_preflipped_decals_compensated_in_preview=True,sign_uv_and_texture_unchanged=True,ground_source='v056',approximate_lighting=True,sign_clearance_m=2.98,rendered_meshes=rendered,image=target.name,image_sha256=sha(target)))
print(target,flush=True)
