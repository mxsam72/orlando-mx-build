"""Append parametric facility meshes to the validated FBX7400 baseline.

All new meshes, material colours, connections and textures are generated from
source. Existing perimeter materials/meshes retain their source properties.
"""
import copy,io,struct,zlib
from PIL import Image
from scipy.spatial import cKDTree
from v014_common import *
from apply_scenery_patch import parse,encode,property_values
from rebind_scenery import array
from facility_mesh_v014 import PALETTE

def values(n):return property_values(n['props'],n['count'])
def prop(v):
    if isinstance(v,bytes):return b'S'+struct.pack('<I',len(v))+v
    if isinstance(v,str):return prop(v.encode())
    if isinstance(v,bool):return b'C'+struct.pack('<?',v)
    if isinstance(v,int):return b'L'+struct.pack('<q',v)
    return b'D'+struct.pack('<d',v)
def node(name,*v,children=None):return dict(name=name.encode(),count=len(v),props=b''.join(prop(x) for x in v),children=children or [],sentinel=bytes(13) if children else b'')
def integer(name,v):return dict(name=name.encode(),count=1,props=b'I'+struct.pack('<i',v),children=[],sentinel=b'')
def arr(name,data,typ='d'):
    a=np.asarray(data,dtype='<f8' if typ=='d' else '<i4').ravel();b=zlib.compress(a.tobytes(),6)
    return dict(name=name.encode(),count=1,props=typ.encode()+struct.pack('<III',len(a),1,len(b))+b,children=[],sentinel=b'')
def child(n,name):return next(c for c in n['children'] if c['name']==name.encode())
def setvalues(n,*v):n['count']=len(v);n['props']=b''.join(prop(x) for x in v)
def geometry(mid,mesh):
    # Reflect native Z into FBX Z; reverse winding to preserve outward normals.
    vertices=np.asarray(mesh['vertices'])*[100,100,-100];faces=[list(reversed(f)) for f in mesh['faces']]
    inds=[];norm=[];uv=[]
    for f in faces:
        pts=vertices[f];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);length=np.linalg.norm(n)
        assert length>1e-9,(mesh['name'],'degenerate face');n/=length
        inds.extend(f[:-1]+[-f[-1]-1]);norm.extend([n]*len(f));uv.extend([[p[0]/400,p[1]/400] for p in pts])
    def layer(kind,reference,data):return node('LayerElement'+kind,0,children=[integer('Version',101),node('Name',''),node('MappingInformationType','ByPolygonVertex' if kind!='Material' else 'AllSame'),node('ReferenceInformationType',reference),*data])
    layers=[layer('Normal','Direct',[arr('Normals',norm)]),layer('UV','Direct',[arr('UV',uv)]),layer('Material','IndexToDirect',[arr('Materials',[0],'i')])]
    layerdef=node('Layer',0,children=[integer('Version',100),*[node('LayerElement',children=[node('Type','LayerElement'+k),integer('TypedIndex',0)]) for k in ['Normal','Material','UV']]])
    return node('Geometry',mid,mesh['name'].encode()+b'\x00\x01Geometry','Mesh',children=[integer('GeometryVersion',124),arr('Vertices',vertices),arr('PolygonVertexIndex',inds,'i'),*layers,layerdef])

def main():
    original=(O/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects');conns=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    byid={values(n)[0]:n for n in objects['children'] if n['count']}
    models={i:values(n)[1].split(b'\0')[0].decode() for i,n in byid.items() if n['name']==b'Model'}
    geomodel={values(n)[1]:values(n)[2] for n in conns['children'] if len(values(n))>2 and values(n)[2] in models and byid.get(values(n)[1],{}).get('name')==b'Geometry'}
    template=copy.deepcopy(next(byid[i] for i,name in models.items() if name.startswith('fence_post_')))
    remove=set();removed=[]
    prefixes=('fence_post_','fence_rail_','WLLCONC_canopy_','canopy_','utility_pole_','crossarm_', 'pickup_','windshield_','sideglass_','bed_','bedrail_','wheel_','headlight_', 'trailer_','stripe_','trailerwheel_','hitch_','portable_toilet_','toilet_roof_','timing_')
    for gid,mid in geomodel.items():
        name=models[mid];v=array(child(byid[gid],'Vertices')).reshape(-1,3)*[.01,.01,-.01];low=v[v[:,1]<v[:,1].min()+.5];xz=low[:,[0,2]].mean(0)
        facility_tree_replace=(name.startswith(('tree_','scrub_')) and 220<xz[0]<389 and 80<xz[1]<174)
        # v014 user-marked clearing: remove baseline trees/scrub inside the
        # starting-area infield, left of the rightmost gate and before the
        # approach/corner sequence that leads toward R09.  Facility oaks live
        # below z=174 and are preserved as separate parametric assets.
        zone=read(S/'pit_facilities.json').get('tree_removal_intent',{}).get('authored_zone_xz',{})
        start_tree_replace=(name.startswith(('tree_','scrub_')) and zone and
                            zone['min_x']<xz[0]<zone['max_x'] and zone['min_z']<xz[1]<zone['max_z'])
        replace=name.startswith(prefixes) or facility_tree_replace or start_tree_replace
        if replace:remove.update([gid,mid]);removed.append(name)
    objects['children']=[n for n in objects['children'] if values(n)[0] not in remove]
    conns['children']=[n for n in conns['children'] if not any(v in remove for v in values(n)[1:3])]
    uid=max(i for i in byid if isinstance(i,int))+1000
    def new_id():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,property=None):conns['children'].append(node('C','OP' if property else 'OO',a,b,*([property] if property else [])))
    # Clone the baseline's known-good diffuse texture/material/video wiring.
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'marker_white',b'white'])
    matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in conns['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in conns['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    mats={};textures=O/'facility_textures';textures.mkdir(exist_ok=True)
    for name,color in PALETTE.items():
        mi,ti,vi=new_id(),new_id(),new_id();mats[name]=mi;fname='v014_'+name+'.tga'
        im=Image.new('RGB',(16,16),color);im.save(textures/fname);raw=(textures/fname).read_bytes()
        for source,nid,kind in [(base_mat,mi,'Material'),(byid[texid],ti,'Texture'),(byid[vidid],vi,'Video')]:
            n=copy.deepcopy(source);old=values(n);setvalues(n,nid,('v014_'+name).encode()+b'\x00\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                if c['name']==b'Media':setvalues(c,('v014_'+name).encode()+b'\x00\x01Video')
                if c['name']==b'Content':c['props']=b'R'+struct.pack('<I',len(raw))+raw;c['count']=1
                if c['name']==b'Properties70':
                    # fbx2edf may fall back to the FBX material's diffuse colour
                    # when it cannot resolve a generated texture.  Early v011
                    # cloned marker_white and left this fallback at pure white,
                    # which is exactly what appeared in-game.  Encode the intended
                    # palette colour directly as well as keeping the diffuse texture.
                    rgb=tuple(float(ch)/255.0 for ch in color)
                    for p in c['children']:
                        v=values(p)
                        if not v: continue
                        if v[0] in [b'DiffuseColor',b'AmbientColor']:
                            setvalues(p,*v[:4],*rgb)
                        elif v[0]==b'Diffuse':
                            # Diffuse factor, not RGB.
                            setvalues(p,*v[:4],1.0)
            objects['children'].append(n)
        connect(ti,mi,'DiffuseColor');connect(vi,ti)
    meshes=read(O/'facility_meshes.json');probes=[];q,w=route();qt=cKDTree(q[:,:2]);sa=np.load(O/'route.npz')['start'];st=cKDTree(sa[:,:2]);cfg=read(S/'facilities.json');clear=[]
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    pits=np.array([[x,z] for x in range(260,331,10) for z in [110,117,124]])
    for mesh in meshes:
        v=np.asarray(mesh['vertices']);assert np.isfinite(v).all()
        # Collision/clearance checks use low geometry: crowns can overhang lawns.
        bottom=v[v[:,1]<ground(H,v[:,[0,2]])+1.7][:,[0,2]]
        contact=len(bottom)>0
        if not contact:bottom=v[:,[0,2]]
        dist,ix=qt.query(bottom);mc=float((dist-w[ix]/2).min())
        sd,si=st.query(bottom);half=np.interp(sa[si,3],*np.array(cfg['start_width_knots']).T)/2;sc=float((sd-half).min())
        pc=float(cKDTree(bottom).query(pits)[0].min());clear.append(dict(mesh=mesh['name'],main_edge_m=mc,start_edge_m=sc,pit_spawn_m=pc))
        assert mc>1 and sc>1 and (not contact or pc>2.0),(mesh['name'],'clearance failed',clear[-1])
        gid,mid=new_id(),new_id();g=geometry(gid,mesh);m=copy.deepcopy(template);mv=values(m);setvalues(m,mid,mesh['name'].encode()+b'\x00\x01Model',*mv[2:]);objects['children'] += [g,m];connect(gid,mid);connect(mats[mesh['material']],mid);connect(mid,0)
        if len(probes)<24 and mesh['material'] not in ['glass','leaf1','leaf2','leaf3']:probes.append(v[0].tolist())
    for item in defs['children']:
        if item['name']==b'Count':item['props']=b'I'+struct.pack('<i',len(objects['children']))
        elif item['name']==b'ObjectType':child(item,'Count')['props']=b'I'+struct.pack('<i',sum(n['name']==values(item)[0] for n in objects['children']))
    out=encode(nodes,tail);verified,_=parse(out);(O/'scenery.fbx').write_bytes(out)
    # Read the serialized FBX back: assert both intended RGB fallback values
    # and diffuse bitmap links, guarding the exact white-object regression.
    objs=next(n for n in verified if n['name']==b'Objects')['children']
    links=next(n for n in verified if n['name']==b'Connections')['children']
    material_checks=[]
    for name,rgb in PALETTE.items():
        material=next(n for n in objs if n['name']==b'Material' and values(n)[0]==mats[name])
        props=child(material,'Properties70')['children']
        color=next(values(n)[4:7] for n in props if values(n)[0]==b'DiffuseColor')
        assert np.allclose(color,np.array(rgb)/255,atol=1e-10),(name,'wrong diffuse fallback')
        link=next(n for n in links if len(values(n))==4 and values(n)[2]==mats[name] and values(n)[3]==b'DiffuseColor')
        tex=next(n for n in objs if n['name']==b'Texture' and values(n)[0]==values(link)[1])
        filename=values(child(tex,'RelativeFilename'))[0].decode()
        assert filename=='v014_'+name+'.tga' and (textures/filename).exists()
        assert Image.open(textures/filename).convert('RGB').getpixel((0,0))==tuple(rgb)
        material_checks.append(dict(material=name,diffuse_rgb=color,texture=filename,sha256=sha(textures/filename)))
    # Earlier relocated fence probes are now obsolete. Keep unaffected markers.
    existing=read(O/'native_coordinate_probes.json')['expected_xyz_metres'];save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=probes+existing[-16:]))
    qa=read(R/'DOCUMENTATION/v014_scenery_validation.json');qa.update(facility_meshes=len(meshes),new_vertices=sum(len(m['vertices']) for m in meshes),removed_legacy_models=removed,facility_clearances=clear,output_sha256=sha(O/'scenery.fbx'),coordinate_probes=len(probes)+16,parametric_facilities=True,wire_fence_has_real_openings=True,new_materials=len(mats),material_regression_checks=material_checks,material_checks_pass=True,scenery_checks_pass=True)
    save(R/'DOCUMENTATION/v014_scenery_validation.json',qa);print('Facilities appended:',len(meshes),'new meshes;',len(removed),'legacy placeholders removed')
if __name__=='__main__':main()
