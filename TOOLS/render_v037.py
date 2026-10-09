"""Render actual v032 source assets; these are not MX Bikes game captures.

Read-only on track files. FBX material connections, UVs, positions and the native
height field are retained. Camera/render settings are presentation settings.
"""
from pathlib import Path
import argparse, collections, hashlib, io, json, math, os, re, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy
from v027_scenery import parse, values, child, vertices, geometry_records
from rebind_scenery import array
from v032_common import layer_blocks, atomic

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/os.environ.get('TRACK_SOURCE_FOLDER','V037_OUTPUT')
WORK=ROOT.parent/'v037-media-work'
OUT=ROOT.parent/('deliverables-v037-renders/'+SOURCE.name.lower())
SIZE=600.
HEIGHT=np.fromfile(SOURCE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
KEEP=[]

def log(message): print(message,flush=True)
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get_child(n,name): return next((x for x in n['children'] if x['name']==name),None)
def ground(x,z):
    scalar=np.asarray(x).ndim==0 and np.asarray(z).ndim==0
    ans=map_coordinates(HEIGHT,[(600-np.atleast_1d(z))/600*2048,np.atleast_1d(x)/600*2048],order=1,mode='nearest')
    return ans[0] if scalar else ans
CAMERA_HEIGHT=np.fromfile(ROOT/'V036_OUTPUT/terrain.raw','<u2').reshape(2049,2049)/65535*18
def loc(x,z,above):
    h=map_coordinates(CAMERA_HEIGHT,[[(600-z)/600*2048],[x/600*2048]],order=1,mode='nearest')[0]
    return [float(x),float(z),float(h)+above]
def font(n,bold=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',n)
def save_image(im,path,format,**options):
    buffer=io.BytesIO();im.save(buffer,format=format,**options);atomic(path,buffer.getvalue())

def vtk_texture(im):
    im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
    a=np.ascontiguousarray(np.asarray(im)[::-1]);h,w,c=a.shape
    d=vtk.vtkImageData();d.SetDimensions(w,h,1)
    d.GetPointData().SetScalars(numpy_to_vtk(a.reshape(-1,c),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR))
    t=vtk.vtkTexture();t.SetInputData(d);t.InterpolateOn();t.RepeatOn();t.MipmapOn()
    KEEP.extend([d,t]);return t

def make_poly(points,triangles,uv=None):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.asarray(points,np.float32),deep=True))
    cells=vtk.vtkCellArray();triangles=np.asarray(triangles,dtype=np.int64)
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0,3*len(triangles)+1,3,dtype=np.int64),deep=True),numpy_to_vtkIdTypeArray(triangles.ravel(),deep=True))
    d=vtk.vtkPolyData();d.SetPoints(p);d.SetPolys(cells)
    if uv is not None:
        tc=numpy_to_vtk(np.asarray(uv,np.float32),deep=True);tc.SetName('UV');d.GetPointData().SetTCoords(tc)
    KEEP.extend([p,cells,d]);return d

def actor_from_poly(poly,texture=None,smooth=False,specular=.05):
    normal=vtk.vtkPolyDataNormals();normal.SetInputData(poly);normal.ConsistencyOn();normal.AutoOrientNormalsOff();normal.ComputePointNormalsOn();normal.ComputeCellNormalsOff()
    normal.SetFeatureAngle(65 if smooth else 30)
    if smooth:normal.SplittingOff()
    else:normal.SplittingOn()
    normal.Update()
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(normal.GetOutputPort());m.ScalarVisibilityOff()
    a=vtk.vtkActor();a.SetMapper(m)
    if texture:a.SetTexture(texture)
    prop=a.GetProperty();prop.SetInterpolationToPhong();prop.SetAmbient(.42);prop.SetDiffuse(.70);prop.SetSpecular(specular);prop.SetSpecularPower(28);prop.BackfaceCullingOff()
    KEEP.extend([normal,m,a]);return a

def load_scenery():
    nodes,_=parse((SOURCE/'scenery.fbx').read_bytes())
    objects=next(n for n in nodes if n['name']==b'Objects')['children']
    con=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    by_id={values(n)[0]:n for n in objects};models={k:n for k,n in by_id.items() if n['name']==b'Model'}
    materials={k:n for k,n in by_id.items() if n['name']==b'Material'}
    textures={k:n for k,n in by_id.items() if n['name']==b'Texture'}
    videos={k:n for k,n in by_id.items() if n['name']==b'Video'}
    model_materials=collections.defaultdict(list);mat_texture={};texture_video={}
    for c in con:
        if c[1] in materials and c[2] in models:model_materials[c[2]].append(c[1])
        if c[1] in textures and c[2] in materials and (len(c)<4 or c[3]==b'DiffuseColor'):mat_texture[c[2]]=c[1]
        if c[1] in videos and c[2] in textures:texture_video[c[2]]=c[1]
    all_texture={};texture_names={}
    for mid,tid in mat_texture.items():
        tx=textures[tid];name=values(child(tx,b'FileName'))[0].decode().replace('\\','/').split('/')[-1]
        file=SOURCE/'facility_textures'/name
        if file.exists():im=Image.open(file);im.load()
        else:
            video=videos[texture_video[tid]]
            content=values(child(video,b'Content'))[0]
            im=Image.open(io.BytesIO(content));im.load()
        all_texture[mid]=vtk_texture(im);texture_names[str(mid)]=dict(filename=name,size=list(im.size))
    grouped=collections.defaultdict(lambda:dict(v=[],t=[],uv=[],count=0,names=[]))
    bounds={};face_count=0;vertex_count=0
    for name,(g,modelid) in geometry_records(nodes).items():
        v=vertices(g)[:,[0,2,1]].astype(np.float32)
        bounds[name]=[v.min(0).tolist(),v.max(0).tolist()]
        indices=array(child(g,b'PolygonVertexIndex')).astype(np.int64)
        uv_layer=get_child(g,b'LayerElementUV')
        if uv_layer:
            direct=array(child(uv_layer,b'UV')).reshape(-1,2)
            ref=values(child(uv_layer,b'ReferenceInformationType'))[0]
            uv=direct[array(child(uv_layer,b'UVIndex')).astype(int)] if ref==b'IndexToDirect' else direct
            assert len(uv)==len(indices),(name,len(uv),len(indices))
        else:uv=np.zeros((len(indices),2))
        pv=v[np.where(indices<0,-indices-1,indices)]
        material_layer=get_child(g,b'LayerElementMaterial')
        mat_indices=array(child(material_layer,b'Materials')).astype(int) if material_layer else np.array([0])
        mapping=values(child(material_layer,b'MappingInformationType'))[0] if material_layer else b'AllSame'
        ends=np.flatnonzero(indices<0);start=0
        for face_i,end in enumerate(ends):
            mat_slot=int(mat_indices[face_i if mapping==b'ByPolygon' else 0])
            mats=model_materials[modelid];mid=mats[mat_slot] if mats else None
            group=grouped[mid];n=end-start+1;base=group['count']
            group['v'].append(pv[start:end+1]);group['uv'].append(uv[start:end+1]);group['count']+=n
            # Native writer reverses faces before its Z reflection. The XYZ ->
            # XZY conversion restores the authored front-face orientation.
            group['t'].extend([[base,base+i,base+i+1] for i in range(1,n-1)])
            if not group['names'] or group['names'][-1]!=name:group['names'].append(name)
            start=end+1;face_count+=1;vertex_count+=n
    actors=[]
    for mid,group in grouped.items():
        poly=make_poly(np.concatenate(group['v']),group['t'],np.concatenate(group['uv']))
        mat_name=values(materials[mid])[1].split(b'\0')[0].decode() if mid else 'unassigned'
        metallic=any(s in mat_name for s in ['steel','alloy','rim','cyber','glass'])
        a=actor_from_poly(poly,all_texture.get(mid),False,.20 if metallic else .035)
        if 'entry_sign' in mat_name or mat_name in ['v032_memorial','v033_qwikchute_logo']:
            # Each board explicitly contains front and rear artwork triangles.
            # Render the facing set once, preventing opposite-UV z fighting.
            a.GetProperty().BackfaceCullingOn()
        if mid not in all_texture and mid:
            p=get_child(materials[mid],b'Properties70')
            color=next((values(q)[4:7] for q in p['children'] if values(q)[0]==b'DiffuseColor'),[.65,.65,.65])
            a.GetProperty().SetColor(*color)
        actors.append(a)
    meta=dict(models=len(bounds),materials=len(grouped),faces=int(face_count),polygon_vertices=int(vertex_count),textures=texture_names,bounds=bounds)
    (WORK/(SOURCE.name.lower()+'_scene_metadata.json')).write_text(json.dumps(meta,indent=2))
    log(f'Scenery loaded: {len(bounds)} real models, {face_count} faces, {len(grouped)} materials')
    return actors,bounds

def find_source(name):
    for folder in [SOURCE/'materials',SOURCE/'facility_textures',SOURCE/'masks',SOURCE]:
        if (folder/name).exists():return folder/name
    # Windows native staging prefixes the retained physical mask filename.
    if name.startswith('mask_') and (SOURCE/'masks'/name[5:]).exists():return SOURCE/'masks'/name[5:]
    raise FileNotFoundError(name)

def terrain_image(box,n=3072):
    maskproof=SOURCE/'holeshot_mask_validation.json'
    sig=digest(maskproof)[:12] if maskproof.exists() else digest(SOURCE/'terrain.raw')[:12]
    key=SOURCE.name+'_'+sig+'_'+'_'.join(str(round(x,2)) for x in box)+f'_{n}'
    cache=WORK/'terrain_textures'/f'{key}.png';cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        try:
            im=Image.open(cache);im.load();return im
        except OSError:cache.unlink()
    X=np.linspace(box[0],box[2],n,dtype=np.float32);Z=np.linspace(box[3],box[1],n,dtype=np.float32)
    result=np.zeros((n,n,3),np.float32)
    for index,_,block in layer_blocks((SOURCE/'compiled_track.hmf').read_text()):
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1]
        if index==0:continue # Completely covered by native unmasked layer1.
        rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        tex=Image.open(find_source(name)).convert('RGB')
        footprint=max((box[2]-box[0])/(n-1),(box[3]-box[1])/(n-1))*rep/SIZE*tex.width
        factor=2**max(0,int(math.floor(math.log2(max(1.,footprint)))))
        if factor>1:tex=tex.resize((max(4,tex.width//factor),max(4,tex.height//factor)),Image.Resampling.BOX)
        tex=np.asarray(tex,np.float32)
        mask_match=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        mask=np.asarray(Image.open(find_source(mask_match[1])).getchannel('A'),np.float32)/255 if mask_match else None
        tx=(X/SIZE*rep%1)*(tex.shape[1]-1)
        for row in range(0,n,96):
            z=Z[row:row+96];ty=((SIZE-z)/SIZE*rep%1)*(tex.shape[0]-1)
            xx,yy=np.meshgrid(tx,ty)
            sample=np.stack([map_coordinates(tex[...,c],[yy,xx],order=1,mode='grid-wrap') for c in range(3)],axis=-1)
            if mask is not None:
                mx,my=np.meshgrid(X/SIZE*(mask.shape[1]-1),(SIZE-z)/SIZE*(mask.shape[0]-1))
                alpha=map_coordinates(mask,[my,mx],order=1,mode='nearest')[...,None]
                result[row:row+96]=result[row:row+96]*(1-alpha)+sample*alpha
            else:result[row:row+96]=sample
        log(f'  Terrain layer {index}: {name}')
    im=Image.fromarray(np.uint8(np.clip(np.rint(result),0,255)));save_image(im,cache,'PNG')
    return im

def terrain_actor(box,n=3072,step=1,cut_box=None):
    # Align exactly to native height-field samples; no invented jump geometry.
    c0=max(0,int(math.floor(box[0]/SIZE*2048)));c1=min(2048,int(math.ceil(box[2]/SIZE*2048)))
    r0=max(0,int(math.floor((SIZE-box[3])/SIZE*2048)));r1=min(2048,int(math.ceil((SIZE-box[1])/SIZE*2048)))
    c0=c0//4*4;c1=min(2048,int(math.ceil(c1/4))*4)
    r0=r0//4*4;r1=min(2048,int(math.ceil(r1/4))*4)
    cs=np.arange(c0,c1+1,step);rs=np.arange(r0,r1+1,step)
    x=cs/2048*SIZE;z=SIZE-rs/2048*SIZE;xx,zz=np.meshgrid(x,z)
    box=[float(x[0]),float(z[-1]),float(x[-1]),float(z[0])]
    v=np.stack([xx,zz,HEIGHT[np.ix_(rs,cs)]],axis=-1).reshape(-1,3)
    uv=np.stack([(xx-box[0])/(box[2]-box[0]),(zz-box[1])/(box[3]-box[1])],axis=-1).reshape(-1,2)
    w=len(cs);rows=len(rs);a=(np.arange(rows-1)[:,None]*w+np.arange(w-1)[None,:]).ravel()
    # Row order follows decreasing game Z. Reverse to face upward in XZY.
    tri=np.concatenate([np.stack([a,a+w,a+1],1),np.stack([a+1,a+w,a+w+1],1)])
    if cut_box is not None:
        # Match the regional grid boundary and remove covered background cells,
        # avoiding coplanar overlays or floating distant scenery.
        cx0=math.floor(cut_box[0]/SIZE*2048/4)*4/2048*SIZE
        cx1=math.ceil(cut_box[2]/SIZE*2048/4)*4/2048*SIZE
        cz0=SIZE-math.ceil((SIZE-cut_box[1])/SIZE*2048/4)*4/2048*SIZE
        cz1=SIZE-math.floor((SIZE-cut_box[3])/SIZE*2048/4)*4/2048*SIZE
        centers=v[tri,:2].mean(1)
        inside=(centers[:,0]>cx0)&(centers[:,0]<cx1)&(centers[:,1]>cz0)&(centers[:,1]<cz1)
        tri=tri[~inside]
    poly=make_poly(v,tri,uv)
    actor=actor_from_poly(poly,vtk_texture(terrain_image(box,n)),True,.018)
    log(f'Terrain: {len(v)} native points / {len(tri)} triangles; crop {box}')
    return actor

def shots():
    return [dict(id='01_Oval_Overhead',title='Oval in the empty field',subtitle='Two grass infields, paved crossover and two Cybertrucks',pos=loc(535,340,155),focus=loc(535,340,0),up=[1,0,0],fov=50,box=[450,232,600,447],tex=4096,step=1),
      dict(id='02_Oval_Oblique',title='Car oval beyond the trees',subtitle='Paved loop and central crossover',pos=loc(668,477,126),focus=loc(528,340,.5),fov=56,box=[430,228,600,452],tex=4096,step=1),
      dict(id='03_Field_Entrance',title='Open entrance from the field',subtitle='White and green boundary with a clear opening',pos=loc(455,331,3.6),focus=loc(502,340,1.1),fov=75,box=[430,238,600,440],tex=4096,step=1),
      dict(id='04_Cybertruck_Straight',title='Cybertruck on the straight',subtitle='Static stainless-steel display grounded on the asphalt',pos=loc(501,315,4.0),focus=loc(489,325,1.05),fov=56,box=[459,294,514,355],tex=4096,step=1),
      dict(id='05_Cybertruck_Curve',title='Cybertruck on the bend',subtitle='Second truck follows the same circulation',pos=loc(582,399,4.5),focus=loc(567.5269,407.5269,1.30),fov=58,box=[532,368,596,435],tex=4096,step=1),
      dict(id='06_Full_Site',title='Motocross track and new oval',subtitle='Tested MX layout retained',pos=loc(718,510,305),focus=loc(395,288,0),fov=54,box=[145,75,600,465],tex=6144,step=1),
      dict(id='07_Start_Preserved',title='Tested start retained',subtitle='v036 terrain and riding surfaces unchanged',pos=loc(380,238,175),focus=loc(380,238,0),up=[1,0,0],fov=57,box=[295,145,475,302],tex=4096,step=1)]
    
def create_renderer(width,height):
    renderer=vtk.vtkRenderer();renderer.SetBackground(.66,.78,.88);renderer.SetBackground2(.31,.53,.72);renderer.GradientBackgroundOn();renderer.AutomaticLightCreationOff()
    window=getattr(vtk,os.environ.get('MEDIA_VTK_WINDOW','vtkOSOpenGLRenderWindow'))()
    window.SetOffScreenRendering(1);window.SetSize(width,height);window.SetMultiSamples(8);window.AddRenderer(renderer)
    sun=vtk.vtkLight();sun.SetLightTypeToSceneLight();sun.SetPosition(170,65,450);sun.SetFocalPoint(320,270,0);sun.SetColor(1.,.98,.94);sun.SetIntensity(.86);sun.PositionalOff();renderer.AddLight(sun)
    fill=vtk.vtkLight();fill.SetLightTypeToSceneLight();fill.SetPosition(590,420,280);fill.SetFocalPoint(320,270,0);fill.SetColor(.85,.92,1.);fill.SetIntensity(.24);fill.PositionalOff();renderer.AddLight(fill)
    # Contact shadows add depth without changing source geometry or materials.
    if os.environ.get('MEDIA_SSAO','1')=='1':
        base=vtk.vtkRenderStepsPass();ssao=vtk.vtkSSAOPass();ssao.SetDelegatePass(base);ssao.SetRadius(1.0);ssao.SetBias(.015);ssao.SetKernelSize(48);ssao.BlurOn();renderer.SetPass(ssao);KEEP.extend([base,ssao])
    KEEP.extend([renderer,window,sun,fill]);return renderer,window

def render_shot(renderer,window,shot,width,height):
    cam=renderer.GetActiveCamera();cam.SetPosition(*shot['pos']);cam.SetFocalPoint(*shot['focus']);cam.SetViewUp(*shot.get('up',[0,0,1]));cam.SetViewAngle(shot['fov'])
    distance=float(np.linalg.norm(np.asarray(shot['pos'])-shot['focus']));cam.SetClippingRange(max(.15,min(2.,distance/100)),1500)
    window.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.SetInputBufferTypeToRGB();capture.ReadFrontBufferOff();capture.Update()
    rgb=vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(height,width,3)[::-1]
    im=Image.fromarray(rgb.copy())
    # Small honest provenance label is retained on every public-facing render.
    overlay=Image.new('RGBA',im.size);draw=ImageDraw.Draw(overlay)
    fs=max(11,round(width/1920*19));label=SOURCE.name[:4].lower()+' SOURCE RENDER · NOT AN IN-GAME SCREENSHOT'
    f=font(fs);bbox=draw.textbbox((0,0),label,font=f);bw=bbox[2]+28;bh=fs+22
    draw.rounded_rectangle((width-bw-18,height-bh-16,width-18,height-16),radius=5,fill=(12,20,24,168))
    draw.text((width-bw-4,height-bh-8),label,font=f,fill=(242,243,241,235))
    im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    return im

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only');ap.add_argument('--width',type=int,default=2560);ap.add_argument('--height',type=int,default=1440);ap.add_argument('--draft',action='store_true');args=ap.parse_args()
    WORK.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);(OUT/'images').mkdir(exist_ok=True)
    baseline={p.name:digest(p) for p in [SOURCE/'scenery.fbx',SOURCE/'terrain.raw',SOURCE/'compiled_track.hmf']}
    start=time.time();renderer,window=create_renderer(args.width,args.height)
    actors,bounds=load_scenery()
    for a in actors:renderer.AddActor(a)
    manifest=[];terrain_cache={};background_cache={};selected=[s for s in shots() if not args.only or s['id'].startswith(tuple(args.only.split(',')))]
    for shot in selected:
        n=min(shot['tex'],1536) if args.draft else shot['tex'];key=tuple(shot['box'])+(n,shot['step'])
        if key not in terrain_cache:terrain_cache[key]=terrain_actor(shot['box'],n,shot['step'])
        for t in list(terrain_cache.values())+list(background_cache.values()):renderer.RemoveActor(t)
        if shot['box']!=[0,0,600,600]:
            bgkey=tuple(shot['box'])
            if bgkey not in background_cache:background_cache[bgkey]=terrain_actor([0,0,600,600],n=1536 if args.draft else 4096,step=4,cut_box=shot['box'])
            renderer.AddActor(background_cache[bgkey])
        renderer.AddActor(terrain_cache[key])
        log('Rendering '+shot['id']);im=render_shot(renderer,window,shot,args.width,args.height)
        file=OUT/'images'/(shot['id']+('_draft' if args.draft else '')+'.jpg');save_image(im,file,'JPEG',quality=95,subsampling=0,optimize=True)
        # Lossless masters for signs and memorial, preserving the actual art.
        if not args.draft:save_image(im,OUT/'images'/(shot['id']+'.png'),'PNG')
        manifest.append({**shot,'filename':file.name,'pixels':[args.width,args.height],'sha256':digest(file),'provenance':f'Actual {SOURCE.name[:4].lower()} FBX geometry/textures and native terrain source; external renderer; not an MX Bikes game capture.'})
        log(f'  Saved {file.name}, {file.stat().st_size/1e6:.2f} MB, elapsed {time.time()-start:.1f}s')
    assert baseline=={p.name:digest(p) for p in [SOURCE/'scenery.fbx',SOURCE/'terrain.raw',SOURCE/'compiled_track.hmf']},'Track source changed during read-only render'
    name='manifest'+('_draft' if args.draft else '')+('_'+args.only if args.only else '')+'.json'
    (OUT/name).write_text(json.dumps(dict(track_version=SOURCE.name[:4].lower(),source_sha256=baseline,track_sources_unchanged=True,renderer=vtk.vtkVersion.GetVTKVersion(),renders=manifest),indent=2)+'\n')
    log(f'Finished {len(manifest)} views in {time.time()-start:.1f}s. Track sources unchanged.')

if __name__=='__main__':main()

