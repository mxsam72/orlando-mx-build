"""Append source meshes and exact asset clones without changing baseline records."""
import copy, struct, zlib
from collections import Counter
import numpy as np
from v027_scenery import parse, encode, values, child, fingerprint, vertices, geometry_records
from rebind_scenery import array, encoded_array
from v037_common import *

def prop(v):
    if isinstance(v,bytes):return b'S'+struct.pack('<I',len(v))+v
    if isinstance(v,str):return prop(v.encode())
    if isinstance(v,int):return b'L'+struct.pack('<q',v)
    return b'D'+struct.pack('<d',float(v))
def node(name,*v,children=None):
    return dict(name=name.encode(),count=len(v),props=b''.join(prop(x) for x in v),children=children or [],sentinel=bytes(13) if children else b'')
def integer(name,v):
    return dict(name=name.encode(),count=1,props=b'I'+struct.pack('<i',v),children=[],sentinel=b'')
def arr(name,a,typ='d'):
    a=np.asarray(a,dtype='<f8' if typ=='d' else '<i4').ravel();b=zlib.compress(a.tobytes(),6)
    return dict(name=name.encode(),count=1,props=typ.encode()+struct.pack('<III',len(a),1,len(b))+b,children=[],sentinel=b'')
def setvalues(n,*v):n['count']=len(v);n['props']=b''.join(prop(x) for x in v)
def mapped_geometry(uid,m):
    vv=np.asarray(m['vertices'])*[100,100,-100];faces=np.asarray(m['faces'],dtype=np.int32)[:,::-1]
    pts=vv[faces];norm=np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0]);length=np.linalg.norm(norm,axis=1)
    assert np.all(length>1e-10),m['name'];norm/=length[:,None]
    inds=faces.copy();inds[:,-1]=-inds[:,-1]-1
    uv=np.asarray(m['uv'])[:,::-1,:].reshape(-1,2)
    def layer(kind,ref,data):
        return node('LayerElement'+kind,0,children=[integer('Version',101),node('Name','UVMap' if kind=='UV' else ''),node('MappingInformationType','AllSame' if kind=='Material' else 'ByPolygonVertex'),node('ReferenceInformationType',ref),*data])
    layers=[layer('Normal','Direct',[arr('Normals',np.repeat(norm,3,axis=0))]),layer('UV','IndexToDirect',[arr('UV',uv),arr('UVIndex',np.arange(len(uv)),'i')]),layer('Material','IndexToDirect',[arr('Materials',[0],'i')])]
    ld=node('Layer',0,children=[integer('Version',100),*[node('LayerElement',children=[node('Type','LayerElement'+k),integer('TypedIndex',0)]) for k in ['Normal','Material','UV']]])
    return node('Geometry',uid,m['name'].encode()+b'\x00\x01Geometry','Mesh',children=[integer('GeometryVersion',124),arr('Vertices',vv),arr('PolygonVertexIndex',inds,'i'),*layers,ld])

def append(meshes,clones,palette):
    original=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects');links=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    records={values(n)[0]:fingerprint(n) for n in objects['children']};connections=[fingerprint(n) for n in links['children']]
    byid={values(n)[0]:n for n in objects['children']};uid=max(byid)+1000
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'white',b'marker_white'])
    matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in links['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    mats={};texchecks=[]
    for name,rgb in palette.items():
        ids=[newid(),newid(),newid()];mats[name]=ids[0];fname='v037_'+name+'.tga';raw=(O/'facility_textures'/fname).read_bytes()
        for src,nid,kind in zip([base_mat,byid[texid],byid[vidid]],ids,['Material','Texture','Video']):
            n=copy.deepcopy(src);old=values(n);setvalues(n,nid,('v037_'+name).encode()+b'\x00\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                if c['name']==b'Media':setvalues(c,('v037_'+name).encode()+b'\x00\x01Video')
                if c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
                if c['name']==b'Properties70':
                    for p in c['children']:
                        v=values(p)
                        if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*v[:4],*(np.array(rgb)/255))
                        elif v and v[0]==b'Diffuse':setvalues(p,*v[:4],1.)
                        elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],fname)
            objects['children'].append(n)
        connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1]);texchecks.append(dict(texture=fname,sha256=sha(O/'facility_textures'/fname)))
    probes=[];entries=[]
    for m in meshes:
        gid,mid=newid(),newid();g=mapped_geometry(gid,m);model=copy.deepcopy(template);old=values(model);setvalues(model,mid,m['name'].encode()+b'\x00\x01Model',*old[2:])
        objects['children'] += [g,model];connect(gid,mid);connect(mats[m['material']],mid);connect(mid,0)
        v=np.asarray(m['vertices']);ix=sorted(set([0,len(v)//3,len(v)*2//3,len(v)-1]));probes += v[ix].tolist()
        entries.append(dict(name=m['name'],vertices=len(v),triangles=len(m['faces']),bounds_xyz_m=[v.min(0).tolist(),v.max(0).tolist()]))
    for part in clones:
        g=copy.deepcopy(part['geometry']);gid,mid=newid(),newid();old=values(g);setvalues(g,gid,part['name'].encode()+b'\x00\x01Geometry',*old[2:])
        child(g,b'Vertices')['props']=encoded_array(part['vertices']*[100,100,-100])
        for layer in g['children']:
            if layer['name']!=b'LayerElementNormal':continue
            nn=child(layer,b'Normals');norm=array(nn).reshape(-1,3)*[1,1,-1];norm=(norm@part['rotation'].T)*[1,1,-1];nn['props']=encoded_array(norm)
        model=copy.deepcopy(part['model']);mv=values(model);setvalues(model,mid,part['name'].encode()+b'\x00\x01Model',*mv[2:])
        objects['children'] += [g,model];connect(gid,mid);connect(part['material_id'],mid);connect(mid,0)
        probes.append(part['vertices'][0].tolist());v=part['vertices'];entries.append(dict(name=part['name'],vertices=len(v),bounds_xyz_m=[v.min(0).tolist(),v.max(0).tolist()]))
    counts=Counter(n['name'] for n in objects['children']);declared=[]
    for d in defs['children']:
        if d['name']!=b'ObjectType':continue
        typ=values(d)[0];extra=counts[typ]-sum(n['name']==typ for n in byid.values());ct=child(d,b'Count');old=values(ct)[0];ct['props']=b'I'+struct.pack('<i',old+extra);declared.append(old+extra)
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',sum(declared))
    out=encode(nodes,tail);atomic(O/'scenery.fbx',out)
    got,_=parse(out);assert encode(got,tail)==out
    newrecords={values(n)[0]:fingerprint(n) for n in next(n for n in got if n['name']==b'Objects')['children']}
    assert all(newrecords[k]==v for k,v in records.items())
    gotlinks=[fingerprint(n) for n in next(n for n in got if n['name']==b'Connections')['children']];assert gotlinks[:len(connections)]==connections
    rec=geometry_records(got)
    for m in meshes:assert np.allclose(vertices(rec[m['name']][0]),m['vertices'],rtol=0,atol=1e-10)
    for part in clones:assert np.allclose(vertices(rec[part['name']][0]),part['vertices'],rtol=0,atol=1e-10)
    qa=dict(checks_pass=True,baseline_records_retained_exact=len(records),baseline_connections_retained_exact=len(connections),baseline_geometry_count=len(geometry_records(parse(original)[0])),new_geometry_count=len(entries),total_geometry_count=len(rec),new_meshes=entries,new_textures=texchecks)
    save(O/'oval_scenery_validation.json',qa);save(O/'oval_native_probes.json',dict(expected_xyz_metres=probes));return qa
