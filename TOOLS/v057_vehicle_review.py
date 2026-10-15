"""Matched serialized-mesh source reviews; not MX Bikes captures."""
import json
import hashlib
import sys
import zipfile
import numpy as np
from PIL import Image, ImageDraw
from v057_inputs import R, PREV, O, sha, save
from v027_scenery import parse, geometry_records, vertices, child
from rebind_scenery import array
from v049_previews import font

OUT=R/'BUILD/v057_review'


def mesh_digest(path):
    ns,_=parse(path.read_bytes()); rec=geometry_records(ns); digest=hashlib.sha256()
    for name,(g,_) in sorted(rec.items()):
        if not name.startswith('van_shane_'):continue
        digest.update(name.encode())
        for prop in [child(g,b'Vertices'),child(g,b'PolygonVertexIndex'),child(child(g,b'LayerElementNormal'),b'Normals')]:
            decoded=np.round(array(prop),5).astype('<f8');decoded[decoded==0]=0.
            digest.update(decoded.tobytes())
    return digest.hexdigest()


def render(path,version,view,cam):
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
    ns,_=parse(path.read_bytes()); rec=geometry_records(ns)
    renderer=vtk.vtkRenderer();renderer.SetBackground(.77,.81,.84)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1200,760);window.SetMultiSamples(4);window.AddRenderer(renderer)
    allv=np.concatenate([vertices(g) for n,(g,_) in rec.items() if n.startswith('van_shane_')])
    anchor=np.array([343.8,allv[:,1].min(),153.8]);t=np.deg2rad(186);rot=np.array([[np.cos(t),0,np.sin(t)],[0,1,0],[-np.sin(t),0,np.cos(t)]])
    palette={'van_paint':(.065,.072,.077),'dark':(.028,.032,.035),'glass':(.018,.033,.043),'alloy':(.53,.56,.57),
             'steel':(.35,.37,.38),'tire':(.045,.045,.043),'tread':(.05,.05,.047),'red_light':(.54,.012,.018),'headlight':(.71,.74,.72),
             'chevy_badge':(.68,.48,.12),'amber':(.79,.32,.018)}
    for name,(g,_) in rec.items():
        if not name.startswith('van_shane_'):continue
        v=(vertices(g)-anchor)@rot
        inds=array(child(g,b'PolygonVertexIndex')).reshape(-1,3);inds=np.where(inds<0,-inds-1,inds)[:,::-1]
        # Use serialized polygon normals, including real hard body creases.
        raw_norm=array(child(child(g,b'LayerElementNormal'),b'Normals')).reshape(-1,3,3)[:,::-1]
        nv=(raw_norm*[1,1,-1])@rot
        points=vtk.vtkPoints();points.SetData(numpy_to_vtk(v[inds].reshape(-1,3),deep=True));polys=vtk.vtkCellArray()
        for i in range(len(inds)):polys.InsertNextCell(3,[i*3,i*3+1,i*3+2])
        data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(polys)
        data.GetPointData().SetNormals(numpy_to_vtk(nv.reshape(-1,3),deep=True))
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(data)
        actor=vtk.vtkActor();actor.SetMapper(mapper);p=actor.GetProperty();key=name.removeprefix('van_shane_');p.SetColor(*palette[key]);p.SetAmbient(.23);p.SetDiffuse(.70);p.SetSpecular(.50 if key in ['van_paint','glass','alloy','steel'] else .08);p.SetSpecularPower(35 if key!='glass' else 70)
        renderer.AddActor(actor)
    plane=vtk.vtkPlaneSource();plane.SetOrigin(-7,-.013,-7);plane.SetPoint1(7,-.013,-7);plane.SetPoint2(-7,-.013,7)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(plane.GetOutputPort());actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.49,.48,.44);renderer.AddActor(actor)
    for position,intensity in [((4,8,5),.9),((-6,4,-4),.7),((1,5,-7),.6)]:
        light=vtk.vtkLight();light.SetPosition(*position);light.SetFocalPoint(0,1,0);light.SetIntensity(intensity);renderer.AddLight(light)
    camera=renderer.GetActiveCamera();camera.SetPosition(*cam);camera.SetFocalPoint(0,1.0,0);camera.SetViewUp(0,1,0);camera.ParallelProjectionOn();camera.SetParallelScale(3.05)
    renderer.ResetCameraClippingRange();window.Render();grab=vtk.vtkWindowToImageFilter();grab.SetInput(window);grab.Update()
    a=vtk_to_numpy(grab.GetOutput().GetPointData().GetScalars()).reshape(760,1200,-1)[::-1,:,:3].copy();window.Finalize()
    im=Image.fromarray(a);d=ImageDraw.Draw(im);d.rectangle((0,0,1200,42),fill=(20,24,28));d.text((16,10),version+' Chevrolet Express / '+view+' — serialized source mesh; not game footage',font=font(20),fill='white')
    target=OUT/(version+'_express_'+view+'.jpg');im.save(target,quality=95);return target


def main():
    OUT.mkdir(parents=True,exist_ok=True); rows=[]
    for view,cam in [('side',(-11,2.2,0)),('front_three_quarter',(-8,4.2,9)),('rear_three_quarter',(8,4,-9))]:
        frames=[]
        for version,folder in [('v056',PREV),('v057',O)]:
            p=render(folder/'scenery.fbx',version,view,cam);frames.append(Image.open(p).copy());rows.append(dict(file=p.name,sha256=sha(p),source_only=True))
        pair=Image.new('RGB',(2400,760));pair.paste(frames[0],(0,0));pair.paste(frames[1],(1200,0));pair.save(OUT/('comparison_express_'+view+'.jpg'),quality=94)
    import vtk
    save(OUT/'vehicle_review.json',dict(source_only=True,serialized_fbx_used=True,matched_camera_and_lights=True,approximate_material_lighting=True,meshes_sha256=sha(O/'scenery.fbx'),
        canonical_express_mesh_digests={v:mesh_digest(f/'scenery.fbx') for v,f in [('v056',PREV),('v057',O)]},renders=rows,vtk_version=vtk.vtkVersion.GetVTKVersion()))
    print('V057_EXPRESS_SOURCE_REVIEW_READY',flush=True)


def verify_saved_review():
    # Carry reviewed local renders into Windows without a second OpenGL stack.
    # The decoded, rounded serialized vertices/indices/normals must agree.
    with zipfile.ZipFile(R/'V057_SOURCE/express_review.zip') as z:
        assert z.testzip() is None
        for name in z.namelist():
            assert '/' not in name and '\\' not in name and name.endswith(('.jpg','.json'))
            (OUT/name).write_bytes(z.read(name))
    q=json.loads((OUT/'vehicle_review.json').read_text())
    for version,folder in [('v056',PREV),('v057',O)]:assert q['canonical_express_mesh_digests'][version]==mesh_digest(folder/'scenery.fbx')
    for row in q['renders']:assert sha(OUT/row['file'])==row['sha256']
    q['meshes_sha256']=sha(O/'scenery.fbx');q['decoded_serialized_meshes_match_reviewed_source']=True;save(OUT/'vehicle_review.json',q)
    print('V057_SAVED_EXPRESS_REVIEWS_VERIFIED_AGAINST_DECODED_SERIALIZED_MESHES',flush=True)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='verify':verify_saved_review()
    else:main()
