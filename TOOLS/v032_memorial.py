"""Append the approved two-sided Pup Whatley memorial without changing v030 objects."""
import copy, math, struct, zlib
from collections import Counter
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v032_common import *
from v027_scenery import parse, encode, values, child, fingerprint, geometry_records, vertices
from rebind_scenery import array
from v032_sign import projected

def prop(v):
    if isinstance(v, bytes): return b'S'+struct.pack('<I',len(v))+v
    if isinstance(v, str): return prop(v.encode())
    if isinstance(v, int): return b'L'+struct.pack('<q',v)
    return b'D'+struct.pack('<d',v)
def node(name,*v,children=None):
    return dict(name=name.encode(),count=len(v),props=b''.join(prop(x) for x in v),children=children or [],sentinel=bytes(13) if children else b'')
def integer(name,v): return dict(name=name.encode(),count=1,props=b'I'+struct.pack('<i',v),children=[],sentinel=b'')
def arr(name,data,typ='d'):
    a=np.asarray(data,dtype='<f8' if typ=='d' else '<i4').ravel();b=zlib.compress(a.tobytes(),6)
    return dict(name=name.encode(),count=1,props=typ.encode()+struct.pack('<III',len(a),1,len(b))+b,children=[],sentinel=b'')
def setvalues(n,*v): n['count']=len(v);n['props']=b''.join(prop(x) for x in v)
def ground(h,p):
    p=np.asarray(p);return map_coordinates(h,[(600-p[...,1])/600*2048,p[...,0]/600*2048],order=1,mode='nearest')

def geometry(mid,mesh):
    vv=np.asarray(mesh['vertices'])*[100,100,-100];inds=[];norm=[];uv=[]
    for face,coords in zip(mesh['faces'],mesh['uv']):
        f=list(reversed(face));p=vv[f];normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal)
        inds.extend(f[:-1]+[-f[-1]-1]);norm.extend([normal]*len(f));uv.extend(list(reversed(coords)))
    def layer(kind,reference,data,name=''):
        return node('LayerElement'+kind,0,children=[integer('Version',101),node('Name',name),node('MappingInformationType','ByPolygonVertex' if kind!='Material' else 'AllSame'),node('ReferenceInformationType',reference),*data])
    layers=[layer('Normal','Direct',[arr('Normals',norm)]),layer('UV','IndexToDirect',[arr('UV',uv),arr('UVIndex',range(len(uv)),'i')],'UVMap'),layer('Material','IndexToDirect',[arr('Materials',[0],'i')])]
    ld=node('Layer',0,children=[integer('Version',100),*[node('LayerElement',children=[node('Type','LayerElement'+k),integer('TypedIndex',0)]) for k in ['Normal','Material','UV']]])
    return node('Geometry',mid,mesh['name'].encode()+b'\x00\x01Geometry','Mesh',children=[integer('GeometryVersion',124),arr('Vertices',vv),arr('PolygonVertexIndex',inds,'i'),*layers,ld])

def make_meshes(h,cfg):
    origin=np.array([cfg['xz_m'][0],float(ground(h,[cfg['xz_m']])[0]),cfg['xz_m'][1]])
    theta=math.radians(cfg['heading_deg']);c,s=math.cos(theta),math.sin(theta);rotation=np.array([[c,-s],[s,c]])
    meshes={}
    def add(v,faces,material):
        v=np.array(v,float);v[:,[0,2]]=v[:,[0,2]]@rotation;v+=origin
        m=meshes.setdefault(material,dict(name=cfg['asset_id']+'_'+material,asset=cfg['asset_id'],material=material,vertices=[],faces=[],uv=[]))
        offset=len(m['vertices']);m['vertices'].extend(v.tolist())
        for f in faces:
            m['faces'].append([i+offset for i in f])
            # Match the proven entry-sign projection in serialized native winding.
            if material=='memorial': coords=projected(v,list(reversed(f)))[0][::-1].tolist()
            else: coords=[[v[i,0]/4,v[i,1]/4] for i in f]
            m['uv'].append(coords)
    def box(center,dim,material):
        v=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])*np.array(dim)/2+center
        add(v,[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]],material)
    w=cfg['image_width_m'];height=cfg['image_height_m'];lo=cfg['image_lower_edge_above_ground_m'];hi=lo+height;b=cfg['frame_border_m'];d=cfg['board_depth_m']
    box([0,(lo+hi)/2,0],[w,height,d],'frame')
    for y in [lo-b/2,hi+b/2]:box([0,y,0],[w+2*b,b,.34],'frame')
    for x in [-w/2-b/2,w/2+b/2]:box([x,(lo+hi)/2,0],[b,height,.34],'frame')
    for x in [-3.3,0,3.3]:
        p=(np.array([x,0])@rotation)+origin[[0,2]];g=float(ground(h,[p])[0])-origin[1]
        box([x,(hi+b+g)/2,0],[.24,hi+b-g,.24],'frame')
        box([x,g+.09,0],[.62,.18,.7],'concrete')
    z=d/2+.004
    add([[-w/2,lo,-z],[w/2,lo,-z],[w/2,hi,-z],[-w/2,hi,-z],[-w/2,lo,z],[w/2,lo,z],[w/2,hi,z],[-w/2,hi,z]],[[0,3,2],[0,2,1],[4,5,6],[4,6,7]],'memorial')
    return list(meshes.values()),origin

def clearances(meshes,h):
    v=np.concatenate([np.asarray(m['vertices']) for m in meshes]);xz=v[:,[0,2]]
    # Densely sample the full footprint rather than checking only corner vertices.
    grid=np.array([[x,z] for x in np.linspace(xz[:,0].min(),xz[:,0].max(),100) for z in np.linspace(xz[:,1].min(),xz[:,1].max(),12)])
    d=dict(np.load(O/'route.npz'));cfg=read(R/'V024_SOURCE/facilities.json');checks={}
    for name,q,width in [('main',d['q'],d['width']),('start',d['start'],np.interp(d['start'][:,3],*np.array(cfg['start_width_knots']).T))]:
        dist,i=cKDTree(q[:,:2]).query(grid);edge=dist-width[i]/2;checks[name+'_edge_clearance_m']=float(edge.min());assert edge.min()>3
    pits=read(R/'V016_SOURCE/pit_facilities.json');roadchecks=[]
    for road in pits['roads']:
        p=np.array(road['points']);dist=np.full(len(grid),np.inf)
        for a,b in zip(p[:-1],p[1:]):
            t=np.clip((grid-a)@(b-a)/np.dot(b-a,b-a),0,1);dist=np.minimum(dist,np.linalg.norm(grid-a-t[:,None]*(b-a),axis=1))
        edge=float(dist.min()-road['width']/2);assert edge>2;roadchecks.append(edge)
    checks['pit_road_edge_clearance_m']=min(roadchecks)
    spawn=np.array([[260+col*10,110+row*7] for row in range(3) for col in range(8)])
    checks['nearest_pit_spawn_m']=float(cKDTree(grid).query(spawn)[0].min());assert checks['nearest_pit_spawn_m']>4
    newlo=v.min(0);newhi=v.max(0);nodes,_=parse((O/'scenery.fbx').read_bytes());near=[]
    for name,(g,_) in geometry_records(nodes).items():
        old=vertices(g);delta=np.maximum(np.maximum(old.min(0)-newhi,newlo-old.max(0)),0);gap=float(np.linalg.norm(delta))
        assert gap>.25,(name,'memorial intersects existing scenery',gap)
        if gap<12:near.append(dict(mesh=name,bounds_gap_m=gap))
    checks['nearby_object_clearances']=sorted(near,key=lambda x:x['bounds_gap_m']);checks['checks_pass']=True
    return checks

def append(meshes,textures):
    original=(O/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects');conns=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    oldrecords={values(n)[0]:fingerprint(n) for n in objects['children']};oldlinks=[fingerprint(n) for n in conns['children']]
    byid={values(n)[0]:n for n in objects['children']};uid=max(i for i in byid if isinstance(i,int))+1000
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,property=None):conns['children'].append(node('C','OP' if property else 'OO',a,b,*([property] if property else [])))
    template=next(n for n in objects['children'] if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'marker_white',b'white']);matid=values(base)[0]
    texid=next(values(n)[1] for n in conns['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in conns['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    mats={};texchecks=[]
    for material in sorted(textures):
        path,rgb=textures[material];raw=path.read_bytes();fname=path.name;mi,ti,vi=newid(),newid(),newid();mats[material]=mi
        for src,nid,kind in [(base,mi,'Material'),(byid[texid],ti,'Texture'),(byid[vidid],vi,'Video')]:
            n=copy.deepcopy(src);old=values(n);setvalues(n,nid,('v032_'+material).encode()+b'\x00\x01'+kind.encode(),*old[2:])
            for item in n['children']:
                if item['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(item,fname)
                if item['name']==b'Media':setvalues(item,('v032_'+material).encode()+b'\x00\x01Video')
                if item['name']==b'Content':item['props']=b'R'+struct.pack('<I',len(raw))+raw;item['count']=1
                if item['name']==b'Properties70':
                    for p in item['children']:
                        val=values(p)
                        if val and val[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*val[:4],*(np.array(rgb)/255))
                        elif val and val[0]==b'Diffuse':setvalues(p,*val[:4],1.)
                        elif val and val[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*val[:4],fname)
            objects['children'].append(n)
        connect(ti,mi,'DiffuseColor');connect(vi,ti);texchecks.append(dict(material=material,texture=fname,size_px=list(Image.open(path).size),sha256=sha(path)))
    for mesh in meshes:
        gid,mid=newid(),newid();g=geometry(gid,mesh);m=copy.deepcopy(template);mv=values(m);setvalues(m,mid,mesh['name'].encode()+b'\x00\x01Model',*mv[2:]);objects['children'] += [g,m];connect(gid,mid);connect(mats[mesh['material']],mid);connect(mid,0)
    additions=Counter(n['name'] for n in objects['children'] if values(n)[0] not in oldrecords)
    for item in defs['children']:
        if item['name']==b'Count':item['props']=b'I'+struct.pack('<i',values(item)[0]+sum(additions.values()))
        elif item['name']==b'ObjectType' and additions[values(item)[0]]:
            c=child(item,b'Count');c['props']=b'I'+struct.pack('<i',values(c)[0]+additions[values(item)[0]])
    output=encode(nodes,tail);again,_=parse(output);objs=next(n for n in again if n['name']==b'Objects')['children'];links=next(n for n in again if n['name']==b'Connections')['children']
    assert {values(n)[0]:fingerprint(n) for n in objs if values(n)[0] in oldrecords}==oldrecords
    assert [fingerprint(n) for n in links[:len(oldlinks)]]==oldlinks
    records=geometry_records(again);uvchecks=[]
    for mesh in meshes:
        g=records[mesh['name']][0];assert np.allclose(vertices(g),mesh['vertices'],atol=1e-10)
        uv=array(child(child(g,b'LayerElementUV'),b'UV'));assert np.array_equal(uv,np.asarray([list(reversed(c)) for c in mesh['uv']]).ravel())
        if mesh['material']=='memorial':
            uv=uv.reshape(4,3,2);v=vertices(g)
            for i,f in enumerate(mesh['faces']):
                expected,normal=projected(v,list(reversed(f)));assert np.allclose(uv[i],expected,atol=1e-10)
                uvchecks.append(dict(triangle=i,normal=normal.tolist(),horizontal_and_vertical_readable=True))
    atomic(O/'scenery.fbx',output)
    probes=read(O/'native_coordinate_probes.json');newprobes=[]
    for mesh in meshes:
        v=np.asarray(mesh['vertices']);newprobes+=v[[0,len(v)//2,-1]].tolist()
    probes['expected_xyz_metres']+=newprobes;save(O/'native_coordinate_probes.json',probes);save(O/'memorial_native_probes.json',dict(expected_xyz_metres=newprobes))
    return dict(retained_v030_objects_after_entry_uv_fix_byte_exact=True,retained_connections_byte_exact=True,added_object_records={k.decode():v for k,v in additions.items()},new_textures=texchecks,mesh_roundtrip_checks_pass=True,both_faces_readable_in_native_projection=True,uv_projection_checks=uvchecks,new_coordinate_probes=len(newprobes))

def main():
    cfg=read(S/'memorial_spec.json');source=S/'pup_whatley_memorial.png';assert sha(source)==cfg['approved_image_sha256']
    im=Image.open(source).convert('RGB');assert list(im.size)==cfg['approved_image_size_px'];assert abs(cfg['image_width_m']/cfg['image_height_m']-im.width/im.height)<1e-10
    folder=O/'facility_textures';folder.mkdir(exist_ok=True);path=folder/'v032_pup_whatley_memorial.tga'
    image_file(im.resize(cfg['texture_size_px'],Image.Resampling.LANCZOS),path)
    textures={'memorial':(path,(255,255,255))}
    for material,rgb in [('frame',(43,45,47)),('concrete',(145,143,137))]:
        p=folder/('v032_memorial_'+material+'.tga');image_file(Image.new('RGB',(32,32),rgb),p);textures[material]=(p,rgb)
    h=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18;meshes,origin=make_meshes(h,cfg);clear=clearances(meshes,h)
    save(O/'memorial_meshes.json',meshes);qa=append(meshes,textures);qa.update(checks_pass=True,approved_image_sha256=sha(source),approved_image_content_unchanged=True,artwork_size_m=[cfg['image_width_m'],cfg['image_height_m']],approved_source_size_px=list(im.size),native_texture_size_px=cfg['texture_size_px'],resampling_does_not_add_source_detail=True,texture_resampling='Lanczos, uncropped approved art; physical mesh restores original aspect ratio',ground_anchor_xyz_m=origin.tolist(),lower_edge_above_ground_m=cfg['image_lower_edge_above_ground_m'],top_above_ground_m=cfg['image_lower_edge_above_ground_m']+cfg['image_height_m'],clearances=clear,mesh_count=len(meshes),vertices=sum(len(m['vertices']) for m in meshes),in_game_visual_check=False)
    save(O/'memorial_validation.json',qa);print('Large two-sided memorial appended; v030 records, road access and native UVs verified.',flush=True)
if __name__=='__main__':main()
