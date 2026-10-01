"""Append textured owner assets to the unchanged v018-derived facility FBX."""
import copy,struct
from PIL import Image
from append_facilities_v021 import node,integer,arr,child,values,setvalues,parse,encode,prop
from rebind_scenery import array
from v021_common import *

def geometry(mid,mesh):
    vv=np.asarray(mesh['vertices'])*[100,100,-100];inds=[];normals=[];uv=[]
    for face,coords in zip(mesh['faces'],mesh['uv']):
        f=list(reversed(face));p=vv[f];n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n);inds.extend(f[:-1]+[-f[-1]-1]);normals.extend([n]*len(f));uv.extend(list(reversed(coords)))
    def layer(kind,reference,data,name=''):
        return node('LayerElement'+kind,0,children=[integer('Version',101),node('Name',name),node('MappingInformationType','ByPolygonVertex' if kind!='Material' else 'AllSame'),node('ReferenceInformationType',reference),*data])
    layers=[
        layer('Normal','Direct',[arr('Normals',normals)]),
        layer('UV','IndexToDirect',[arr('UV',uv),arr('UVIndex',range(len(uv)),'i')],'UVMap'),
        layer('Material','IndexToDirect',[arr('Materials',[0],'i')])
    ]
    layerdef=node('Layer',0,children=[integer('Version',100),*[node('LayerElement',children=[node('Type','LayerElement'+k),integer('TypedIndex',0)]) for k in ['Normal','Material','UV']]])
    return node('Geometry',mid,mesh['name'].encode()+b'\x00\x01Geometry','Mesh',children=[integer('GeometryVersion',124),arr('Vertices',vv),arr('PolygonVertexIndex',inds,'i'),*layers,layerdef])

def main():
    assert read(R/'DOCUMENTATION/v021_vehicle_validation.json')['checks_pass']
    original=(O/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects');conns=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    old_objects=copy.deepcopy(objects['children']);old_connections=copy.deepcopy(conns['children']);byid={values(n)[0]:n for n in objects['children'] if n['count']}
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'marker_white',b'white']);matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in conns['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture');vidid=next(values(n)[1] for n in conns['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    uid=max(i for i in byid if isinstance(i,int))+1000
    def new_id():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,property=None):conns['children'].append(node('C','OP' if property else 'OO',a,b,*([property] if property else [])))
    materials=read(S/'vehicle_materials.json');mats={};textures=O/'facility_textures';checks=[]
    for name,info in materials.items():
        mi,ti,vi=new_id(),new_id(),new_id();mats[name]=mi;fname='v021_vehicle_'+name+'.tga';src=S/info['file'];assert sha(src)==info['sha256']
        source_im=Image.open(src).convert('RGB')
        assert source_im.width&(source_im.width-1)==0 and source_im.height&(source_im.height-1)==0,(name,source_im.size,'NPOT texture rejected by PiBoSo importer')
        source_im.save(textures/fname);raw=(textures/fname).read_bytes()
        for source,nid,kind in [(base_mat,mi,'Material'),(byid[texid],ti,'Texture'),(byid[vidid],vi,'Video')]:
            n=copy.deepcopy(source);old=values(n);setvalues(n,nid,('v021_vehicle_'+name).encode()+b'\x00\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                if c['name']==b'Media':setvalues(c,('v021_vehicle_'+name).encode()+b'\x00\x01Video')
                if c['name']==b'Content':c['props']=b'R'+struct.pack('<I',len(raw))+raw;c['count']=1
                if c['name']==b'Properties70':
                    uvset_found=False
                    for p in c['children']:
                        v=values(p)
                        if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*v[:4],*(np.array(info['rgb'])/255))
                        elif v and v[0]==b'Diffuse':setvalues(p,*v[:4],1.0)
                        elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],fname)
                        elif v and v[0]==b'UVSet':setvalues(p,*v[:4],'UVMap');uvset_found=True
                    if kind=='Texture' and not uvset_found:c['children'].append(node('P','UVSet','KString','','','UVMap'))
            objects['children'].append(n)
        connect(ti,mi,'DiffuseColor');connect(vi,ti);checks.append(dict(material=name,material_id=mi,texture_id=ti,video_id=vi,texture=fname,sha256=sha(textures/fname)))
    vehicle_meshes=read(O/'vehicle_meshes.json');sign_meshes=read(O/'sign_graphic_meshes.json')
    meshes=vehicle_meshes+sign_meshes;geoms={};probes=[]
    for mesh in meshes:
        gid,mid=new_id(),new_id();g=geometry(gid,mesh);m=copy.deepcopy(template);mv=values(m);setvalues(m,mid,mesh['name'].encode()+b'\x00\x01Model',*mv[2:]);objects['children'] += [g,m];connect(gid,mid);connect(mats[mesh['material']],mid);connect(mid,0);geoms[gid]=mesh
    for a in read(S/'vehicles.json')['assets']:
        part=next(m for m in meshes if m['asset']==a['id'] and m['material'] in ['dark','alloy','sam_paint','van_paint','cyber_steel','white','tire']);probes.append(np.asarray(part['vertices'])[0].tolist())
    for item in defs['children']:
        if item['name']==b'Count':item['props']=b'I'+struct.pack('<i',len(objects['children']))
        elif item['name']==b'ObjectType':child(item,'Count')['props']=b'I'+struct.pack('<i',sum(n['name']==values(item)[0] for n in objects['children']))
    out=encode(nodes,tail);verified,_=parse(out);objs=next(n for n in verified if n['name']==b'Objects')['children'];links=next(n for n in verified if n['name']==b'Connections')['children'];oid={values(n)[0]:n for n in objs}
    # Every pre-existing FBX object and connection survives byte-for-byte in its node data.
    assert objs[:len(old_objects)]==old_objects and links[:len(old_connections)]==old_connections
    for gid,mesh in geoms.items():
        g=oid[gid];assert np.allclose(array(child(g,'Vertices')).reshape(-1,3),np.asarray(mesh['vertices'])*[100,100,-100]);uv=array(child(child(g,'LayerElementUV'),'UV')).reshape(-1,3,2);assert np.allclose(uv,np.asarray(mesh['uv'])[:,::-1,:])
    for ck in checks:
        tex=oid[ck['texture_id']];assert values(child(tex,'RelativeFilename'))[0].decode()==ck['texture'];assert any(values(c)==[b'OP',ck['texture_id'],ck['material_id'],b'DiffuseColor'] for c in links)
        rgb=next(values(p)[4:7] for p in child(oid[ck['material_id']],'Properties70')['children'] if values(p)[0]==b'DiffuseColor');assert np.allclose(rgb,np.array(materials[ck['material']]['rgb'])/255)
        assert Image.open(textures/ck['texture']).size==(materials[ck['material']]['width'],materials[ck['material']]['height'])
    (O/'scenery.fbx').write_bytes(out);p=read(O/'native_coordinate_probes.json');p['expected_xyz_metres']+=probes;save(O/'native_coordinate_probes.json',p)
    qa=read(R/'DOCUMENTATION/v021_scenery_validation.json');qa.update(new_materials=qa['new_materials']+len(materials),vehicle_materials=len(materials),vehicle_meshes=len(vehicle_meshes),vehicle_triangles=sum(len(m['faces']) for m in vehicle_meshes),sign_graphic_meshes=len(sign_meshes),vehicle_texture_checks=checks,vehicle_uv_roundtrip_pass=True,preexisting_objects_unchanged=True,pre_vehicle_fbx_sha256=__import__('hashlib').sha256(original).hexdigest(),output_sha256=sha(O/'scenery.fbx'),coordinate_probes=len(p['expected_xyz_metres']));save(R/'DOCUMENTATION/v021_scenery_validation.json',qa)
    print('Appended',len(meshes),'vehicle/bike mesh parts; existing scenery retained; UV and texture wiring verified')
if __name__=='__main__':main()

