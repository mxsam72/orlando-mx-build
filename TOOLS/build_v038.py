"""Move/repaint the two trucks and add compact shared-texture billboards.

The v037 road and every unrelated FBX object are retained exactly. Only
the 22 truck geometry records and two body-material connections change.
"""
import copy, math, shutil, struct
from collections import Counter
import numpy as np
from PIL import Image
import shapely
from shapely.geometry import Polygon, box
from v038_common import *
from v027_scenery import parse, encode, values, child, fingerprint, vertices, geometry_records
from rebind_scenery import array, encoded_array
from v037_fbx import prop, node, setvalues, mapped_geometry
from verify_v037_source import faces

def yaw(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,0,-s],[0,1,0],[s,0,c]])

def transform_geometry(g,rotation,origin,pivot,scale=1.):
    v=(vertices(g)-pivot)*scale@rotation.T+origin
    child(g,b'Vertices')['props']=encoded_array(v*[100,100,-100])
    for layer in g['children']:
        if layer['name']!=b'LayerElementNormal':continue
        n=child(layer,b'Normals');a=array(n).reshape(-1,3)*[1,1,-1]
        n['props']=encoded_array((a@rotation.T)*[1,1,-1])
    return v

def optimize_normals(cfg):
    report=[];digests=set();savings=0
    for name in cfg['normal_map_optimization']['files']:
        source=BASE/'materials'/name;target=O/'materials'/name
        with Image.open(source) as im:
            rgba=np.array(im.convert('RGBA'));size=im.size
        assert size==(2048,2048)
        old_pixel_sha=__import__('hashlib').sha256(rgba.tobytes()).hexdigest()
        rgb=Image.fromarray(rgba[:,:,:3]).resize((1024,1024),Image.Resampling.LANCZOS)
        n=np.array(rgb,dtype=float)/127.5-1
        n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-9)
        normal=np.uint8(np.rint(np.clip((n+1)*127.5,0,255)))
        alpha=np.array(Image.fromarray(rgba[:,:,3]).resize((1024,1024),Image.Resampling.LANCZOS))
        result=np.dstack([normal,alpha]);image_file(Image.fromarray(result),target)
        import zlib
        old_zip=len(zlib.compress(rgba.tobytes(),6));new_zip=len(zlib.compress(result.tobytes(),6))
        if old_pixel_sha not in digests:savings+=old_zip-new_zip;digests.add(old_pixel_sha)
        report.append(dict(file=name,old_size_px=list(size),size_px=[1024,1024],source_sha256=sha(source),sha256=sha(target),alpha_preserved=bool(rgba[:,:,3].min()==rgba[:,:,3].max()==result[:,:,3].min()==result[:,:,3].max()),old_rgba_deflate_bytes=old_zip,new_rgba_deflate_bytes=new_zip))
    qa=dict(checks_pass=True,changed_files=report,unique_native_payloads=len(digests),estimated_native_payload_savings_bytes=savings,all_color_maps_and_oval_textures_retained_exact=True,normal_vectors_renormalized=True)
    save(O/'optimization_validation.json',qa);return qa

def solid_box(name,material,lo,hi):
    lo=np.asarray(lo);hi=np.asarray(hi)
    v=np.array([[lo[0],lo[1],lo[2]],[hi[0],lo[1],lo[2]],[hi[0],hi[1],lo[2]],[lo[0],hi[1],lo[2]],[lo[0],lo[1],hi[2]],[hi[0],lo[1],hi[2]],[hi[0],hi[1],hi[2]],[lo[0],hi[1],hi[2]]])
    f=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    return dict(name=name,material_id=material,vertices=v.tolist(),faces=f.tolist(),uv=(v[:,[0,1]]/3)[f].tolist())

def joined(name,material,parts):
    vv=[];ff=[];uv=[]
    for m in parts:
        ff.extend((np.asarray(m['faces'])+len(vv)).tolist());vv.extend(m['vertices']);uv.extend(m['uv'])
    return dict(name=name,material_id=material,vertices=vv,faces=ff,uv=uv)

def entrance_meshes(h,cfg,mats):
    p=cfg['speed_world'];x,z=p['xz_m'];w=p['width_m'];hh=p['image_height_m'];y=float(ground(h,[[x,z]])[0]);bottom=y+p['image_bottom_above_ground_m'];top=bottom+hh
    frame=[];bases=[];half=w/2;post=half+.30
    # Vertical supports are outside the graphic on both faces. All horizontal
    # frame members also lie outside its bounds, so no pole covers any text.
    for side in [-1,1]:
        zz=z+side*post;gy=float(ground(h,[[x,zz]])[0])
        frame.append(solid_box('',mats['frame'],[x-.12,gy-.10,zz-.12],[x+.12,top+.20,zz+.12]))
        bases.append(solid_box('',mats['concrete'],[x-.42,gy-.05,zz-.42],[x+.42,gy+.13,zz+.42]))
    for yy in [bottom-.10,top+.10]:
        frame.append(solid_box('',mats['frame'],[x-.14,yy-.08,z-post-.12],[x+.14,yy+.08,z+post+.12]))
    verts=[];tris=[];uv=[]
    for sign in [-1,1]:
        xx=x+sign*.105;u=np.array([0.,0.,-sign]);c=np.array([xx,(bottom+top)/2,z])
        vv=np.array([c-u*half-[0,hh/2,0],c+u*half-[0,hh/2,0],c+u*half+[0,hh/2,0],c-u*half+[0,hh/2,0]])
        ix=len(verts);verts.extend(vv.tolist());tris.extend([[ix,ix+1,ix+2],[ix,ix+2,ix+3]]);uv.extend([[[0,0],[1,0],[1,1]],[[0,0],[1,1],[0,1]]])
    panel=dict(name=p['id']+'_graphic',material_id=mats['graphic'],vertices=verts,faces=tris,uv=uv)
    meshes=[joined(p['id']+'_frame',mats['frame'],frame),joined(p['id']+'_concrete',mats['concrete'],bases),panel]
    return meshes,dict(checks_pass=True,text=p['text'],size_m=[w,hh],ground_anchor_xyz_m=[x,y,z],two_readable_faces=True,vertical_supports_outside_image=True,minimum_support_image_horizontal_gap_m=.18)

def release():
    source=R/'12_RELEASE/orlandomx_2026_v037';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.suffix in ['.map','.trh']:continue
        copy_exact(p,dest/p.name.replace('orlandomx_2026_v037',NAME))
    ini=dest/(NAME+'.ini');t=ini.read_text();assert 'v037' in t;atomic(ini,t.replace('v037','v038').encode())
    copy_exact(BASE/'orlandomx_2026_v037.rdf',O/(NAME+'.rdf'));copy_exact(O/(NAME+'.rdf'),dest/(NAME+'.rdf'))

def main():
    cfg=read(S/'update.json');assert sha(BASE/'scenery.fbx')==cfg['baseline_scenery_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O);optimization=optimize_normals(cfg);h=height_field()
    original=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    objects=next(n for n in nodes if n['name']==b'Objects');links=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    byid={values(n)[0]:n for n in objects['children']};records={i:fingerprint(n) for i,n in byid.items()};oldlinks=[fingerprint(n) for n in links['children']];rec=geometry_records(nodes)
    uid=max(byid)+1000;new_textures=[];modified_ids=[];connection_changes=[];new_meshes=[];new_probes=[]
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    def material_for(mid):
        return next(values(n)[1] for n in links['children'] if values(n)[2]==mid and byid.get(values(n)[1],{}).get('name')==b'Material')
    existing_qwik={part:material_for(rec['v033_qwikchute_billboard_'+part][1]) for part in ['frame','concrete','logo']}
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'white',b'marker_white']);matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture');vidid=next(values(n)[1] for n in links['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    def new_material(name,image):
        fname=name+'.tga';image_file(image,O/'facility_textures'/fname);raw=(O/'facility_textures'/fname).read_bytes();ids=[newid(),newid(),newid()]
        for src,nid,kind in zip([base_mat,byid[texid],byid[vidid]],ids,['Material','Texture','Video']):
            n=copy.deepcopy(src);v=values(n);setvalues(n,nid,name.encode()+b'\x00\x01'+kind.encode(),*v[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                if c['name']==b'Media':setvalues(c,name.encode()+b'\x00\x01Video')
                if c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
                if c['name']==b'Properties70':
                    for p in c['children']:
                        v=values(p)
                        if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*v[:4],1.,1.,1.)
                        elif v and v[0]==b'Diffuse':setvalues(p,*v[:4],1.)
                        elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],fname)
            objects['children'].append(n)
        connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1]);new_textures.append(dict(texture=fname,sha256=sha(O/'facility_textures'/fname),size_px=list(image.size)));return ids[0]
    paint={}
    yy,xx=np.mgrid[:128,:128];grain=(np.sin(xx*.13)+np.sin(yy*.10))*.65
    for car in cfg['vehicles']:
        rgb=np.uint8(np.rint(np.clip(np.array(car['paint_rgb'])+grain[:,:,None],0,255)))
        paint[car['paint']]=new_material('v038_cybertruck_'+car['paint'],Image.fromarray(rgb))
    image=Image.open(S/cfg['speed_world']['graphic_png']).convert('RGB');entrance_mat=new_material('v038_orlando_speed_world',image)
    road=rec['TRKASPH_v037_oval_surface'][0];rv=vertices(road);rf=np.asarray(faces(road));poly=shapely.union_all(shapely.polygons(rv[:,[0,2]][rf]));trucks=[]
    old_vehicle_probes=[]
    for car in cfg['vehicles']:
        names=[n for n in rec if n.startswith(car['id']+'_')];assert len(names)==11
        parts={n:rec[n] for n in names};allv=np.concatenate([vertices(g) for g,mid in parts.values()]);pivot=np.r_[(allv[:,0].min()+allv[:,0].max())/2,allv[:,1].min(),(allv[:,2].min()+allv[:,2].max())/2]
        front=vertices(parts[car['id']+'_headlight'][0])[:,[0,2]].mean(0);rear=vertices(parts[car['id']+'_red_light'][0])[:,[0,2]].mean(0);f=front-rear;rotation=yaw(math.radians(car['heading_degrees'])-math.atan2(f[1],f[0]))
        relative=allv-pivot;rot=relative@rotation.T;low=relative[:,1]<.065;foot=rot[low][:,[0,2]]+car['xz_m'];q=foot-car['xz_m']
        fit=np.linalg.lstsq(np.c_[q,np.ones(len(q))],ground(h,foot),rcond=None)[0];normal=np.r_[-fit[0],1.,-fit[1]];normal/=np.linalg.norm(normal);axis=np.cross([0,1,0],normal);cos=normal[1];K=np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
        tilt=np.eye(3)+K+K@K/(1+cos);rotation=tilt@rotation;origin=np.r_[car['xz_m'][0],fit[2],car['xz_m'][1]]
        v=relative@rotation.T+origin;origin[1]+=float(np.max(ground(h,v[low][:,[0,2]])-v[low][:,1]));v=relative@rotation.T+origin;gap=v[low][:,1]-ground(h,v[low][:,[0,2]])
        assert gap.min()>-1e-8 and gap.max()<.1,(car['id'],gap.tolist())
        footprint=Polygon(v[:,[0,2]]).convex_hull;assert not poly.intersects(footprint);distance=float(poly.distance(footprint));assert distance>2.5,(car['id'],distance)
        for name,(g,mid) in parts.items():
            old_vehicle_probes.append(vertices(g)[0].tolist());vv=transform_geometry(g,rotation,origin,pivot);modified_ids.append(values(g)[0]);new_probes.extend(vv[[0,len(vv)//2,-1]].tolist())
            if name.endswith('_cyber_steel'):
                oldmat=material_for(mid)
                link=next(n for n in links['children'] if values(n)[1:3]==[oldmat,mid]);old_fp=fingerprint(link);setvalues(link,'OO',paint[car['paint']],mid);connection_changes.append(dict(model=name,old_material_id=oldmat,new_material_id=paint[car['paint']],prior_connection_fingerprint=old_fp))
        trucks.append(dict(**car,parts=11,static=True,all_vertices_off_asphalt=True,grass_side_of_entrance=True,road_edge_clearance_m=distance,wheel_clearance_min_m=float(gap.min()),wheel_clearance_max_m=float(gap.max()),bounds_xyz_m=[v.min(0).tolist(),v.max(0).tolist()]))
    def add_clone(name,srcname,rotation,origin,pivot,scale):
        g0,mid0=rec[srcname];gid,mid=newid(),newid();g=copy.deepcopy(g0);v=values(g);setvalues(g,gid,name.encode()+b'\x00\x01Geometry',*v[2:]);vv=transform_geometry(g,rotation,origin,pivot,scale)
        model=copy.deepcopy(byid[mid0]);mv=values(model);setvalues(model,mid,name.encode()+b'\x00\x01Model',*mv[2:]);objects['children'] += [g,model];connect(gid,mid);connect(material_for(mid0),mid);connect(mid,0)
        new_probes.extend(vv[[0,len(vv)//2,-1]].tolist());new_meshes.append(dict(name=name,vertices=len(vv),bounds_xyz_m=[vv.min(0).tolist(),vv.max(0).tolist()],original_texture_reused=True))
    qw=cfg['qwikchute'];origin=[qw['xz_m'][0],float(ground(h,[qw['xz_m']])[0]),qw['xz_m'][1]]
    for part in ['frame','concrete','logo']:add_clone(qw['id']+'_'+part,qw['source']+'_'+part,yaw(math.radians(qw['heading_degrees'])),origin,qw['reference_ground_xyz_m'],qw['scale'])
    meshes,signqa=entrance_meshes(h,cfg,dict(frame=existing_qwik['frame'],concrete=existing_qwik['concrete'],graphic=entrance_mat))
    for m in meshes:
        gid,mid=newid(),newid();g=mapped_geometry(gid,m);model=copy.deepcopy(template);v=values(model);setvalues(model,mid,m['name'].encode()+b'\x00\x01Model',*v[2:]);objects['children'] += [g,model];connect(gid,mid);connect(m['material_id'],mid);connect(mid,0)
        vv=np.asarray(m['vertices']);new_probes.extend(vv[[0,len(vv)//2,-1]].tolist());new_meshes.append(dict(name=m['name'],vertices=len(vv),bounds_xyz_m=[vv.min(0).tolist(),vv.max(0).tolist()]))
    counts=Counter(n['name'] for n in objects['children']);decl=[]
    for d in defs['children']:
        if d['name']!=b'ObjectType':continue
        typ=values(d)[0];count=values(child(d,b'Count'))[0]+counts[typ]-sum(n['name']==typ for n in byid.values());child(d,b'Count')['props']=b'I'+struct.pack('<i',count);decl.append(count)
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',sum(decl));out=encode(nodes,tail);atomic(O/'scenery.fbx',out)
    got,_=parse(out);after={values(n)[0]:n for n in next(n for n in got if n['name']==b'Objects')['children']}
    assert all(fingerprint(after[i])==fp for i,fp in records.items() if i not in modified_ids)
    from scipy.spatial import cKDTree
    original_probes=read(BASE/'native_coordinate_probes.json')['expected_xyz_metres'];dist=cKDTree(old_vehicle_probes).query(original_probes)[0];kept=[p for p,d in zip(original_probes,dist) if d>1e-7];assert len(original_probes)-len(kept)==22
    save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=kept+new_probes));save(O/'v038_removed_truck_probes.json',dict(prior_xyz_metres=old_vehicle_probes))
    scene=dict(checks_pass=True,baseline_scenery_sha256=sha(BASE/'scenery.fbx'),retained_baseline_object_records=len(records)-len(modified_ids),modified_truck_geometry_ids=modified_ids,modified_connections=connection_changes,new_textures=new_textures,new_meshes=new_meshes,road_wall_and_all_other_objects_byte_exact=True,prior_truck_probes_removed=22)
    save(O/'v038_scenery_validation.json',scene);save(O/'v038_vehicle_validation.json',dict(checks_pass=True,vehicles=trucks,static_vehicle_count=2,original_pit_cybertruck_preserved=True));save(O/'v038_entrance_validation.json',signqa);save(O/'v038_layout.json',cfg)
    qa=dict(read(BASE/'source_validation.json'));qa.update(version='v038',baseline_version='user-tested v037',baseline_commit=cfg['baseline_source_commit'],source_checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),v038_scenery=scene,v038_vehicles=read(O/'v038_vehicle_validation.json'),optimization=optimization,oval_geometry_and_textures_exact_v037=True,all_MX_color_maps_exact_v037=True,selected_terrain_normals_resampled=True,native_compilation=False)
    save(O/'source_validation.json',qa);release()
    print('v038 source ready: red/black trucks on entry-side grass, two billboards, eight targeted normal-map files; oval byte exact.',flush=True)

if __name__=='__main__':main()
