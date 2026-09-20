#!/usr/bin/env python3
"""Bind existing scenery to the revised terrain and emit a small verified patch."""
from pathlib import Path
import base64,json,shutil,struct,zlib
import numpy as np
from scipy.ndimage import map_coordinates
from apply_scenery_patch import parse,encode,apply,digest,property_values

ROOT=Path(__file__).resolve().parents[1]
def values(n):return property_values(n['props'],n['count'])
def array(n):
    typ,count,data=values(n)[0]
    dtype={b'd':'<f8',b'i':'<i4',b'f':'<f4'}[typ]
    return np.frombuffer(data,dtype=dtype).copy()
def encoded_array(a):
    a=np.asarray(a,dtype='<f8').ravel();data=zlib.compress(a.tobytes(),6)
    return b'd'+struct.pack('<III',len(a),1,len(data))+data

def main():
    source=ROOT/'BUILD/v006_scenery.fbx'
    if not source.exists():shutil.copy2(ROOT/'07_OBJECTS_SOURCE/scenery.fbx',source)
    data=source.read_bytes();nodes,tail=parse(data)
    assert encode(nodes,tail)==data,'FBX round trip must be byte-identical before editing'
    objects=next(n for n in nodes if n['name']==b'Objects')
    connections=next(n for n in nodes if n['name']==b'Connections')
    models={values(n)[0]:values(n)[1].split(b'\x00')[0].decode() for n in objects['children'] if n['name']==b'Model'}
    bound={}
    for n in connections['children']:
        v=values(n)
        if len(v)>2 and v[2] in models:bound[v[1]]=models[v[2]]
    old=np.fromfile(ROOT/'BUILD/v006_terrain.raw',dtype='<u2').reshape(2049,2049)/65535*18
    new=np.fromfile(ROOT/'02_HEIGHTMAP/terrain.raw',dtype='<u2').reshape(2049,2049)/65535*18
    delta=new-old
    def ground_delta(x,z):return map_coordinates(delta,[(600-np.asarray(z))/600*2048,np.asarray(x)/600*2048],order=1,mode='nearest')
    original_props={}
    def walk(n,path):
        original_props[id(n)]=(path,n['props'])
        for i,c in enumerate(n['children']):walk(c,path+[i])
    for i,n in enumerate(nodes):walk(n,[i])
    replacements={};changes=[];probes=[];total_vertices=0
    def update(n,p):
        path,before=original_props[id(n)]
        replacements['/'.join(map(str,path))]=dict(before_sha256=digest(before),properties_base64=base64.b64encode(p).decode())
        n['props']=p
    for geom in objects['children']:
        if geom['name']!=b'Geometry':continue
        name=bound.get(values(geom)[0],'')
        vertex_node=next(n for n in geom['children'] if n['name']==b'Vertices')
        v=array(vertex_node).reshape(-1,3);original=v.copy();total_vertices+=len(v)
        # FBX uses centimetres and negative Z; native compiler flips Z.
        bottom=v[v[:,1]<v[:,1].min()+3.0]
        anchor=bottom[:,[0,2]].mean(0)/100
        if name.startswith('fence_rail_'):
            dy=ground_delta(v[:,0]/100,-v[:,2]/100)
        else:
            amount=float(ground_delta([anchor[0]],[-anchor[1]])[0]);dy=np.full(len(v),amount)
        if np.max(abs(dy))>.001:
            v[:,1]+=dy*100
            update(vertex_node,encoded_array(v))
            if name.startswith('fence_rail_'):
                inds=array(next(n for n in geom['children'] if n['name']==b'PolygonVertexIndex'))
                normals=[];face=[]
                for k in inds:
                    face.append(int(-k-1 if k<0 else k))
                    if k<0:
                        pts=v[face];normal=np.cross(pts[1]-pts[0],pts[2]-pts[0]);normal/=np.linalg.norm(normal)
                        normals.extend([normal.tolist()]*len(face));face=[]
                for layer in geom['children']:
                    if layer['name']!=b'LayerElementNormal':continue
                    mapping=next(values(n)[0] for n in layer['children'] if n['name']==b'MappingInformationType')
                    reference=next(values(n)[0] for n in layer['children'] if n['name']==b'ReferenceInformationType')
                    assert mapping==b'ByPolygonVertex' and reference in (b'Direct',b'IndexToDirect')
                    nn=next(n for n in layer['children'] if n['name']==b'Normals')
                    if reference==b'IndexToDirect':
                        ni=array(next(n for n in layer['children'] if n['name']==b'NormalsIndex'))
                        assert len(ni)==len(normals)
                        averaged=np.zeros_like(array(nn).reshape(-1,3))
                        np.add.at(averaged,ni,np.asarray(normals))
                        length=np.linalg.norm(averaged,axis=1)
                        valid=length>1e-8
                        averaged[valid]/=length[valid,None]
                        averaged[~valid]=array(nn).reshape(-1,3)[~valid]
                        update(nn,encoded_array(averaged))
                    else:
                        assert len(array(nn))==len(normals)*3
                        update(nn,encoded_array(normals))
            assert np.array_equal(v[:,[0,2]],original[:,[0,2]])
            changes.append(dict(model=name,vertices=len(v),minimum_shift_m=float(dy.min()),maximum_shift_m=float(dy.max())))
        if name.startswith('SOFTCPLAS_marker_') and len(probes)<40:
            probes.append([float(v[0,0]/100),float(v[0,1]/100),float(-v[0,2]/100)])
    patch=dict(source_fbx_sha256=digest(data),replacements=replacements)
    output=apply(data,patch);patch['result_fbx_sha256']=digest(output)
    assert apply(data,patch)==output
    (ROOT/'07_OBJECTS_SOURCE/scenery.fbx').write_bytes(output)
    (ROOT/'V007_SOURCE/scenery_patch.json').write_text(json.dumps(patch,separators=(',',':'))+'\n')
    (ROOT/'BUILD/native_coordinate_probes.json').write_text(json.dumps(dict(expected_xyz_metres=probes),indent=2)+'\n')
    qa=dict(source_fbx_sha256=patch['source_fbx_sha256'],result_fbx_sha256=patch['result_fbx_sha256'],
            unchanged_roundtrip_identical=True,modified_models=len(changes),total_vertices=total_vertices,
            topology_axes_materials_preserved=True,changes=changes,native_conversion=False)
    (ROOT/'DOCUMENTATION/v007_scenery_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps({k:v for k,v in qa.items() if k!='changes'},indent=2))

if __name__=='__main__':main()
