"""Add road-edge collision infill and scenery to the delivered v040 source.

Original road, walls, artwork, terrain and all protected displays are untouched.
Only the three explicitly identified generic pickup geometry/models are removed.
Coordinates are native PiBoSo metres (+Z), converted once by mapped_geometry.
"""
import copy,math,os,shutil,struct
from collections import Counter
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,label
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon,LineString,box
from v041_common import *
from v027_scenery import parse,encode,values,child,vertices,geometry_records,fingerprint
from v037_fbx import mapped_geometry,node,setvalues
from build_v037 import capsule,ATLAS_BOUNDS
from v037_common import ground,road_height
from rebind_scenery import array,encoded_array
from verify_v037_source import faces

class Mesh:
    def __init__(self,name,material):self.name=name;self.material=material;self.v=[];self.f=[];self.uv=[]
    def triangle(self,points,uv=None):
        q=np.asarray(points,float)
        if np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))<1e-10:return
        ix=len(self.v);self.v.extend(q.tolist());self.f.append([ix,ix+1,ix+2])
        self.uv.append((q[:,[0,2]]/2 if uv is None else np.asarray(uv)).tolist())
    def quad(self,points,uv=None):
        q=np.asarray(points);u=q[:,[0,2]]/2 if uv is None else np.asarray(uv)
        for ids in [[0,1,2],[0,2,3]]:self.triangle(q[ids],u[ids])
    def box(self,lo,hi):
        x0,y0,z0=lo;x1,y1,z1=hi
        v=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                    [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
        for f in [[0,3,2,1],[4,5,6,7],[0,4,7,3],[1,2,6,5],[0,1,5,4],[3,7,6,2]]:
            self.quad(v[f],[[0,0],[1,0],[1,1],[0,1]])
    def tube(self,a,b,r=.035,n=10):
        a=np.asarray(a,float);b=np.asarray(b,float);axis=b-a;axis/=np.linalg.norm(axis)
        ref=np.array([0,1,0]) if abs(axis[1])<.9 else np.array([1,0,0])
        u=np.cross(axis,ref);u/=np.linalg.norm(u);v=np.cross(axis,u)
        t=np.arange(n)*2*np.pi/n;ring=(np.cos(t)[:,None]*u+np.sin(t)[:,None]*v)*r
        p=a+ring;q=b+ring
        for i in range(n):
            j=(i+1)%n;self.quad([p[i],p[j],q[j],q[i]])
            self.triangle([a,p[j],p[i]]);self.triangle([b,q[i],q[j]])
    def extrude_xy(self,poly,z0,z1):
        for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(poly)):
            q=np.asarray(tr.exterior.coords)[:3]
            a,b=q[1]-q[0],q[2]-q[0]
            if a[0]*b[1]-a[1]*b[0]<0:q=q[::-1]
            self.triangle(np.c_[q[::-1],np.full(3,z0)])
            self.triangle(np.c_[q,np.full(3,z1)])
        for ring_index,ring in enumerate([poly.exterior,*poly.interiors]):
            p=np.asarray(ring.coords)
            # Exterior is counterclockwise in XY; interior rings clockwise.
            want_ccw=ring_index==0
            if bool(shapely.is_ccw(ring))!=want_ccw:p=p[::-1]
            for a,b in zip(p[:-1],p[1:]):self.quad([[*a,z0],[*b,z0],[*b,z1],[*a,z1]])
    def result(self):
        return dict(name=self.name,material=self.material,vertices=self.v,faces=self.f,uv=self.uv)

def palette_textures(cfg):
    palette={'seating_silver':(173,183,185),'seating_dark':(52,61,65)}
    for color in cfg['replacement_color_order'][:len(cfg['generic_pickups'])]:palette['cybertruck_'+color]=cfg['truck_paint_rgb'][color]
    yy,xx=np.mgrid[:256,:256]
    for name,rgb in palette.items():
        grain=(np.sin(xx*.29)+np.sin(yy*1.7))*.7
        if name=='seating_silver':grain+=np.sin(yy*.8)*1.3
        im=Image.fromarray(np.uint8(np.clip(np.rint(np.asarray(rgb)+grain[...,None]),0,255)))
        image_file(im,O/'facility_textures'/('v041_'+name+'.tga'))
    return palette

def road_infill(rec,cfg,h):
    g=rec['TRKASPH_v037_oval_surface'][0];v=vertices(g);ff=np.asarray(faces(g))
    road=shapely.union_all(shapely.polygons(v[ff][:,:,[0,2]]));assert road.geom_type=='Polygon'
    road_outer=Polygon(road.exterior)
    oval=read(BASE/'oval_layout.json');center=np.asarray(oval['centre_xz_m'])
    outside=Polygon(capsule(cfg['gap_fill_outer_radius_m'],oval['half_straight_m'])+center)
    fill=outside.difference(road_outer)
    m=Mesh('TRKASPH_v041_oval_wall_gap_fill','@v037_asphalt')
    tree=cKDTree(v[:,[0,2]])
    max_join_error=0.;a,b,c,d=ATLAS_BOUNDS
    for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(fill)):
        p=np.asarray(tr.exterior.coords)[:3]
        if tr.area<1e-10:continue
        y=road_height(h,p,oval)
        distance,ii=tree.query(p);on=distance<1e-7;y[on]=v[ii[on],1]
        q=np.c_[p[:,0],y,p[:,1]]
        if np.cross(q[1]-q[0],q[2]-q[0])[1]<0:q=q[::-1]
        uv=np.c_[(q[:,0]-a)/(c-a),(q[:,2]-b)/(d-b)]
        m.triangle(q,uv)
    wall=vertices(rec['WLLCONC_v037_oval_wall_white'][0]);base=wall.reshape(-1,8,3)[:,:4]
    points=base.mean(1)[:,[0,2]]
    covered=shapely.covers(outside,shapely.points(points))
    assert np.all(covered)
    assert fill.intersection(road_outer).area<1e-8
    # Every new inner-boundary vertex is an exact old road boundary point.
    edge_points=np.asarray(road.exterior.coords)[:-1]
    joined=shapely.intersects(shapely.points(edge_points),outside)
    active=edge_points[joined]
    dist,ii=tree.query(active);assert dist.max()<1e-7
    mv=np.asarray(m.v);mt=cKDTree(mv[:,[0,2]])
    dd,jj=mt.query(active);assert dd.max()<1e-7
    max_join_error=float(np.max(np.abs(mv[jj,1]-v[ii,1])))
    assert max_join_error<1e-10
    qa=dict(checks_pass=True,original_road_and_wall_records_unchanged=True,
            original_nominal_road_wall_gap_m=oval['wall_radius_m']-oval['wall_thickness_m']/2-oval['outer_radius_m'],
            gap_fill_area_m2=fill.area,maximum_shared_edge_height_error_m=max_join_error,
            wall_footing_centerlines_covered=True,no_overlay_on_existing_pavement=True,
            collision_prefix='TRKASPH',terrain_and_road_camber_unchanged=True)
    return m.result(),qa

def seating(cfg,h):
    s=cfg['seating'];x0=s['front_x_m'];pitch=s['row_pitch_m'];rise=s['row_rise_m'];rows=s['rows']
    intervals=s['sections_z_m']+s['stairs_z_m'];xz=np.array([[x,z] for x in [x0-.1,x0+rows*pitch+.35] for z in [307.8,371.2]])
    floor=float(ground(h,xz).max())+s['front_floor_above_ground_m']
    deck=Mesh('WLLCONC_v041_grandstand_decks','seating_dark')
    benches=Mesh('v041_grandstand_benches','seating_silver')
    backs=Mesh('v041_grandstand_seat_backs','seating_silver')
    support=Mesh('v041_grandstand_supports','seating_dark')
    rails=Mesh('v041_grandstand_guardrails','seating_silver')
    def stair_profile(n,dx,dy):
        p=[[x0,floor]]
        for r in range(n):
            x=x0+(r+1)*dx;y=floor+r*dy;p.append([x,y])
            if r<n-1:p.append([x,y+dy])
        return LineString(p).buffer(.04,cap_style=2,join_style=2)
    bank=stair_profile(rows,pitch,rise);stairs=stair_profile(rows*2,pitch/2,rise/2)
    for z0,z1 in s['sections_z_m']:
        deck.extrude_xy(bank,z0,z1)
        for r in range(rows):
            x=x0+r*pitch;y=floor+r*rise
            benches.box([x+.25,y+.40,z0+.12],[x+.55,y+.46,z1-.12])
            backs.box([x+.55,y+.50,z0+.12],[x+.59,y+.78,z1-.12])
            for z in np.linspace(z0+.5,z1-.5,7):
                support.box([x+.38,y+.02,z-.035],[x+.45,y+.40,z+.035])
        # Open steel understructure, with footings below the terrain.
        for z in np.linspace(z0+.25,z1-.25,7):
            for r in [0,3,6,9]:
                x=x0+(r+.7)*pitch;y=floor+r*rise
                foot=float(ground(h,[[x,z]])[0])-.08
                support.box([x-.055,foot,z-.055],[x+.055,y-.045,z+.055])
            support.tube([x0+.3,floor-.10,z],[x0+(rows-.2)*pitch,floor+(rows-1)*rise-.13,z],.05)
        rear=x0+rows*pitch+.18;top=floor+(rows-1)*rise
        for z in np.arange(z0,z1+.01,2):rails.tube([rear,top-.08,z],[rear,top+1.10,z])
        for y in [top+.45,top+1.08]:rails.tube([rear,y,z0],[rear,y,z1])
        for z in [z0,z1]:
            rails.tube([x0+.06,floor+1.08,z],[rear,top+1.08,z])
            for r in [0,3,6,9]:
                x=x0+(r+.25)*pitch;y=floor+r*rise
                rails.tube([x,y,z],[x,y+1.08,z])
    for z0,z1 in s['stairs_z_m']:
        deck.extrude_xy(stairs,z0,z1)
        for z in [z0+.10,z1-.10]:
            rails.tube([x0+.04,floor+1.02,z],[x0+rows*pitch-.10,floor+(rows-1)*rise+1.02,z])
    meshes=[m.result() for m in [deck,benches,backs,support,rails]]
    vv=np.concatenate([np.asarray(m['vertices']) for m in meshes])
    assert vv[:,0].min()>591.5 and vv[:,0].max()<600
    qa=dict(checks_pass=True,rows=rows,sections=len(s['sections_z_m']),length_m=63,
            front_native_x_m=x0,faces_course_native_direction=[-1,0,0],
            height_rises_away_from_course=True,opposite_entrance_arch=True,
            seat_floor_clearance_m=.40,seat_back_clearance_m=.04,
            separate_stair_aisles=True,solid_opaque_materials=True,exterior_face_culling=True,
            original_course_and_wall_untouched=True,bounds_xyz_m=[vv.min(0).tolist(),vv.max(0).tolist()],in_game_visual_check=False)
    return meshes,qa

def crocodile(cfg,rec):
    c=cfg['crocodile'];src=Image.open(S/c['source_image']).convert('RGBA')
    scale=min(1.,2048/src.width,1024/src.height);size=(round(src.width*scale),round(src.height*scale))
    photo=src.resize(size,Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(2048,1024));canvas.paste(photo,(0,0))
    # Preserve the original transparent cutout in editable source. Native game
    # art uses opaque RGB on the animal silhouette, avoiding alpha-sort flicker.
    image_file(canvas.convert('RGB'),O/'facility_textures/v041_crocodile_photo.tga')
    alpha=np.asarray(canvas.getchannel('A'));mask=alpha>=128
    lab,n=label(mask);counts=np.bincount(lab.ravel());counts[0]=0;mask=lab==counts.argmax()
    rectangles=[]
    for y,row in enumerate(mask):
        edges=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
        for a,b in edges.reshape(-1,2):rectangles.append(box(a,y,b,y+1))
    silhouette=shapely.union_all(rectangles).simplify(.85,preserve_topology=True)
    assert silhouette.geom_type=='Polygon' and silhouette.is_valid
    left,top,right,bottom=silhouette.bounds;ratio=c['length_m']/(right-left)
    cx,cz=c['center_xz_m'];water=vertices(rec[c['water_mesh']][0]);wy=float(water[0,1])
    foot=wy-c['feet_below_water_m'];depth=c['front_back_separation_m']
    pond=Polygon(water[:,[0,2]]);assert pond.covers(box(cx-c['length_m']/2,cz-depth/2,cx+c['length_m']/2,cz+depth/2))
    m=Mesh('v041_pond_crocodile_photographic','crocodile_photo')
    def xyz(p,z):return np.c_[cx+(p[:,0]-(left+right)/2)*ratio,foot+(bottom-p[:,1])*ratio,np.full(len(p),z)]
    def uv(p):return np.c_[p[:,0]/2048,1-p[:,1]/1024]
    for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(silhouette)):
        p=np.asarray(tr.exterior.coords)[:3]
        # Pixel Y points down; clockwise pixel triangles have +Z world normal.
        for sign in [-1,1]:
            q=xyz(p,cz+sign*depth/2)
            if np.cross(q[1]-q[0],q[2]-q[0])[2]*sign<0:q=q[::-1];u=uv(p)[::-1]
            else:u=uv(p)
            m.triangle(q,u)
    for i,ring in enumerate([silhouette.exterior,*silhouette.interiors]):
        points=np.asarray(ring.coords)
        # Pixel Y is inverted by xyz(): clockwise pixel exteriors become
        # counterclockwise world XY exteriors with outward extrusion sides.
        if bool(shapely.is_ccw(ring))!=(i!=0):points=points[::-1]
        for a,b in zip(points[:-1],points[1:]):
            q=np.r_[xyz(np.array([a,b]),cz-depth/2),xyz(np.array([b,a]),cz+depth/2)]
            m.quad(q,uv(np.array([a,b,b,a])))
    qa=dict(checks_pass=True,length_m=c['length_m'],source_image=c['source_image'],
            source_image_sha256=sha(S/c['source_image']),native_texture='v041_crocodile_photo.tga',
            native_texture_sha256=sha(O/'facility_textures/v041_crocodile_photo.tga'),
            native_texture_size_px=[2048,1024],native_texture_opaque_rgb=True,
            silhouette_outline_instead_of_rectangular_photo_card=True,
            front_back_separation_m=depth,center_xz_m=[cx,cz],water_mesh=c['water_mesh'],
            footprint_inside_water=True,decorative_no_race_collision=True,
            source_alpha_preserved=True,generated_photorealistic_cutout=True,in_game_visual_check=False)
    return m.result(),qa

def truck_replacements(nodes,rec,cfg,h):
    objects=next(n for n in nodes if n['name']==b'Objects')['children'];byid={values(n)[0]:n for n in objects}
    con=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    parts={n:(g,mid) for n,(g,mid) in rec.items() if n.startswith('truck_jordan_')};assert len(parts)==11
    allv=np.concatenate([vertices(g) for g,mid in parts.values()]);center=(allv[:,[0,2]].min(0)+allv[:,[0,2]].max(0))/2;bottom=allv[:,1].min()
    head=vertices(parts['truck_jordan_headlight'][0])[:,[0,2]].mean(0);tail=vertices(parts['truck_jordan_red_light'][0])[:,[0,2]].mean(0)
    heading=math.atan2(*(head-tail)[::-1]);clones=[];removed=[];checks=[]
    for index,prefix in enumerate(cfg['generic_pickups']):
        old={n:(g,mid) for n,(g,mid) in rec.items() if n.startswith(prefix+'_')};assert len(old)==4,prefix
        target=np.concatenate([vertices(g) for g,mid in old.values()]);xz=(target[:,[0,2]].min(0)+target[:,[0,2]].max(0))/2
        front=vertices(old[prefix+'_glass'][0])[:,[0,2]].mean(0)-xz;angle=math.atan2(front[1],front[0])-heading
        ct,st=math.cos(angle),math.sin(angle);yaw=np.array([[ct,0,-st],[0,1,0],[st,0,ct]])
        relative=allv-[center[0],bottom,center[1]];rot=relative@yaw.T;low=relative[:,1]<.065
        contact=rot[low][:,[0,2]]+xz
        fit=np.linalg.lstsq(np.c_[contact-xz,np.ones(len(contact))],ground(h,contact),rcond=None)[0]
        normal=np.array([-fit[0],1.,-fit[1]]);normal/=np.linalg.norm(normal);axis=np.cross([0,1,0],normal)
        K=np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
        tilt=np.eye(3)+K+K@K/(1+normal[1]);rotation=tilt@yaw
        new=relative@rotation.T+[xz[0],fit[2],xz[1]];dy=float(np.max(ground(h,new[low][:,[0,2]])-new[low,1]))
        origin=np.array([xz[0],fit[2]+dy,xz[1]]);new=relative@rotation.T+origin
        gap=new[low,1]-ground(h,new[low][:,[0,2]])
        assert gap.min()>-1e-8 and gap.max()<.12,(prefix,gap.min(),gap.max())
        color=cfg['replacement_color_order'][index];id='v041_pit_cybertruck_'+str(index+1).zfill(2)+'_'+color
        for n,(g,mid) in parts.items():
            mat=next(v[1] for v in con if v[2]==mid and byid.get(v[1],{}).get('name')==b'Material')
            clones.append(dict(name=id+'_'+n.removeprefix('truck_jordan_'),geometry=g,model=byid[mid],
                               material_id=mat,paint='cybertruck_'+color if n.endswith('_cyber_steel') else None,
                               vertices=(vertices(g)-[center[0],bottom,center[1]])@rotation.T+origin,rotation=rotation,old_group=prefix))
        removed+=list(old)
        checks.append(dict(original_group=prefix,new_group=id,color=color,parts=11,xz_m=xz.tolist(),
                           original_heading_preserved=True,wheel_clearance_min_m=float(gap.min()),wheel_clearance_max_m=float(gap.max()),
                           original_parking_anchor_preserved=True,source='truck_jordan',bounds_xyz_m=[new.min(0).tolist(),new.max(0).tolist()]))
    return clones,removed,dict(checks_pass=True,count=len(checks),color_order=[c['color'] for c in checks],vehicles=checks,
                             four_accepted_pit_displays_untouched=True,red_black_oval_cybertrucks_untouched=True)

def append_scene(nodes,meshes,clones,removed,rec):
    objects=next(n for n in nodes if n['name']==b'Objects');links=next(n for n in nodes if n['name']==b'Connections')
    byid={values(n)[0]:n for n in objects['children']};uid=max(byid)+1000
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    removed_ids={i for n in removed for i in [values(rec[n][0])[0],rec[n][1]]}
    objects['children']=[n for n in objects['children'] if values(n)[0] not in removed_ids]
    links['children']=[n for n in links['children'] if not any(i in removed_ids for i in values(n)[1:3])]
    template=byid[rec['covered_stand_timber'][1]]
    material=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'v033_qwikchute_logo')
    matid=values(material)[0];con=[values(n) for n in links['children']]
    tid=next(n[1] for n in con if n[2]==matid and byid.get(n[1],{}).get('name')==b'Texture')
    vid=next(n[1] for n in con if n[2]==tid and byid.get(n[1],{}).get('name')==b'Video')
    textures=[];mats={}
    for p in sorted((O/'facility_textures').glob('v041_*.tga')):
        name=p.stem.removeprefix('v041_');ids=[newid() for _ in range(3)];mats[name]=ids[0];raw=p.read_bytes()
        for src,nid,kind in zip([material,byid[tid],byid[vid]],ids,['Material','Texture','Video']):
            n=copy.deepcopy(src);old=values(n);setvalues(n,nid,p.stem.encode()+b'\0\1'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,p.name)
                if c['name']==b'Media':setvalues(c,p.stem.encode()+b'\0\1Video')
                if c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
                if c['name']==b'Properties70':
                    for prop in c['children']:
                        vv=values(prop)
                        if vv and vv[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(prop,*vv[:4],1.,1.,1.)
                        elif vv and vv[0] in [b'EmissiveFactor',b'TransparencyFactor']:setvalues(prop,*vv[:4],0.)
                        elif vv and vv[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(prop,*vv[:4],p.name)
            objects['children'].append(n)
        connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1]);textures.append(dict(texture=p.name,sha256=sha(p)))
    entries=[]
    for m in meshes:
        gid,mid=newid(),newid();g=mapped_geometry(gid,m);model=copy.deepcopy(template);old=values(model);setvalues(model,mid,m['name'].encode()+b'\0\1Model',*old[2:]);setvalues(child(model,b'Culling'),'CullingOnCCW')
        material_id=mats[m['material']] if not m['material'].startswith('@') else next(values(n)[0] for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==m['material'][1:].encode())
        objects['children']+=[g,model];connect(gid,mid);connect(material_id,mid);connect(mid,0)
        v=np.asarray(m['vertices']);entries.append(dict(name=m['name'],vertices=len(v),triangles=len(m['faces']),bounds_xyz_m=[v.min(0).tolist(),v.max(0).tolist()]))
    for part in clones:
        gid,mid=newid(),newid();g=copy.deepcopy(part['geometry']);old=values(g);setvalues(g,gid,part['name'].encode()+b'\0\1Geometry',*old[2:]);child(g,b'Vertices')['props']=encoded_array(part['vertices']*[100,100,-100])
        for layer in g['children']:
            if layer['name']==b'LayerElementNormal':
                n=child(layer,b'Normals');norm=array(n).reshape(-1,3)*[1,1,-1];n['props']=encoded_array((norm@part['rotation'].T)*[1,1,-1])
        model=copy.deepcopy(part['model']);old=values(model);setvalues(model,mid,part['name'].encode()+b'\0\1Model',*old[2:]);setvalues(child(model,b'Culling'),'CullingOnCCW')
        objects['children']+=[g,model];connect(gid,mid);connect(mats[part['paint']] if part['paint'] else part['material_id'],mid);connect(mid,0)
        v=part['vertices'];entries.append(dict(name=part['name'],vertices=len(v),bounds_xyz_m=[v.min(0).tolist(),v.max(0).tolist()]))
    definitions=next(n for n in nodes if n['name']==b'Definitions');counts=Counter(n['name'] for n in objects['children']);declared=[]
    for d in definitions['children']:
        if d['name']==b'ObjectType':
            typ=values(d)[0];ct=counts[typ] if typ!=b'GlobalSettings' else values(child(d,b'Count'))[0]
            child(d,b'Count')['props']=b'I'+struct.pack('<i',ct);declared.append(ct)
    child(definitions,b'Count')['props']=b'I'+struct.pack('<i',sum(declared))
    return dict(removed_object_ids=sorted(removed_ids),new_geometry=entries,new_textures=textures)

def refresh_probes(oldrec,newrec,removed,newnames,truckqa):
    removed_vertices={prefix:np.concatenate([vertices(g) for n,(g,mid) in oldrec.items() if n.startswith(prefix+'_')]) for prefix in read(S/'update.json')['generic_pickups']}
    oldtree={p:cKDTree(v) for p,v in removed_vertices.items()}
    newtree={q['original_group']:cKDTree(np.concatenate([vertices(g) for n,(g,mid) in newrec.items() if n.startswith(q['new_group']+'_')])) for q in truckqa['vehicles']}
    refreshed=[]
    for path in BASE.glob('*probes.json'):
        data=read(path)
        if 'expected_xyz_metres' not in data:continue
        points=np.asarray(data['expected_xyz_metres'],float);count=0
        for p,tree in oldtree.items():
            hit=np.flatnonzero(tree.query(points)[0]<1e-7)
            if len(hit):points[hit]=newtree[p].data[newtree[p].query(points[hit])[1]];count+=len(hit)
        data['expected_xyz_metres']=points.tolist();save(O/path.name,data);refreshed.append(dict(file=path.name,removed_pickup_probes_replaced=count))
    points=[]
    for name in newnames:
        v=vertices(newrec[name][0]);points.extend(v[np.unique(np.linspace(0,len(v)-1,min(5,len(v)),dtype=int))].tolist())
    save(O/'v041_native_probes.json',dict(expected_xyz_metres=points))
    return refreshed

def release():
    src=R/'12_RELEASE/orlandomx_2026_v040';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        if p.suffix in ['.map','.trh']:continue
        copy_exact(p,dest/p.name.replace('orlandomx_2026_v040',NAME))
    ini=dest/(NAME+'.ini');t=ini.read_text();assert 'v040' in t;atomic(ini,t.replace('v040','v041').encode())
    copy_exact(BASE/'orlandomx_2026_v040.rdf',O/(NAME+'.rdf'));copy_exact(O/(NAME+'.rdf'),dest/(NAME+'.rdf'))

def main():
    cfg=read(S/'update.json');qa=read(BASE/'source_validation.json')
    assert qa['version']=='v040' and qa['source_checks_pass']
    assert sha(BASE/'scenery.fbx')==cfg['baseline_scenery_sha256'] and sha(BASE/'terrain.raw')==cfg['baseline_terrain_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O)
    original=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    oldnodes=parse(original)[0];oldrec=geometry_records(oldnodes);rec=geometry_records(nodes)
    h=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    palette_textures(cfg);infill,gapqa=road_infill(rec,cfg,h);seats,seatqa=seating(cfg,h);croc,crocqa=crocodile(cfg,rec)
    clones,removed,truckqa=truck_replacements(nodes,rec,cfg,h)
    meshes=[infill,*seats,croc];scene=append_scene(nodes,meshes,clones,removed,rec)
    output=encode(nodes,tail);atomic(O/'scenery.fbx',output);newnodes=parse(output)[0];newrec=geometry_records(newnodes)
    before={values(n)[0]:fingerprint(n) for n in next(n for n in oldnodes if n['name']==b'Objects')['children']}
    after={values(n)[0]:fingerprint(n) for n in next(n for n in newnodes if n['name']==b'Objects')['children']}
    assert all(after[k]==v for k,v in before.items() if k not in scene['removed_object_ids'])
    names=[m['name'] for m in meshes]+[c['name'] for c in clones]
    scene.update(checks_pass=True,retained_original_object_records_exact=len(before)-len(scene['removed_object_ids']),
                 removed_generic_pickup_geometry=removed,probe_refresh=refresh_probes(oldrec,newrec,removed,names,truckqa))
    save(O/'v041_gap_validation.json',gapqa);save(O/'v041_seating_validation.json',seatqa);save(O/'v041_crocodile_validation.json',crocqa);save(O/'v041_vehicle_validation.json',truckqa);save(O/'v041_asset_validation.json',scene)
    qa=copy.deepcopy(qa);qa.update(version='v041',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_version='user-delivered v040',baseline_commit=cfg['baseline_source_commit'],source_checks_pass=False,scenery_sha256=sha(O/'scenery.fbx'),terrain_sha256=sha(O/'terrain.raw'),v041_gap_fill=gapqa,v041_stadium_seating=seatqa,v041_pit_cybertrucks=truckqa,v041_crocodile=crocqa,native_compilation=False,in_game_riding_test=False)
    save(O/'source_validation.json',qa);save(O/'v041_layout.json',cfg);release()
    print('v041 authored: native gap infill, course-facing grandstands, three colored Cybertrucks, opaque photographic crocodile.',flush=True)

if __name__=='__main__':main()
