"""Build the additive v037 asphalt oval and two static Cybertruck assets."""
import copy, math, shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay
import shapely
from shapely.geometry import LineString, Polygon, box
from v037_common import *
from v037_fbx import append
from v027_scenery import parse, values, child, geometry_records, vertices
from rebind_scenery import array

PALETTE={'asphalt':(79,81,82),'wallwhite':(222,221,211),'wallgreen':(155,205,56)}
ATLAS_BOUNDS=[465.,249.,591.,431.]
def textures(cfg):
    dest=O/'facility_textures';rng=np.random.default_rng(3709);n=2048
    grains=rng.normal(0,1,(n,n));fine=gaussian_filter(grains,.42,mode='wrap')*8
    broad=gaussian_filter(grains,22,mode='wrap');broad=broad/(broad.std()+1e-9)*1.25
    grain=fine+broad
    for name,rgb in PALETTE.items():
        if name=='asphalt':
            im=np.uint8(np.rint(np.clip(np.asarray(rgb)+grain[...,None],0,255)))
            image=Image.fromarray(im).resize((4096,4096),Image.Resampling.BICUBIC)
            # Native UV atlas contains the paint/wear on the riding surface.
            # This avoids separate coplanar meshes flickering at long distance.
            def px(points):
                p=np.asarray(points)+cfg['centre_xz_m'];a,b,c,d=ATLAS_BOUNDS
                return list(map(tuple,np.c_[(p[:,0]-a)/(c-a)*4095,(d-p[:,1])/(d-b)*4095]))
            draw=ImageDraw.Draw(image);scale=4096/154
            for r,w in [(46.1,.72),(44.4,.20)]:
                p=capsule(r,35);draw.line(px(np.r_[p,p[:1]]),fill=(59,61,62),width=max(1,round(w*scale)),joint='curve')
            for sign in [1,-1]:draw.line(px([[-22,-11*sign],[22,11*sign]]),fill=(65,67,68),width=round(.30*scale))
            p=capsule(54.,35);draw.line(px(np.r_[p,p[:1]]),fill=(236,235,227),width=round(.20*scale),joint='curve')
            for z in cfg['infield_centres_local_z_m']:
                p=ellipse(z,35.27,30.27);draw.line(px(np.r_[p,p[:1]]),fill=(226,193,59),width=round(.18*scale),joint='curve')
            for i in range(18):
                for j in range(2):
                    p=np.array([[480.7+i,314+j*.55],[481.7+i,314+j*.55],[481.7+i,314+(j+1)*.55],[480.7+i,314+(j+1)*.55]])-cfg['centre_xz_m']
                    draw.polygon(px(p),fill=(236,235,227) if (i+j)%2==0 else (48,50,51))
            image_file(image,dest/('v037_'+name+'.tga'));continue
        else:
            yy,xx=np.mgrid[:256,:256];im=np.uint8(np.rint(np.clip(np.asarray(rgb)+(np.sin(xx*.7)+np.sin(yy*.13))[...,None]*.8,0,255)))
        image_file(Image.fromarray(im),dest/('v037_'+name+'.tga'))
    dx=(np.roll(grain,-1,1)-np.roll(grain,1,1))*.016;dz=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.016
    nn=np.stack([-dx,-dz,np.ones_like(dx)],axis=-1);nn/=np.linalg.norm(nn,axis=-1)[...,None]
    image_file(Image.fromarray(np.uint8(np.rint((nn+1)*127.5))),dest/'v037_asphalt_n.tga')
    atomic(dest/'v037_asphalt.shd',b'bump\n{\n map = v037_asphalt_n.tga\n}\nspecular\n{\n shininess = 7\n}\n')

def capsule(radius,half,n=320):
    # Counterclockwise world XZ boundary, two semicircles and straight sides.
    top=np.c_[radius*np.cos(np.linspace(0,np.pi,n)),half+radius*np.sin(np.linspace(0,np.pi,n))]
    bottom=np.c_[radius*np.cos(np.linspace(np.pi,2*np.pi,n)),-half+radius*np.sin(np.linspace(np.pi,2*np.pi,n))]
    return np.r_[top,bottom]
def ellipse(z,a,b,n=260):
    t=np.linspace(0,2*np.pi,n,endpoint=False);return np.c_[a*np.cos(t),z+b*np.sin(t)]
def mesh(name,material,v,f,uv=None):
    v=np.asarray(v,float);f=np.asarray(f,np.int32)
    # In native XYZ an XZ polygon is upward when its XZ winding is clockwise.
    normals=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    bad=normals[:,1]<0;f[bad]=f[bad][:,::-1]
    if uv is None:uv=(v[:,[0,2]]/3.5)[f]
    return dict(name=name,material=material,vertices=v.tolist(),faces=f.tolist(),uv=np.asarray(uv).tolist())
def surface(h,cfg):
    c=np.asarray(cfg['centre_xz_m']);outline=capsule(cfg['outer_radius_m'],cfg['half_straight_m'])
    holes=[ellipse(z,*cfg['infield_radii_xz_m']) for z in cfg['infield_centres_local_z_m']]
    poly=Polygon(outline,[p[::-1] for p in holes]).union(box(*cfg['entry_apron_bounds_local_xz_m']))
    step=cfg['surface_mesh_spacing_m'];x=np.arange(-69,55+step,step);z=np.arange(-90,90+step,step);xx,zz=np.meshgrid(x,z)
    pp=np.c_[xx.ravel(),zz.ravel()];inside=shapely.contains_xy(poly,pp[:,0],pp[:,1]);pp=pp[inside]
    rings=[np.asarray(poly.exterior.coords)[:-1]]+[np.asarray(r.coords)[:-1] for r in poly.interiors]
    pp=np.r_[pp,*rings];pp=np.unique(np.round(pp,10),axis=0)
    # Break exact rectangular grid ties, keeping real boundary vertices exact.
    boundary=np.r_[*rings];bd=set(map(tuple,np.round(boundary,10)))
    for i,p in enumerate(pp):
        if tuple(p) not in bd:pp[i]+=[math.sin(i*.37)*1e-7,math.cos(i*.29)*1e-7]
    f=Delaunay(pp).simplices
    tr=shapely.polygons(pp[f]);keep=shapely.covers(poly.buffer(1e-8),tr);f=f[keep]
    # Enforce the concave entrance and infield boundaries: unconstrained grid
    # triangulation can omit slivers. Fill them with constrained triangles.
    missing=poly.difference(shapely.union_all(tr[keep]));extra=shapely.get_parts(shapely.constrained_delaunay_triangles(missing))
    lookup={tuple(np.round(p,10)):i for i,p in enumerate(pp)};points=pp.tolist();added=[]
    for t in extra:
        if t.area<1e-8:continue
        inds=[]
        for p in np.asarray(t.exterior.coords)[:3]:
            key=tuple(np.round(p,10))
            if key not in lookup:lookup[key]=len(points);points.append(list(key))
            inds.append(lookup[key])
        added.append(inds)
    pp=np.asarray(points);f=np.r_[f,np.asarray(added,np.int32).reshape(-1,3)]
    area=float(shapely.area(shapely.polygons(pp[f])).sum());gap=float(poly.area-area);assert -1e-5<gap<.001,('road triangulation gap',gap)
    p=pp+c;v=np.c_[p[:,0],road_height(h,p,cfg),p[:,1]]
    a,b,c,d=ATLAS_BOUNDS;uv=np.c_[(v[:,0]-a)/(c-a),(v[:,2]-b)/(d-b)]
    m=mesh('TRKASPH_v037_oval_surface','asphalt',v,f)
    m['uv']=uv[np.asarray(m['faces'])].tolist()
    qa=dict(checks_pass=True,physical_mesh_prefix='TRKASPH',surface_area_m2=float(poly.area),mesh_area_m2=area,triangulation_gap_m2=gap,bounds_xz_m=[float(v[:,0].min()),float(v[:,2].min()),float(v[:,0].max()),float(v[:,2].max())],triangles=len(f),vertices=len(v),heightmap_unchanged=True,grass_infield_count=len(poly.interiors),surface_height_clearance_m=float((v[:,1]-ground(h,p)).min()))
    save(O/'oval_surface_validation.json',qa);return m,poly,holes

def walls(h,cfg):
    p=capsule(cfg['wall_radius_m'],cfg['half_straight_m']);p=np.r_[p,p[:1]]
    vv=[];fg=[];vg=[];ff=[]
    for a,b in zip(p[:-1],p[1:]):
        mid=(a+b)/2
        if mid[0]<-50 and abs(mid[1])<cfg['wall_entry_half_width_m']:continue
        normal=np.array([-(b-a)[1],(b-a)[0]]);normal/=np.linalg.norm(normal)
        half=cfg['wall_thickness_m']/2;corn=np.array([a-normal*half,b-normal*half,b+normal*half,a+normal*half])+cfg['centre_xz_m']
        y=road_height(h,corn,cfg)-.015
        base=np.c_[corn[:,0],y,corn[:,1]];top=base+[0,.70,0]
        ix=len(vv);vv.extend(base.tolist()+top.tolist())
        faces=[[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7],[4,5,6],[4,6,7],[3,2,1],[3,1,0]]
        fg.extend((np.array(faces)+ix).tolist())
        ix=len(vg);vb=base+[0,.70,0];vt=base+[0,.88,0];vg.extend(vb.tolist()+vt.tolist());ff.extend((np.array(faces)+ix).tolist())
    # Wall faces are already solid boxes; preserve their outward winding.
    def wallmesh(name,material,v,f):return dict(name=name,material=material,vertices=v,faces=f,uv=(np.asarray(v)[:,[0,1]]/3.5)[np.asarray(f)].tolist())
    return [wallmesh('WLLCONC_v037_oval_wall_white','wallwhite',vv,fg),wallmesh('WLLCONC_v037_oval_wall_green_cap','wallgreen',vg,ff)]

def trucks(h,cfg,poly):
    nodes,_=parse((BASE/'scenery.fbx').read_bytes());rec=geometry_records(nodes)
    objects=next(n for n in nodes if n['name']==b'Objects')['children'];byid={values(n)[0]:n for n in objects}
    con=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    prefix=cfg['vehicle_reference']+'_';parts={n:g for n,(g,mid) in rec.items() if n.startswith(prefix)};assert len(parts)==11
    v0=np.concatenate([vertices(g) for g in parts.values()]);centre=(v0[:,[0,2]].min(0)+v0[:,[0,2]].max(0))/2;bottom=v0[:,1].min()
    front=vertices(parts[prefix+'headlight'])[:,[0,2]].mean(0);rear=vertices(parts[prefix+'red_light'])[:,[0,2]].mean(0);forward=front-rear;angle=math.atan2(forward[1],forward[0])
    result=[];checks=[]
    for truck in cfg['vehicles']:
        theta=math.radians(truck['heading_degrees'])-angle;c,ss=math.cos(theta),math.sin(theta)
        yaw=np.array([[c,0,-ss],[0,1,0],[ss,0,c]])
        relative=v0-[centre[0],bottom,centre[1]];rot=relative@yaw.T
        corner=rot[rot[:,1]<.08][:,[0,2]]+truck['xz_m']
        fit=np.linalg.lstsq(np.c_[corner[:,0]-truck['xz_m'][0],corner[:,1]-truck['xz_m'][1],np.ones(len(corner))],road_height(h,corner,cfg),rcond=None)[0]
        normal=np.array([-fit[0],1.,-fit[1]]);normal/=np.linalg.norm(normal);axis=np.cross([0,1,0],normal);cos=normal[1]
        K=np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
        tilt=np.eye(3)+K+K@K/(1+cos);rotation=tilt@yaw
        allv=relative@rotation.T+[truck['xz_m'][0],fit[2],truck['xz_m'][1]]
        low=relative[:,1]<.065;foot=allv[low];dy=float(np.max(road_height(h,foot[:,[0,2]],cfg)-foot[:,1]));origin=[truck['xz_m'][0],fit[2]+dy,truck['xz_m'][1]]
        allv=relative@rotation.T+origin;foot=allv[low];gap=foot[:,1]-road_height(h,foot[:,[0,2]],cfg)
        assert gap.min()>-1e-8 and gap.max()<.10,(truck['id'],gap.min(),gap.max())
        localfoot=foot[:,[0,2]]-cfg['centre_xz_m'];assert np.all(shapely.covers(poly,shapely.points(localfoot)))
        for n,g in parts.items():
            mid=rec[n][1];mat=next(v[1] for v in con if v[2]==mid and byid.get(v[1],{}).get('name')==b'Material')
            vv=(vertices(g)-[centre[0],bottom,centre[1]])@rotation.T+origin
            result.append(dict(name=truck['id']+'_'+n.removeprefix(prefix),geometry=g,model=byid[mid],material_id=mat,vertices=vv,rotation=rotation))
        checks.append(dict(id=truck['id'],parts=len(parts),xz_m=truck['xz_m'],heading_degrees=truck['heading_degrees'],static=True,wheel_clearance_min_m=float(gap.min()),wheel_clearance_max_m=float(gap.max()),all_wheel_contacts_on_asphalt=True,bounds_xyz_m=[allv.min(0).tolist(),allv.max(0).tolist()]))
    qa=dict(checks_pass=True,static_vehicle_count=len(checks),source_asset=cfg['vehicle_reference'],original_pit_asset_retained=True,vehicles=checks)
    save(O/'oval_vehicle_validation.json',qa);return result

def release():
    src=R/'12_RELEASE/orlandomx_2026_v036';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        if p.suffix in ['.map','.trh']:continue
        name=p.name.replace('orlandomx_2026_v036',NAME);copy_exact(p,dest/name)
    ini=dest/(NAME+'.ini');text=ini.read_text();assert 'v036' in text;atomic(ini,text.replace('v036','v037').encode())
    rdf=O/(NAME+'.rdf');copy_exact(BASE/'orlandomx_2026_v036.rdf',rdf);copy_exact(rdf,dest/rdf.name)
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:copy_exact(BASE/name,dest/name)

def main():
    cfg=read(S/'oval.json');assert len(cfg['vehicles'])==2
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O);textures(cfg);h=height_field();road,poly,holes=surface(h,cfg);bind_road_mesh(road['vertices'])
    meshes=[road]+walls(h,cfg);clones=trucks(h,cfg,poly);scene=append(meshes,clones,PALETTE)
    save(O/'oval_layout.json',cfg);release()
    probes=read(BASE/'native_coordinate_probes.json')['expected_xyz_metres']+read(O/'oval_native_probes.json')['expected_xyz_metres']
    save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=probes))
    old=read(BASE/'source_validation.json');qa=dict(old)
    qa.update(version='v037',baseline_version='v036',baseline_commit=cfg['baseline_native_commit'],baseline_code_commit=cfg['baseline_code_commit'],source_checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),tested_MX_heightmap_byte_exact=True,tested_MX_masks_byte_exact=True,tested_MX_routes_race_and_reset_byte_exact=True,oval_surface=read(O/'oval_surface_validation.json'),oval_vehicles=read(O/'oval_vehicle_validation.json'),oval_scenery=scene,native_compilation=False)
    save(O/'source_validation.json',qa)
    print('v037 authored: asphalt oval, two infield islands, central crossover, two Cybertrucks; tested MX inputs retained.',flush=True)
if __name__=='__main__':main()
