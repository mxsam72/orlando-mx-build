"""Add the behind-gate shaded bay, rails and practice entry to fixed scenery."""
import copy, math, struct
from collections import Counter
from PIL import Image
from facility_mesh_v016 import Scene, PALETTE
from append_facilities_v016 import node, integer, arr, prop, setvalues, geometry
from v027_scenery import parse, encode, values, child, fingerprint, geometry_records, vertices
from v028_common import *

def rails(s,points,name,material='timber',height=1.25):
    path=sample_polyline(points,2.8)
    for k,p in enumerate(path):
        s.asset(name,p[:2]); s.box([0,height/2,0],[.14,height,.14],material)
        if k==0:continue
        a=path[k-1,:2];b=p[:2];mid=(a+b)/2; length=np.linalg.norm(b-a)
        s.asset(name,mid,math.degrees(math.atan2(-(b[1]-a[1]),b[0]-a[0])))
        for y in ([.30,.72,height-.12] if material=='timber' else [.4,height-.12]):s.box([0,y,0],[length,.13,.10],material)
        if material=='alloy':
            for x in np.arange(-length/2+.18,length/2,.35):s.box([x,.7,0],[.035,.86,.035],material)

def meshes(h,cfg):
    s=Scene(h); data=dict(np.load(O/'route.npz')); a=access_layout(data['start'],cfg); parallel=a['parallel']
    for k,oak in enumerate(cfg['oak_assets']):
        s.asset(oak['id'],oak['xz']); radius=oak['radius']
        s.beam([0,0,0],[.16,5.1,-.12],.43,'bark',12)
        for j in range(9):
            theta=j*math.tau/9+.25;cx=math.cos(theta)*radius*.48;cz=math.sin(theta)*radius*.48;cy=6.4+(j%3)*.55
            s.beam([.1,3.7,0],[cx,cy,cz],.16 if j%2 else .22,'bark',9)
            # High underside gives usable oak shade over the staging area.
            s.crown([cx,cy+1.0,cz],radius*.55,'leaf'+str(1+j%3),270+k*19+j)
    for p in cfg['staging_assets']:
        s.asset(p['id'],p['xz'],p['heading'])
        if p['type']=='table':
            s.box([0,.77,0],[2.2,.10,.82],'timber')
            for x in [-.83,.83]:
                for z in [-.28,.28]:s.beam([x,0,z],[x,.75,z],.035,'alloy',6)
        elif p['type']=='bike_stand':
            s.box([0,.43,0],[.48,.06,.48],'rubber')
            for x in [-.2,.2]:
                for z in [-.2,.2]:s.beam([x*.8,.42,z*.8],[x,0,z],.028,'alloy',6)
        else:
            # Keep the existing accepted facility primitive style for added
            # background vehicles, without moving the user's custom vehicles.
            from facility_mesh_v016 import build
            parts=build(h,{'assets':[dict(p,heading=p.get('heading',0))],'fence_opening_station_m':[0,0]}, {'fence_polyline_xz':[[0,0],[.01,0]]})
            for part in parts:
                if part['asset']==p['id']: s.meshes[(part['asset'],part['material'])]=part
    rails(s,cfg['back_rail_points_xz_m'],'v028_staging_back_rail')
    ranges=[('v028_practice_wood_left',cfg['wood_fence_start_station_range_m'],'timber',1),
            ('v028_practice_barrier_left',cfg['barrier_start_station_range_m'],'alloy',1),
            ('v028_practice_barrier_right',cfg['barrier_start_station_range_m'],'alloy',-1)]
    for name,(begin,end),material,side in ranges:
        ss=np.linspace(begin,end,max(3,int((end-begin)/1.0)))
        p=np.c_[np.interp(ss,parallel[:,2],parallel[:,0]),np.interp(ss,parallel[:,2],parallel[:,1])]
        th=np.arctan2(np.gradient(p[:,1]),np.gradient(p[:,0]))
        p+=side*cfg['fence_half_offset_m']*np.c_[-np.sin(th),np.cos(th)]
        if side==1:
            # Follow the actual accepted clay edge, not the practice path's
            # tangent: changing start width otherwise pulls a rail inward.
            start=data['start'];knots=np.asarray(read(R/'V024_SOURCE/facilities.json')['start_width_knots'])
            th=np.interp(ss,start[:,3],start[:,2]);half=np.interp(ss,knots[:,0],knots[:,1])/2
            edge=half+cfg['fence_clay_edge_gap_m']
            p=np.c_[np.interp(ss,start[:,3],start[:,0])+np.sin(th)*edge,np.interp(ss,start[:,3],start[:,1])-np.cos(th)*edge]
        rails(s,p,name,material)
    parts=list(s.meshes.values())
    vehicle_meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')
    originals={p['id']:p for p in read(R/'V024_SOURCE/vehicles.json')['assets']}
    oldh=np.fromfile(R/'V026_OUTPUT/terrain.raw','<u2').reshape(N,N)/65535*SCALE
    for bike in cfg.get('staging_bikes',[]):
        source=originals[bike['reference_asset']];oldxz=np.array(source['xz']);newxz=np.array(bike['xz'])
        theta=math.radians(bike['heading']-source['heading']);c,ss=math.cos(theta),math.sin(theta)
        for mesh in vehicle_meshes:
            if mesh['asset']!=bike['reference_asset']:continue
            m=copy.deepcopy(mesh);v=np.asarray(m['vertices']);v[:,[0,2]]=(v[:,[0,2]]-oldxz)@np.array([[c,-ss],[ss,c]])+newxz
            v[:,1]+=float(ground(h,[newxz])[0]-ground(oldh,[oldxz])[0])+bike['wheel_lift_m']
            m.update(name=bike['id']+'_'+m['material'],asset=bike['id'],material='reuse_'+m['material'],vertices=v.tolist())
            parts.append(m)
    return parts,a

def mapped_geometry(mid,mesh):
    vv=np.asarray(mesh['vertices'])*[100,100,-100];inds=[];norm=[];uv=[]
    for face,coords in zip(mesh['faces'],mesh['uv']):
        f=list(reversed(face));p=vv[f];normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal)
        inds.extend(f[:-1]+[-f[-1]-1]);norm.extend([normal]*len(f));uv.extend(list(reversed(coords)))
    def layer(kind,reference,data,name=''):
        return node('LayerElement'+kind,0,children=[integer('Version',101),node('Name',name),node('MappingInformationType','ByPolygonVertex' if kind!='Material' else 'AllSame'),node('ReferenceInformationType',reference),*data])
    layers=[layer('Normal','Direct',[arr('Normals',norm)]),layer('UV','IndexToDirect',[arr('UV',uv),arr('UVIndex',range(len(uv)),'i')],'UVMap'),layer('Material','IndexToDirect',[arr('Materials',[0],'i')])]
    ld=node('Layer',0,children=[integer('Version',100),*[node('LayerElement',children=[node('Type','LayerElement'+k),integer('TypedIndex',0)]) for k in ['Normal','Material','UV']]])
    return node('Geometry',mid,mesh['name'].encode()+b'\x00\x01Geometry','Mesh',children=[integer('GeometryVersion',124),arr('Vertices',vv),arr('PolygonVertexIndex',inds,'i'),*layers,ld])

def clearance(meshes,h,a,cfg):
    d=dict(np.load(O/'route.npz')); q=d['q']; start=d['start']; fc=read(R/'V024_SOURCE/facilities.json')
    knots=np.asarray(fc['start_width_knots']); width=np.interp(start[:,3],knots[:,0],knots[:,1]);checks=[]
    lane=a['lane']; connector=a['connector']
    for m in meshes:
        v=np.asarray(m['vertices']); assert np.isfinite(v).all()
        low=v[v[:,1]-ground(h,v[:,[0,2]])<cfg['minimum_rider_headroom_m']]
        ck=dict(mesh=m['name'],low_vertices=len(low))
        for name,line,w,open_line in [('main',q,d['width'],False),('race_start',start,width,True),('practice',lane,None,True),('pit_connector',connector,None,True)]:
            if not len(low):ck[name+'_edge_clearance_m']=None;continue
            dist,lat,st,half,valid=route_projection(low[:,[0,2]],line,w,open_line)
            edge=dist-half; edge[~valid]=1000
            ck[name+'_edge_clearance_m']=float(edge.min())
            minimum=cfg['minimum_race_start_fence_edge_clearance_m'] if name=='race_start' else cfg['minimum_new_low_mesh_route_edge_clearance_m']
            assert edge.min()>minimum,(m['name'],name,'low-mesh corridor intrusion',float(edge.min()))
        checks.append(ck)
    return checks

def append(meshes):
    original=(O/'scenery.fbx').read_bytes(); nodes,tail=parse(original); assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects'); conns=next(n for n in nodes if n['name']==b'Connections'); defs=next(n for n in nodes if n['name']==b'Definitions')
    old_records={values(n)[0]:fingerprint(n) for n in objects['children']};old_links=[fingerprint(n) for n in conns['children']]
    byid={values(n)[0]:n for n in objects['children']}; uid=max(i for i in byid if isinstance(i,int))+1000
    def newid():
        nonlocal uid; uid+=1;return uid
    def connect(a,b,property=None):conns['children'].append(node('C','OP' if property else 'OO',a,b,*([property] if property else [])))
    template=next(n for n in objects['children'] if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'marker_white',b'white']); matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in conns['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in conns['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    used=sorted({m['material'] for m in meshes}); mats={}; texchecks=[]; textures=O/'facility_textures'; textures.mkdir(exist_ok=True)
    for name in used:
        if name.startswith('reuse_'):
            material=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==('v024_vehicle_'+name.removeprefix('reuse_')).encode())
            mats[name]=values(material)[0]
            continue
        rgb=PALETTE[name]; mi,ti,vi=newid(),newid(),newid();mats[name]=mi
        fname='v028_'+('TREE_' if name.startswith('leaf') else '')+name+'.tga'; n=256
        yy,xx=np.meshgrid(np.arange(n)/n,np.arange(n)/n,indexing='ij')
        # Fine reusable grain; form and shade come from the actual oak meshes.
        grain=np.sin(2*np.pi*(xx*7+yy*3))*1.8+np.sin(2*np.pi*(xx*23-yy*11))*1.2
        if name in ['timber','bark']:grain+=np.sin(2*np.pi*xx*31+.25*np.sin(2*np.pi*yy*3))*3
        im=np.uint8(np.rint(np.clip(np.array(rgb)+grain[...,None],0,255)));Image.fromarray(im).save(textures/fname);raw=(textures/fname).read_bytes()
        for source,nid,kind in [(base_mat,mi,'Material'),(byid[texid],ti,'Texture'),(byid[vidid],vi,'Video')]:
            n=copy.deepcopy(source); old=values(n);setvalues(n,nid,('v028_'+name).encode()+b'\x00\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                if c['name']==b'Media':setvalues(c,('v028_'+name).encode()+b'\x00\x01Video')
                if c['name']==b'Content':c['props']=b'R'+struct.pack('<I',len(raw))+raw;c['count']=1
                if c['name']==b'Properties70':
                    for p in c['children']:
                        v=values(p)
                        if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*v[:4],*(np.array(rgb)/255))
                        elif v and v[0]==b'Diffuse':setvalues(p,*v[:4],1.)
                        elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],fname)
            objects['children'].append(n)
        connect(ti,mi,'DiffuseColor');connect(vi,ti);texchecks.append(dict(material=name,texture=fname,sha256=sha(textures/fname)))
    probes=[]
    for mesh in meshes:
        gid,mid=newid(),newid();g=mapped_geometry(gid,mesh) if 'uv' in mesh else geometry(gid,mesh);m=copy.deepcopy(template);mv=values(m);setvalues(m,mid,mesh['name'].encode()+b'\x00\x01Model',*mv[2:])
        objects['children'] += [g,m];connect(gid,mid);connect(mats[mesh['material']],mid);connect(mid,0)
        if not mesh['material'].startswith('leaf'):probes.append(mesh['vertices'][0])
    additions=Counter(n['name'] for n in objects['children'] if values(n)[0] not in old_records)
    for item in defs['children']:
        if item['name']==b'Count':item['props']=b'I'+struct.pack('<i',values(item)[0]+sum(additions.values()))
        elif item['name']==b'ObjectType' and additions[values(item)[0]]:
            c=child(item,b'Count');c['props']=b'I'+struct.pack('<i',values(c)[0]+additions[values(item)[0]])
    output=encode(nodes,tail); check,_=parse(output); objects2=next(n for n in check if n['name']==b'Objects')['children']; conns2=next(n for n in check if n['name']==b'Connections')['children']
    assert {values(n)[0]:fingerprint(n) for n in objects2 if values(n)[0] in old_records}==old_records
    assert [fingerprint(n) for n in conns2[:len(old_links)]]==old_links
    names=geometry_records(check);assert all(m['name'] in names for m in meshes)
    from rebind_scenery import array
    for m in meshes:
        g=names[m['name']][0];assert np.allclose(vertices(g),m['vertices'],atol=1e-10)
        if 'uv' in m:
            u=array(child(child(g,b'LayerElementUV'),b'UV')).reshape(-1,3,2)
            assert np.allclose(u,np.asarray(m['uv'])[:,::-1,:])
    (O/'scenery.fbx').write_bytes(output);old=read(O/'native_coordinate_probes.json');old['expected_xyz_metres']+=probes;save(O/'native_coordinate_probes.json',old)
    return dict(retained_scenery_records_byte_exact=True,retained_connections_byte_exact=True,
                new_mesh_vertex_roundtrip_checks_pass=True,definition_counts_updated_by_delta=True,
                added_object_records=dict((k.decode(),v) for k,v in additions.items()),
                new_textures=texchecks,scenery_sha256=sha(O/'scenery.fbx'),new_coordinate_probes=len(probes))

def main():
    cfg=read(S/'pit_access.json');h=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    parts,a=meshes(h,cfg);checks=clearance(parts,h,a,cfg);save(O/'pit_facility_meshes.json',parts)
    qa=append(parts);qa.update(checks_pass=True,clearance_checks=checks,meshes=len(parts),vertices=sum(len(m['vertices']) for m in parts),
          practice_lane_length_m=float(a['lane'][-1,3]),practice_join_start_station_m=cfg['practice_merge_start_station_m'],
          practice_join_xz_m=a['join'].tolist(),pit_connector_endpoints_match=True,
          dimensions_are_authoring_estimates=True,in_game_riding_test=False)
    save(O/'pit_access_validation.json',qa); print('v028 shaded staging and practice entry appended; clearances passed',flush=True)
if __name__=='__main__':main()
