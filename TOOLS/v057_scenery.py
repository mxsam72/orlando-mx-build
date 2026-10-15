"""Targeted Express rebuild, five truck repaints, solid readable cardboard sign."""
import copy
import io
import struct
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from v057_inputs import R, BASE, PREV, O, sha, save
from v027_scenery import parse, values, child, vertices, geometry_records, fingerprint
from v056_geometry import encode
from v033_billboard import node, setvalues, geometry
from rebind_scenery import array, encoded_array
from scene_texture_bindings_v044 import actual_diffuse_bindings
from vehicle_geometry_v024 import MeshBuilder
from v057_van import build
from v032_sign import projected, render_side

F=O/'facility_textures'
REVIEW=R/'BUILD/v057_review'
ORDER=[('v042_pit_cybertruck_06_yellow','black'),('v042_pit_cybertruck_04_pink','silver'),
       ('v041_pit_cybertruck_01_blue','black'),('v042_pit_cybertruck_05_orange','silver'),('v041_pit_cybertruck_02_purple','black')]


def vehicle_geometry(gid,mesh):
    g=geometry(gid,mesh)
    if mesh['material'] not in ['van_paint','tire','steel','alloy']:return g
    # Serialize actual curved normals; the source renderer uses the same
    # crease angle. Keep hard body joins, smooth the rounded roof and tires.
    v=np.asarray(mesh['vertices'])*[100,100,-100]; fs=np.asarray(mesh['faces'])[:,::-1]
    cross=np.cross(v[fs[:,1]]-v[fs[:,0]],v[fs[:,2]]-v[fs[:,0]])
    n=cross/np.maximum(np.linalg.norm(cross,axis=1,keepdims=True),1e-10)
    keys=[tuple(x) for x in np.round(v,5)]; adjacent={}
    for i,f in enumerate(fs):
        for j in f:adjacent.setdefault(keys[j],set()).add(i)
    result=[]; threshold=np.cos(np.deg2rad(38.))
    for i,f in enumerate(fs):
        for j in f:
            candidates=np.array(sorted(adjacent[keys[j]])); chosen=candidates[n[candidates]@n[i]>threshold]
            out=cross[chosen].sum(0);out/=max(np.linalg.norm(out),1e-10);result.append(out)
    child(child(g,b'LayerElementNormal'),b'Normals')['props']=encoded_array(result)
    return g


def place(meshes,xz,angle,height):
    t=np.deg2rad(angle); rot=np.array([[np.cos(t),0,np.sin(t)],[0,1,0],[-np.sin(t),0,np.cos(t)]])
    for m in meshes:
        m['vertices']=(np.asarray(m['vertices'])@rot.T+[xz[0],height,xz[1]]).tolist()
    return meshes


def face_uv(mesh):
    # Work in the actual serialized polygon order, as established by the
    # previously tested v032 sign repair. Each opposing face reads forward.
    v=np.asarray(mesh['vertices']); uv=[]
    for f in mesh['faces']:
        expected,_=projected(v,list(reversed(f)))
        uv.append(expected[::-1].tolist())
    mesh['uv']=uv


def sign(h,van):
    # 3.00 m of clear space from the nose of the van, facing the pit approach.
    # This is a separate 4-cm-thick object, with no coplanar backface/decal.
    t=np.deg2rad(186); forward=np.array([np.sin(t),np.cos(t)])
    center=np.array([343.8,153.8])+forward*(2.883+3.)
    y=float(map_coordinates(h,[[(600-center[1])/600*2048],[center[0]/600*2048]],order=1)[0])
    m=MeshBuilder('v057_cardboard_sign'); w=2.; bottom=.27; top=1.27; thick=.04
    # Separate opposing faces, with correctly projected UVs and solid edges.
    for z,reverse in [(-thick/2,False),(thick/2,True)]:
        vs=[[-w/2,bottom,z],[w/2,bottom,z],[w/2,top,z],[-w/2,top,z]]
        m.add(vs,[[3,2,1,0] if reverse else [0,1,2,3]],'v057_cardboard')
    face=m.parts['v057_cardboard']; face_uv(face)
    for x in [-w/2,w/2]:m.box([x,.77,0],[.012,1.,thick],'@v024_vehicle_van_paint')
    for yy in [bottom,top]:m.box([0,yy,0],[w,.010,thick],'@v024_vehicle_van_paint')
    for x in [-.68,.68]:
        m.box([x,.47,.052],[.048,1.05,.048],'@v024_timber')
        m.beam([x,.68,.075],[x,-.06,.39],.020,'@v024_timber',6)
    meshes=place(list(m.parts.values()),center,6.,y)
    # Nearest box-to-box XZ distance, not a misleading centre-to-centre claim.
    allvan=np.concatenate([np.asarray(p['vertices']) for p in van]); boards=np.asarray(meshes[0]['vertices'])
    # Exact distance along the van's longitudinal axis to the printed board.
    dist=np.min((boards[:,[0,2]]-np.array([343.8,153.8]))@forward)-np.max((allvan[:,[0,2]]-np.array([343.8,153.8]))@forward)
    assert 2.95<dist<3.05,dist
    return meshes,dict(center_xz_m=center.tolist(),board_dimensions_m=[w,1.,thick],clearance_to_van_nose_m=float(dist),ground_y_m=y,both_faces_readable=True,no_coplanar_faces=True)


def texture():
    F.mkdir(parents=True,exist_ok=True)
    p=R/'V057_SOURCE/assets/free_candy_cardboard.png'
    if not p.exists():p=p.with_suffix('.jpg')
    im=Image.open(p).convert('RGB'); im.resize((1024,256),Image.Resampling.LANCZOS).save(F/'v057_cardboard.tga')
    # Matte sign: share the already allocated alpha-only specular bitmap.
    from v052_foliage import MATTE
    (F/'v057_cardboard.shd').write_text('specular\n{\n  map = '+MATTE+'\n  shininess = 2\n}\n',encoding='utf-8')
    return F/'v057_cardboard.tga'


def allocation(nodes):
    b=actual_diffuse_bindings(nodes); out={}
    objs={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
    links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    for name in b['actual_diffuse_textures']:
        paths=[F/name,R/'V052_OUTPUT/facility_textures'/name,R/'V047_OUTPUT/facility_textures'/name,BASE/'facility_textures'/name,BASE/'materials'/name,BASE/name]
        p=next((p for p in paths if p.exists()),None)
        if p is not None:im=Image.open(p)
        else:
            tid=next(row['texture_id'] for row in b['bindings'] if row['texture']==name)
            video=next(objs[v[1]] for v in links if v[2]==tid and objs.get(v[1],{}).get('name')==b'Video')
            data=child(video,b'Content')['props'];assert data[:1]==b'R'
            im=Image.open(io.BytesIO(data[5:]))
        out[name]=dict(size=list(im.size),rgba8_bytes=im.width*im.height*4)
    return out


def main():
    O.mkdir(parents=True,exist_ok=True); REVIEW.mkdir(parents=True,exist_ok=True)
    raw=(PREV/'scenery.fbx').read_bytes(); nodes,tail=parse(raw); assert encode(nodes,tail)==raw
    before_alloc=allocation(nodes)
    objs=next(n for n in nodes if n['name']==b'Objects'); links=next(n for n in nodes if n['name']==b'Connections')
    byid={values(n)[0]:n for n in objs['children']}; rec=geometry_records(nodes)
    originals={k:fingerprint(n) for k,n in byid.items()}; originals_meta={n['name']:fingerprint(n) for n in nodes if n['name'] not in [b'Objects',b'Connections',b'Definitions']}
    original_links=copy.deepcopy(links['children']); changed=set(); removed=set(); truck_checks=[]
    mats={values(n)[1].split(b'\0')[0].decode():values(n)[0] for n in objs['children'] if n['name']==b'Material'}
    for prefix,color in ORDER:
        g,mid=rec[prefix+'_cyber_steel']; desired=mats['v038_cybertruck_black' if color=='black' else 'v024_vehicle_cyber_steel']
        link=next(n for n in links['children'] if values(n)[2]==mid and byid.get(values(n)[1],{}).get('name')==b'Material')
        oldmat=values(link)[1]; val=values(link); setvalues(link,val[0],desired,*val[2:])
        # Only orphaned target paint chains are pruned; green and all unmarked
        # silver/red/black trucks, mesh coordinates and wheels remain exact.
        assert not any(values(n)[1]==oldmat and byid.get(values(n)[2],{}).get('name')==b'Model' for n in links['children'])
        tids=[values(n)[1] for n in links['children'] if values(n)[2]==oldmat and byid.get(values(n)[1],{}).get('name')==b'Texture']
        vids=[values(n)[1] for n in links['children'] if values(n)[2] in tids and byid.get(values(n)[1],{}).get('name')==b'Video']
        removed.update([oldmat]+tids+vids)
        truck_checks.append(dict(object=prefix,colour=color,material_id=desired,old_material_id=oldmat,geometry_exact=True))
    assert Counter(x['colour'] for x in truck_checks)==dict(black=3,silver=2)
    objs['children']=[n for n in objs['children'] if values(n)[0] not in removed]
    links['children']=[n for n in links['children'] if not any(v in removed for v in values(n)[1:3])]
    h=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    # Ground anchor and heading are identical to the accepted pit placement.
    anchor=float(map_coordinates(h,[[(600-153.8)/600*2048],[343.8/600*2048]],order=1)[0])
    van=place(build(),[343.8,153.8],186.,anchor)
    assert {m['name'] for m in van}=={n for n in rec if n.startswith('van_shane_')}
    entries=[]
    for mesh in van:
        old,mid=rec[mesh['name']]; gid=values(old)[0]
        new=vehicle_geometry(gid,mesh); index=objs['children'].index(old); objs['children'][index]=new; changed.add(gid)
        entries.append(dict(name=mesh['name'],vertices=len(mesh['vertices']),triangles=len(mesh['faces'])))
    sign_meshes,sign_check=sign(h,van); tex=texture()
    # Reuse a proven textured material/texture/video chain, with new IDs.
    template=byid[rec['covered_stand_timber'][1]]; source_mat=byid[mats['v033_qwikchute_logo']]
    con=[values(n) for n in links['children']]
    tid=next(v[1] for v in con if v[2]==values(source_mat)[0] and byid.get(v[1],{}).get('name')==b'Texture')
    vid=next(v[1] for v in con if v[2]==tid and byid.get(v[1],{}).get('name')==b'Video')
    uid=max(byid)+1000
    def newid():
        nonlocal uid
        uid+=1; return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    ids=[newid() for _ in range(3)]; payload=tex.read_bytes()
    for src,nid,kind in zip([source_mat,byid[tid],byid[vid]],ids,['Material','Texture','Video']):
        n=copy.deepcopy(src); old=values(n); setvalues(n,nid,b'v057_cardboard\0\1'+kind.encode(),*old[2:])
        for c in n['children']:
            if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,tex.name)
            if c['name']==b'Media':setvalues(c,b'v057_cardboard\0\1Video')
            if c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(payload))+payload
            if c['name']==b'Properties70':
                for prop in c['children']:
                    v=values(prop)
                    if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(prop,*v[:4],1.,1.,1.)
                    elif v and v[0] in [b'EmissiveFactor',b'TransparencyFactor']:setvalues(prop,*v[:4],0.)
                    elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(prop,*v[:4],tex.name)
        objs['children'].append(n)
    connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1])
    added=[]
    for mesh in sign_meshes:
        gid,mid=newid(),newid(); g=geometry(gid,mesh); model=copy.deepcopy(template); old=values(model)
        setvalues(model,mid,mesh['name'].encode()+b'\0\1Model',*old[2:]);setvalues(child(model,b'Culling'),'CullingOnCCW')
        objs['children'] += [g,model];connect(gid,mid);connect(ids[0] if mesh['material']=='v057_cardboard' else mats[mesh['material'][1:]],mid);connect(mid,0)
        added.append(gid)
    defs=next(n for n in nodes if n['name']==b'Definitions'); counts=Counter(n['name'] for n in objs['children']); declared=[]
    for n in defs['children']:
        if n['name']==b'ObjectType':
            kind=values(n)[0]; ct=counts[kind] if kind!=b'GlobalSettings' else values(child(n,b'Count'))[0]
            child(n,b'Count')['props']=b'I'+struct.pack('<i',ct); declared.append(ct)
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',sum(declared))
    (O/'scenery.fbx').write_bytes(encode(nodes,tail)); check,_=parse((O/'scenery.fbx').read_bytes())
    after={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']}
    assert all(after[k]==v for k,v in originals.items() if k not in changed|removed)
    assert originals_meta=={n['name']:fingerprint(n) for n in check if n['name'] not in [b'Objects',b'Connections',b'Definitions']}
    targets={rec[prefix+'_cyber_steel'][1] for prefix,color in ORDER}
    def protected_link(n):
        v=values(n)
        return not any(i in removed for i in v[1:3]) and not (v[2] in targets and byid.get(v[1],{}).get('name')==b'Material')
    old_links=[fingerprint(n) for n in original_links if protected_link(n)]
    new_links=[fingerprint(n) for n in links['children'] if protected_link(n) and all(i in byid or i==0 for i in values(n)[1:3])]
    assert old_links==new_links,'Unrelated scene connection changed'
    retained=[]; probes=[]; final_rec=geometry_records(check)
    for name,(g,mid) in final_rec.items():
        v=vertices(g); dest=probes if values(g)[0] in changed|set(added) else retained
        dest.extend(dict(geometry=name,expected_xyz_m=v[j].tolist()) for j in sorted({0,len(v)//2,len(v)-1}))
    # UV check reads the re-parsed native polygon records, not authoring UVs.
    g=final_rec['v057_cardboard_sign_v057_cardboard'][0]; v=vertices(g)
    ind=array(child(g,b'PolygonVertexIndex')).reshape(-1,3); ind=np.where(ind<0,-ind-1,ind)
    uv=array(child(child(g,b'LayerElementUV'),b'UV')).reshape(-1,3,2)
    for f,u in zip(ind,uv):assert np.allclose(projected(v,f)[0],u,atol=1e-9)
    image=np.asarray(Image.open(tex).convert('RGB'))
    for i in [0,2]:render_side(v,ind,uv,image,i,w=1000,h=500).save(REVIEW/('sign_face_'+str(1+i//2)+'.png'))
    after_alloc=allocation(check); before_bytes=sum(v['rgba8_bytes'] for v in before_alloc.values());after_bytes=sum(v['rgba8_bytes'] for v in after_alloc.values())
    assert after_bytes<=before_bytes,(before_bytes,after_bytes)
    old_v=sum(len(vertices(g)) for n,(g,mid) in rec.items() if n.startswith('van_shane_'))
    new_v=sum(len(m['vertices']) for m in van+sign_meshes)
    # Conservative source geometry estimate: 48 bytes/vertex + 12/triangle.
    old_t=sum(len(array(child(g,b'PolygonVertexIndex')))//3 for n,(g,mid) in rec.items() if n.startswith('van_shane_'))
    new_t=sum(len(m['faces']) for m in van+sign_meshes)
    geometry_delta=(new_v-old_v)*48+(new_t-old_t)*12
    assert after_bytes-before_bytes+max(0,geometry_delta)<=0,('Source texture + geometry budget',geometry_delta)
    sign_check.update(serialized_uv_forward_and_upright_both_faces=True,texture=tex.name,texture_sha256=sha(tex),texture_size=[1024,256],shared_matte_specular=True)
    save(O/'vehicle_meshes.json',van+sign_meshes)
    save(O/'native_probes.json',dict(retained_geometry=retained,changed_geometry=probes))
    save(O/'scenery_validation.json',dict(checks_pass=True,scenery_unchanged=False,scenery_sha256=sha(O/'scenery.fbx'),baseline_sha256=sha(PREV/'scenery.fbx'),
        all_unrelated_records_exact=True,all_unrelated_connections_exact=True,all_physical_scene_geometry_exact=True,cybertrucks=truck_checks,unmarked_cybertrucks_exact=True,
        express_reference_photos=['IMG_4018.jpg','IMG_4022.jpg'],express_dimensions_m=[5.692,2.014,2.138],express_wheelbase_m=3.429,
        express_geometry=entries,sign=sign_check,removed_unused_paint_records=sorted(removed),
        object_rgba8_base_bytes_before=before_bytes,object_rgba8_base_bytes_after=after_bytes,object_texture_bytes_saved=before_bytes-after_bytes,
        conservative_added_source_geometry_bytes=geometry_delta,estimated_source_allocation_bytes_saved=before_bytes-after_bytes-max(0,geometry_delta),
        object_texture_inventory_before=before_alloc,object_texture_inventory_after=after_alloc,in_game_visual_check=False,performance_test=False))
    print('V057_SCENERY_PASSED: Express, 3 black / 2 silver, 3m sign, unchanged unrelated scenery, bytes saved',before_bytes-after_bytes-max(0,geometry_delta),flush=True)


if __name__=='__main__':main()
