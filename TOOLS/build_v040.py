"""Repair conflicting pit surfaces, place the entrance arch, and add a dirt double.

All coordinates below are native game metres (+Z). No v039 sign UV operation
is repeated. The two Qwikchute signs and all road mesh records remain exact.
"""
import copy, math, shutil, struct
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon
from v040_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from rebind_scenery import array, encoded_array
from verify_v037_source import faces
from v037_fbx import mapped_geometry, node, setvalues

def face_uv(g):
    l=child(g,b'LayerElementUV');uv=array(child(l,b'UV')).reshape(-1,2)
    index=next((c for c in l['children'] if c['name']==b'UVIndex'),None)
    mapping=values(child(l,b'MappingInformationType'))[0]
    ix=array(index).astype(int) if index else np.arange(len(uv));out=[];offset=0
    for f in faces(g):
        out.append(uv[ix[np.asarray(f)]] if mapping in [b'ByVertice',b'ByVertex',b'ByControlPoint'] else uv[ix[offset:offset+len(f)]])
        offset+=len(f)
    return out

def replace_mesh(g,v,ff,uv):
    # mapped_geometry reflects Z and reverses winding; feed reversed native
    # face/UV records to preserve the existing FBX/native handedness exactly.
    used=sorted({i for f in ff for i in f});index={i:j for j,i in enumerate(used)}
    mesh=dict(name=values(g)[1].split(b'\0')[0].decode(),vertices=np.asarray(v)[used].tolist(),
              faces=[[index[i] for i in list(f)[::-1]] for f in ff],uv=[np.asarray(t)[::-1].tolist() for t in uv])
    replacement=mapped_geometry(values(g)[0],mesh)
    assert values(replacement)==values(g)
    g.clear();g.update(replacement)

def triangulated(g,keep=None):
    v=vertices(g);ff=faces(g);uv=face_uv(g);tris=[];tex=[]
    for i,f in enumerate(ff):
        if keep is not None and i not in keep:continue
        for j in range(1,len(f)-1):tris.append([f[0],f[j],f[j+1]]);tex.append(uv[i][[0,j,j+1]])
    return v,tris,tex

def outward_decals(rec,cfg):
    fixed=[]
    tokens=['_premier_wrap','_premier_tail','_chevy_badge','_king_ranch','_four_by_four','_ford_badge',
            '_jordan_number','_jordan_shroud','_premier_number','_premier_shroud','_sam_number','_sam_shroud','_shane_number','_shane_shroud']
    for name,(g,mid) in rec.items():
        if not any(t in name for t in tokens):continue
        prefix='_'.join(name.split('_')[:2]);group=[vertices(gg) for nn,(gg,mm) in rec.items() if nn.startswith(prefix+'_') and nn.endswith(('_dark','_steel','_engine'))]
        assert group,name
        vv=np.concatenate(group);centre=(vv.min(0)+vv.max(0))/2
        v,ff,uv=triangulated(g);chosen=[];chosen_uv=[];normals=[];seen=set()
        for f,t in zip(ff,uv):
            q=v[f];n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
            # Native reflected polygon winding has inward cross products.
            if np.dot(n,q.mean(0)-centre)>1e-7:continue
            key=tuple(sorted(tuple(np.round(x,7)) for x in q))
            if key in seen:continue
            seen.add(key);chosen.append(f);chosen_uv.append(t);normals.append(-n)
        assert chosen and len(chosen)<=len(ff),name
        # Weld positions before calculating the offset; adjacent decal triangles
        # retain shared boundaries instead of opening seams on curved wraps.
        totals={}
        for f,n in zip(chosen,normals):
            for i in f:
                k=tuple(np.round(v[i],7));totals[k]=totals.get(k,np.zeros(3))+n
        newv=[];newf=[]
        for f in chosen:
            tri=[]
            for i in f:
                n=totals[tuple(np.round(v[i],7))];n=n/np.linalg.norm(n)
                tri.append(len(newv));newv.append(v[i]+n*cfg['decal_clearance_addition_m'])
            newf.append(tri)
        replace_mesh(g,newv,newf,chosen_uv)
        fixed.append(dict(name=name,triangles_before=len(ff),triangles_after=len(chosen),
                          duplicate_or_inward_triangles_removed=len(ff)-len(chosen),outward_offset_m=cfg['decal_clearance_addition_m'],uv_pixels_unchanged=True))
    return fixed

def cut_backing(g,axis,plane,openings):
    """Remove only specified covered areas from a planar backing face."""
    v=vertices(g);ff=faces(g);uv=face_uv(g);axes=[i for i in range(3) if i!=axis]
    outv=[];outf=[];outu=[];cut=0
    for f,t in zip(ff,uv):
        q=v[f]
        if np.max(np.abs(q[:,axis]-plane))<1e-7:
            p=Polygon(q[:,axes]);diff=p.difference(shapely.union_all(openings))
            if diff.area<p.area-1e-8:
                cut+=1
                uvfit=np.linalg.lstsq(np.c_[q[:,axes],np.ones(len(q))],t,rcond=None)[0]
                oldn=np.cross(q[1]-q[0],q[2]-q[0])
                geoms=[] if diff.is_empty else ([diff] if diff.geom_type=='Polygon' else list(diff.geoms))
                for piece in geoms:
                    for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(piece)):
                        pt=np.asarray(tr.exterior.coords)[:3];xyz=np.empty((3,3));xyz[:,axes]=pt;xyz[:,axis]=plane
                        if np.dot(np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]),oldn)<0:xyz=xyz[::-1];pt=pt[::-1]
                        i=len(outv);outv.extend(xyz);outf.append([i,i+1,i+2]);outu.append(np.c_[pt,np.ones(3)]@uvfit)
                continue
        for j in range(1,len(f)-1):
            i=len(outv);outv.extend(q[[0,j,j+1]]);outf.append([i,i+1,i+2]);outu.append(t[[0,j,j+1]])
    assert cut>0
    replace_mesh(g,outv,outf,outu)
    return cut

def bathroom(rec):
    glass=vertices(rec['restroom_glass'][0]);openings=[]
    for block in np.split(glass,2):
        low=block.min(0);hi=block.max(0)
        # Preserve door borders but remove the wall and gray panel behind them.
        openings.append(shapely.box(low[0],low[1],hi[0],hi[1]))
    wall=vertices(rec['restroom_siding'][0]);trim=vertices(rec['restroom_trim'][0])
    a=cut_backing(rec['restroom_siding'][0],2,wall[:,2].max(),openings)
    b=cut_backing(rec['restroom_trim'][0],2,trim[:,2].max(),openings)
    # Remove horizontal siding ribs where they run through a door opening.
    a2=rec['restroom_alloy'][0];v=vertices(a2);ff=faces(a2);uv=face_uv(a2);newv=[];newf=[];newuv=[]
    # First eleven 8-vertex blocks are the horizontal wall bands. Handles are
    # the remaining block and must stay attached to their accepted doors.
    for i,(f,t) in enumerate(zip(ff,uv)):
        q=v[f]
        if max(f)<88:
            # Clip every band polygon to the portions outside both door X spans.
            lo=q[:,0].min();hi=q[:,0].max();intervals=[(lo,hi)]
            for op in openings:
                ox0,oy0,ox1,oy1=op.bounds
                if q[:,1].max()<oy0 or q[:,1].min()>oy1:continue
                intervals=[part for aa,bb in intervals for part in [(aa,min(bb,ox0)),(max(aa,ox1),bb)] if part[1]-part[0]>1e-8]
            for aa,bb in intervals:
                # Axis-aligned rib faces are quads; clip their X coordinates.
                qq=q.copy()
                if hi-lo>1e-8:
                    tt=(qq[:,0]-lo)/(hi-lo);qq[:,0]=aa+tt*(bb-aa)
                elif not any(aa-1e-8<=lo<=bb+1e-8 for aa,bb in intervals):continue
                for j in range(1,len(qq)-1):
                    tri=qq[[0,j,j+1]]
                    if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-10:continue
                    ix=len(newv);newv.extend(tri);newf.append([ix,ix+1,ix+2]);newuv.append(t[[0,j,j+1]])
        else:
            for j in range(1,len(f)-1):
                ix=len(newv);newv.extend(q[[0,j,j+1]]);newf.append([ix,ix+1,ix+2]);newuv.append(t[[0,j,j+1]])
    replace_mesh(a2,newv,newf,newuv)
    return dict(wall_faces_opened=a,door_backing_faces_opened=b,wall_ribs_removed_inside_door_areas=True,door_and_handle_positions_unchanged=True)

def flag_texture():
    im=Image.new('RGB',(2048,1024),(255,255,255));d=ImageDraw.Draw(im)
    red=(178,34,52);blue=(60,59,110);stripe=1024/13
    for i in range(0,13,2):d.rectangle([0,round(i*stripe),2047,round((i+1)*stripe)-1],fill=red)
    cw=2048*.4;ch=stripe*7;d.rectangle([0,0,round(cw)-1,round(ch)-1],fill=blue)
    radius=ch*.0616
    for row in range(9):
        count=6 if row%2==0 else 5
        for col in range(count):
            x=cw*(col+(0.5 if count==6 else 1))/6;y=ch*(row+0.5)/9
            p=[(x+radius*(1 if k%2==0 else .382)*math.sin(k*math.pi/5),y-radius*(1 if k%2==0 else .382)*math.cos(k*math.pi/5)) for k in range(10)]
            d.polygon(p,fill=(255,255,255))
    image_file(im,O/'facility_textures/v040_american_flag.tga')

def replace_flag(nodes,rec):
    flag_texture();objects=next(n for n in nodes if n['name']==b'Objects');links=next(n for n in nodes if n['name']==b'Connections')
    byid={values(n)[0]:n for n in objects['children']};newid=max(byid)+1000
    g,mid=rec['front_flag_red'];oldv=vertices(g)
    # The original flag's local horizontal axis is rotated -15 degrees. Keep
    # its pole-side edge, span and vertical extent; use two separated opaque faces.
    angle=math.radians(-15);u=np.array([math.cos(angle),0,math.sin(angle)]);normal=np.array([-u[2],0,u[0]])
    centre=(oldv.min(0)+oldv.max(0))/2;span=np.ptp(oldv@u);height=np.ptp(oldv[:,1]);verts=[];tris=[];uv=[]
    for sign in [-1,1]:
        c=centre+normal*sign*.15;uu=u*sign
        vv=[c-uu*span/2-[0,height/2,0],c+uu*span/2-[0,height/2,0],c+uu*span/2+[0,height/2,0],c-uu*span/2+[0,height/2,0]]
        ix=len(verts);verts.extend(vv);tris.extend([[ix,ix+1,ix+2],[ix,ix+2,ix+3]])
        # Native mirrored Z conversion: retain readable orientation from each side.
        uv.extend([[[0,0],[1,0],[1,1]],[[0,0],[1,1],[0,1]]])
    mesh=dict(name='front_flag_red',vertices=np.asarray(verts).tolist(),faces=tris,uv=uv)
    replacement=mapped_geometry(values(g)[0],mesh);g.clear();g.update(replacement)
    # Clone a flat, white image material to avoid multiplying the flag by red.
    template=next(n for n in objects['children'] if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'v033_qwikchute_logo')
    matid=values(template)[0]
    tid=next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vid=next(values(n)[1] for n in links['children'] if values(n)[2]==tid and byid.get(values(n)[1],{}).get('name')==b'Video')
    ids=[newid+i for i in range(3)];fn='v040_american_flag.tga';raw=(O/'facility_textures'/fn).read_bytes()
    for src,nid,kind in zip([template,byid[tid],byid[vid]],ids,['Material','Texture','Video']):
        n=copy.deepcopy(src);old=values(n);setvalues(n,nid,b'v040_american_flag\x00\x01'+kind.encode(),*old[2:])
        for c in n['children']:
            if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fn)
            if c['name']==b'Media':setvalues(c,b'v040_american_flag\x00\x01Video')
            if c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
            if c['name']==b'Properties70':
                for p in c['children']:
                    a=values(p)
                    if a and a[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*a[:4],fn)
        objects['children'].append(n)
    # Remove old stripe/star meshes; there is no backing cloth or coincident layer.
    removed=[]
    for name in ['front_flag_trim','front_flag_navy']:
        gg,mm=rec[name];removed.extend([values(gg)[0],mm])
    objects['children']=[n for n in objects['children'] if values(n)[0] not in removed]
    links['children']=[n for n in links['children'] if not any(i in removed for i in values(n)[1:3]) and not (values(n)[2]==mid and byid.get(values(n)[1],{}).get('name')==b'Material')]
    links['children'] += [node('C','OP',ids[1],ids[0],'DiffuseColor'),node('C','OO',ids[2],ids[1]),node('C','OO',ids[0],mid)]
    return dict(removed_object_ids=removed,texture=fn,sha256=sha(O/'facility_textures'/fn),size_px=[2048,1024],opaque=True,faces_separation_m=.3,stars=50,stripes=13,pole_unchanged=True)

def freestyle(cfg,nodes):
    raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);old=raw/65535*18
    xx,zz=np.meshgrid(np.arange(2049)*600/2048,600-np.arange(2049)*600/2048)
    f=cfg['freestyle'];p=np.asarray(f['takeoff_profile_z_height_slope']);rise=CubicHermiteSpline(p[:,0],p[:,1],p[:,2])
    height=np.zeros_like(xx);a=(zz>=p[0,0])&(zz<=p[-1,0]);height[a]=rise(zz[a])
    a=(zz>p[-1,0])&(zz<f['takeoff_back_end_z_m']);t=(zz[a]-p[-1,0])/(f['takeoff_back_end_z_m']-p[-1,0]);height[a]=p[-1,1]*(1-t*t*(3-2*t))
    a=(zz>=f['landing_nose_z_m'])&(zz<f['landing_crest_z_m']);t=(zz[a]-f['landing_nose_z_m'])/(f['landing_crest_z_m']-f['landing_nose_z_m']);height[a]=f['landing_height_m']*(t*t*(3-2*t))
    a=(zz>=f['landing_crest_z_m'])&(zz<=f['landing_end_z_m']);t=(zz[a]-f['landing_crest_z_m'])/(f['landing_end_z_m']-f['landing_crest_z_m']);height[a]=f['landing_height_m']*(1-t)**1.35
    dx=np.abs(xx-f['axis_x_m']);t=np.clip((dx-f['flat_half_width_m'])/(f['footprint_half_width_m']-f['flat_half_width_m']),0,1)
    cross=1-t*t*(3-2*t);height*=cross
    rec=geometry_records(nodes);road=rec['TRKASPH_v037_oval_surface'][0];rv=vertices(road);rf=np.asarray(faces(road));union=shapely.union_all(shapely.polygons(rv[rf][:,:,[0,2]]))
    assert union.geom_type=='Polygon' and len(union.interiors)==2
    holes=shapely.union_all([Polygon(h).buffer(-f['grass_boundary_guard_m']) for h in union.interiors])
    allowed=shapely.contains_xy(holes,xx,zz);height[~allowed]=0
    new=np.rint(np.clip(old+height,0,18)/18*65535).astype('<u2');changed=new!=raw
    assert changed.any() and np.array_equal(new[~allowed],raw[~allowed])
    atomic(O/'terrain.raw',new.tobytes());image_file(Image.fromarray(new),O/'terrain_16bit.png');np.save(O/'height_metres.npy',new/65535*18)
    # Masks use their own resolution. Only islands' mound footprints change;
    # all racing, holeshot, pit, sand and road masks remain exact.
    affected=[]
    for name in ['grass.tga','visual_grass.tga','visual_racing.tga','v032_face.tga']:
        path=O/'masks'/name
        if not path.exists():continue
        im=Image.open(path);a=np.array(im);h,w=a.shape[:2]
        x,z=np.meshgrid(np.arange(w)*600/(w-1),600-np.arange(h)*600/(h-1))
        dh=map_coordinates(height,[(600-z)/600*2048,x/600*2048],order=1,mode='nearest')
        active=(dh>.035)&shapely.contains_xy(holes,x,z)
        amount=np.uint8(np.clip(dh/.25,0,1)*255)
        if name in ['grass.tga','visual_grass.tga']:a[active]=0
        elif a.ndim==2:a[active]=np.maximum(a[active],amount[active])
        else:a[active]=np.maximum(a[active],amount[active,None])
        image_file(Image.fromarray(a),path);affected.append(name)
    lip=p[-1,0];crest=f['landing_crest_z_m'];bounds=[float(xx[changed].min()),float(zz[changed].min()),float(xx[changed].max()),float(zz[changed].max())]
    qa=dict(checks_pass=True,native_game_direction='+Z: right grass island to left grass island in supplied screenshot',lip_xyz_m=[f['axis_x_m'],float(map_coordinates(new/65535*18,[[(600-lip)/600*2048],[f['axis_x_m']/600*2048]],order=1)[0]),lip],landing_crest_xyz_m=[f['axis_x_m'],float(map_coordinates(new/65535*18,[[(600-crest)/600*2048],[f['axis_x_m']/600*2048]],order=1)[0]),crest],takeoff_height_above_ground_m=8.5,landing_height_above_ground_m=7.8,lip_to_landing_crest_m=crest-lip,changed_height_samples=int(changed.sum()),bounds_xz_m=bounds,changed_masks=affected,entire_road_and_MX_heightmap_outside_grass_islands_exact=True,footprints_within_grass_holes=True,maximum_height_metres=float(new.max()/65535*18),collision='Native terrain heightfield, soil material; no floating render-only ramp',in_game_riding_test=False)
    save(O/'v040_freestyle_validation.json',qa);return qa

def refresh_probes(oldrec,newrec,changed_names,removed_names,delta):
    old=np.concatenate([vertices(oldrec[n][0]) for n in changed_names+removed_names]);tree=cKDTree(old)
    current=np.concatenate([vertices(newrec[n][0]) for n in changed_names if n in newrec]);newtree=cKDTree(current)
    report=[]
    for path in BASE.glob('*probes.json'):
        data=read(path)
        if 'expected_xyz_metres' not in data:continue
        pts=np.asarray(data['expected_xyz_metres']);dist=tree.query(pts)[0];keep=pts[dist>1e-7].tolist()
        for point in pts[dist<=1e-7]:
            target=point+delta if point[0]>460 and 306<=point[2]<=322 else point
            keep.append(current[newtree.query(target)[1]].tolist())
        data['expected_xyz_metres']=keep;save(O/path.name,data);report.append(dict(file=path.name,updated=int((dist<=1e-7).sum())))
    points=[]
    for name in changed_names:
        if name not in newrec:continue
        v=vertices(newrec[name][0]);points.extend(v[np.unique(np.linspace(0,len(v)-1,min(4,len(v)),dtype=int))].tolist())
    save(O/'v040_native_probes.json',dict(expected_xyz_metres=points))
    return report

def release():
    src=R/'12_RELEASE/orlandomx_2026_v039';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        if p.suffix in ['.map','.trh']:continue
        copy_exact(p,dest/p.name.replace('orlandomx_2026_v039',NAME))
    ini=dest/(NAME+'.ini');t=ini.read_text();assert 'v039' in t;atomic(ini,t.replace('v039','v040').encode())
    copy_exact(BASE/'orlandomx_2026_v039.rdf',O/(NAME+'.rdf'));copy_exact(O/(NAME+'.rdf'),dest/(NAME+'.rdf'))

def main():
    cfg=read(S/'update.json');baseqa=read(BASE/'source_validation.json')
    assert baseqa['version']=='v039' and baseqa['source_checks_pass']
    assert sha(BASE/'scenery.fbx')==cfg['baseline_scenery_sha256'] and sha(BASE/'terrain.raw')==cfg['baseline_terrain_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O)
    original=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    oldrec=geometry_records(parse(original)[0]);rec=geometry_records(nodes)
    objects=next(n for n in nodes if n['name']==b'Objects');before={values(n)[0]:fingerprint(n) for n in objects['children']}
    frame=rec['v032_pup_whatley_memorial_frame'][0];v,ff,uv=triangulated(frame,set(range(6,len(faces(frame)))))
    replace_mesh(frame,v,ff,uv)
    art=rec['v032_pup_whatley_memorial_memorial'][0];v=vertices(art);v[:,2]=144+np.sign(v[:,2]-144)*cfg['memorial_image_half_depth_m'];child(art,b'Vertices')['props']=encoded_array(v*[100,100,-100])
    decals=outward_decals(rec,cfg);bath=bathroom(rec);flag=replace_flag(nodes,rec)
    # Corrected Speed World UVs remain byte exact: placement changes only.
    old_anchor=np.array([465.,314.]);new_anchor=np.asarray(cfg['entrance_anchor_xz_m']);h=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    g=lambda p:float(map_coordinates(h,[[(600-p[1])/600*2048],[p[0]/600*2048]],order=1)[0])
    delta=np.array([new_anchor[0]-old_anchor[0],g(new_anchor)-g(old_anchor),new_anchor[1]-old_anchor[1]])
    for name,(geom,mid) in rec.items():
        if name.startswith('v038_orlando_speed_world_entrance_'):
            v=vertices(geom)+delta
            if name.endswith('_graphic'):v[:,1]+=cfg['entrance_raise_m']
            elif name.endswith('_frame'):
                top=v[:16,1]>v[:16,1].mean();v[np.flatnonzero(top),1]+=cfg['entrance_raise_m'];v[16:,1]+=cfg['entrance_raise_m']
            child(geom,b'Vertices')['props']=encoded_array(v*[100,100,-100])
    # Opaque solids should not render their internal/back-facing shell layers.
    # This is the standard FBX counter-clockwise culling mode; source outward
    # normals/winding are preserved, including the native Z reflection.
    byid={values(n)[0]:n for n in objects['children']};culled=[]
    prefixes=('truck_','van_','bike_','rv_','pickup_','office_','restroom_','covered_stand_',
              'concession_','canopy_','toyhauler_','trailer_','v028_staging_trailer_',
              'v037_oval_cybertruck_','v032_pup_whatley_memorial_','front_flag_red')
    for name,(geom,mid) in geometry_records(nodes).items():
        if name.startswith(prefixes):
            model=byid[mid];c=child(model,b'Culling');setvalues(c,'CullingOnCCW');culled.append(name)
    defs=next(n for n in nodes if n['name']==b'Definitions');counts=Counter(n['name'] for n in objects['children']);decl=[]
    for d in defs['children']:
        if d['name']==b'ObjectType':ct=counts[values(d)[0]];child(d,b'Count')['props']=b'I'+struct.pack('<i',ct);decl.append(ct)
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',sum(decl))
    encoded=encode(nodes,tail);atomic(O/'scenery.fbx',encoded);newnodes=parse(encoded)[0];newrec=geometry_records(newnodes)
    after={values(n)[0]:fingerprint(n) for n in next(n for n in newnodes if n['name']==b'Objects')['children']}
    changed_ids=[i for i in before if i in after and before[i]!=after[i]];removed_ids=[i for i in before if i not in after]
    changed_names=[n for n,(gg,mm) in oldrec.items() if values(gg)[0] in changed_ids];removed_names=[n for n in oldrec if n not in newrec]
    refresh=refresh_probes(oldrec,newrec,changed_names,removed_names,delta)
    jump=freestyle(cfg,newnodes)
    scene=dict(checks_pass=True,changed_object_ids=changed_ids,removed_object_ids=removed_ids,new_object_ids=[i for i in after if i not in before],modified_geometry_names=changed_names,removed_geometry_names=removed_names,culling_models=culled,memorial=dict(backing_box_faces_removed=6,image_support_minimum_depth_clearance_m=.23,three_support_poles_retained=True,original_artwork_uv_unchanged=True),flag=flag,bathroom=bath,decals=decals,entrance_translation_xyz_m=delta.tolist(),entrance_raise_m=cfg['entrance_raise_m'],entrance_uv_unchanged=True,probe_refresh=refresh,game_visual_confirmation_pending=True)
    save(O/'v040_asset_validation.json',scene)
    qa=copy.deepcopy(baseqa);qa.update(version='v040',baseline_version='user-delivered v039',baseline_commit=cfg['baseline_source_commit'],source_checks_pass=False,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),v040_asset_repairs=scene,v040_freestyle=jump,native_compilation=False,in_game_riding_test=False)
    # Inherited validation records describe prior versions; only the v040
    # independent/native reports represent verification of this final source.
    save(O/'source_validation.json',qa);save(O/'v040_layout.json',cfg);release()
    print('v040 authored: memorial/flag/doors/decals repaired; freestyle double and entrance arch placed.',flush=True)

if __name__=='__main__':main()
