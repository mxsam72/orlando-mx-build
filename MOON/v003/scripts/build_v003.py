"""Crater Send: mapped lunar setting, authored crater jumps and half-g flight checks."""
from pathlib import Path
import hashlib, json, math, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates, rotate
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2]; V=ROOT/'v003'; B=V/'build'; G=B/'game'; P=V/'previews'
sys.path.insert(0,str(ROOT/'scripts'))
import build_source as measured
import test_materials as materials
import race_setup as race
NAME='taurus_littrow_mx_v003'; N=2049; SIZE=1600.; DX=SIZE/(N-1); GRAVITY=4.905
SUN=np.array([-8.,4.,-6.]) # native X, vertical Y, north Z
JUMPS=[
 dict(id='J1',name='First Contact',center=[-540,-270],direction=[0,1],radius=100,depth=18,gap=90,angle=32),
 dict(id='J2',name='Rim Reaper',center=[-540,180],direction=[0,1],radius=130,depth=28,gap=160,angle=34),
 dict(id='J3',name='Blue Marble',center=[60,600],direction=[1,0],radius=110,depth=23,gap=120,angle=33),
 dict(id='J4',name='Event Horizon',center=[540,230],direction=[0,-1],radius=135,depth=32,gap=175,angle=34),
 dict(id='J5',name='Dark Side',center=[540,-250],direction=[0,-1],radius=100,depth=20,gap=110,angle=32),
 dict(id='J6',name='Homeward Bound',center=[40,-600],direction=[-1,0],radius=120,depth=26,gap=140,angle=34),
]
HERO=dict(id='H1',name='Shorty Overflight',center=[0,0],direction=[1,0],radius=0,depth=0,gap=220,angle=35,optional=True)

def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def block(n,d):return race.block(n,d)
def sample(h,x,y):
    xx,yy=np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(y))
    return map_coordinates(h,[(800-yy)/DX,(xx+800)/DX],order=1,mode='nearest').squeeze()

def route():
    # Clockwise rounded rectangle, with long straight approaches to every gap.
    paths=[]
    def line(a,b):
        q=np.linspace(a,b,max(2,math.ceil(np.linalg.norm(np.array(b)-a)/.5)),endpoint=False);paths.append(q)
    def arc(c,a0,a1):
        a=np.linspace(math.radians(a0),math.radians(a1),440,endpoint=False)
        paths.append(np.array(c)+140*np.c_[np.cos(a),np.sin(a)])
    line([-540,-460],[-540,460]);arc([-400,460],180,90)
    line([-400,600],[400,600]);arc([400,460],90,0)
    line([540,460],[540,-460]);arc([400,-460],0,-90)
    line([400,-600],[-400,-600]);arc([-400,-460],-90,-180)
    xy=np.vstack(paths);ds=np.linalg.norm(np.roll(xy,-1,axis=0)-xy,axis=1);s=np.r_[0,np.cumsum(ds[:-1])]
    tangent=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    normal=np.c_[-tangent[:,1],tangent[:,0]]
    return s,xy,tangent,normal,float(ds.sum())

def flight_parameters(j):
    angle=math.radians(j['angle']);range_=j['gap']+15
    speed=math.sqrt(range_*GRAVITY/math.sin(2*angle))
    return angle,speed

def ballistic(x,j):
    angle,v=flight_parameters(j)
    return np.tan(angle)*x-GRAVITY*x*x/(2*(v*np.cos(angle))**2)

def ballistic_slope(x,j):
    angle,v=flight_parameters(j)
    return np.tan(angle)-GRAVITY*x/(v*np.cos(angle))**2

def crater_delta(x,y,j):
    r=np.hypot(x-j['center'][0],y-j['center'][1])/j['radius']
    bowl=-j['depth']*(1-smooth((r-.22)/.70))
    rim=6.5*np.exp(-((r-.98)/.135)**2)
    return (bowl+rim)*(1-smooth((r-1.15)/.23))

def sculpt_jump(h,xx,yy,j):
    c=np.array(j['center']);d=np.array(j['direction']);normal=np.array([-d[1],d[0]])
    u=(xx-c[0])*d[0]+(yy-c[1])*d[1];lat=(xx-c[0])*normal[0]+(yy-c[1])*normal[1]
    half=j['gap']/2;run=60.;landing=85.;angle,_=flight_parameters(j)
    start=c+d*(-half-run);start_h=float(sample(h,*start))
    lift=run*np.tan(angle)/2;lip=start_h+lift
    # Flat-tangent entry and the requested launch tangent at the lip.
    takeoff=start_h+lift*np.clip((u+half+run)/run,0,1)**2
    w=smooth((25-np.abs(lat))/9)*smooth((u+half+run+18)/18)*((u<=-half).astype(float))
    h=h*(1-w)+takeoff*w
    # The landing follows the nominal flight tangent at 30 m past its front.
    q=u-half;touch=30.;front=lip+ballistic(j['gap'],j)-5
    initial=lip+ballistic(j['gap']+q,j)-5*(1-smooth(q/touch))
    end=c+d*(half+landing);end_h=float(sample(h,*end))
    join=CubicHermiteSpline([touch,landing],
        [lip+ballistic(j['gap']+touch,j),end_h],
        [ballistic_slope(j['gap']+touch,j),0])
    target=np.where(q<=touch,initial,join(np.clip(q,touch,landing)))
    w=smooth((35-np.abs(lat))/11)*((q>=0)&(q<=landing))
    h=h*(1-w)+target*w
    j.update(runup_profile_m=run,landing_length_m=landing,takeoff_width_m=32,
             landing_width_m=48,launch_height_absolute_m=lip,
             suggested_lip_speed_kmh=round(flight_parameters(j)[1]*3.6,1),
             crater_diameter_m=2*j['radius'],nominal_touchdown_from_lip_m=j['gap']+touch)
    return h

def directional_shadows(h):
    # Source-baked static terrain occlusion. No opaque multi-hour TerrainEd bake.
    u,v=SUN[0],-SUN[2];angle=math.degrees(math.atan2(v,u))-180
    rotated=rotate(h,angle,reshape=True,order=1,mode='constant',cval=-1e6,prefilter=False)
    slope=SUN[1]/math.hypot(SUN[0],SUN[2]);x=np.arange(rotated.shape[1],dtype=np.float32)*DX*slope
    raised=rotated+x[None,:];horizon=np.maximum.accumulate(raised,axis=1)
    delta=horizon-raised;mask=smooth((delta-.12)/.35)
    back=rotate(mask,-angle,reshape=True,order=1,mode='constant',cval=0,prefilter=False)
    rows,cols=h.shape;y0=(back.shape[0]-rows)//2;x0=(back.shape[1]-cols)//2
    return gaussian_filter(back[y0:y0+rows,x0:x0+cols],.7)

def sky():
    rng=np.random.default_rng(170003);w,h=4096,2048
    stars=Image.new('RGB',(w,h));draw=ImageDraw.Draw(stars)
    for i in range(12500):
        x=int(rng.integers(w));y=int(np.arccos(rng.uniform(-1,1))/np.pi*h)
        brightness=int(rng.choice([35,65,110,185,250],p=[.40,.30,.19,.09,.02]))
        color=(int(brightness*.88),int(brightness*.94),brightness)
        draw.point((x,y),fill=color)
    stars.save(B/'NOLIGHTING_v003_stars.tga')
    src=V/'source/earth_blue_marble_nasa.jpg'
    if not src.exists():
        url='https://assets.science.nasa.gov/dynamicimage/assets/science/esd/eo/images/imagerecords/2000/2181/globe_east_lrg.jpg'
        with urllib.request.urlopen(url,timeout=120) as response:src.write_bytes(response.read())
    assert sha(src)=='df0434cf74a06e9dd3c7b9b197b6e215e13db70b4210115969eac9e89f6da502'
    with Image.open(src) as im:
        rgb=np.array(im.convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS))
    # The NASA source is a rendered photographic Earth disk against black space.
    # Preserve the disk's photographic pixels, with transparent space around it.
    brightness=rgb.max(2);alpha=np.uint8(smooth((brightness.astype(float)-2)/8)*255)
    Image.fromarray(np.dstack([rgb,alpha])).save(B/'NOLIGHTING_v003_earth.tga')
    return dict(stars=12500,starfield_pixels=[w,h],earth_source_sha256=sha(src),
                earth_source='https://science.nasa.gov/earth/earth-observatory/the-blue-marble-2181/',
                earth_credit='NASA / Reto Stockli / Robert Simmon / MODIS Science Team',
                earth_angular_diameter_degrees=12,earth_azimuth_degrees=0,earth_elevation_degrees=24,
                artistic_earth_scale_and_placement=True,astronomically_scaled_sky=False)

def main():
    for folder in [B,G,P]:folder.mkdir(parents=True,exist_ok=True)
    s,xy,tangent,normal,L=route();x=np.linspace(-800,800,N,dtype=np.float32);y=x[::-1];xx,yy=np.meshgrid(x,y)
    base,meta=measured.dem_grid('shorty_2m.tif',xx,yy);h=base.copy().astype(np.float32)
    dist,idx=cKDTree(xy).query(np.c_[xx.ravel(),yy.ravel()],workers=4);dist=dist.reshape(N,N);idx=idx.reshape(N,N)
    path_z,_=measured.dem_grid('shorty_2m.tif',xy[:,0],xy[:,1]);path_z=gaussian_filter1d(path_z,18,mode='wrap')
    corridor=smooth((26-dist)/12);h=h*(1-corridor)+path_z[idx]*corridor
    for j in JUMPS:h+=crater_delta(xx,yy,j)
    bypasses=[]
    for j in JUMPS:
        d=np.array(j['direction']);n=np.array([-d[1],d[0]]);a=np.linspace(-np.pi/2,np.pi/2,400)
        r=j['radius']+25;c=np.array(j['center']);q=c+d*(r*np.sin(a))[:,None]-n*(r*np.cos(a))[:,None]
        bypasses.append(q)
        bz,_=measured.dem_grid('shorty_2m.tif',q[:,0],q[:,1]);bz=gaussian_filter1d(bz,10)
        dd,ii=cKDTree(q).query(np.c_[xx.ravel(),yy.ravel()],workers=4);w=smooth((10-dd.reshape(N,N))/5)
        h=h*(1-w)+bz[ii.reshape(N,N)]*w
    for j in JUMPS+[HERO]:h=sculpt_jump(h,xx,yy,j).astype(np.float32)
    # Preserve measured Shorty itself; the optional transfer jumps over it.
    protected=np.hypot(xx,yy)<90;h[protected]=base[protected]
    pit=np.array([-300.,-380.]);pit_h=float(sample(h,*pit));pad=smooth((61-abs(xx-pit[0]))/12)*smooth((34-abs(yy-pit[1]))/10)
    h=h*(1-pad)+pit_h*pad
    lane=np.array([[-350,-380],[-405,-390],[-460,-410],[-540,-430]],float)
    aa=np.linspace(0,3,400);lane=np.c_[np.interp(aa,np.arange(4),lane[:,0]),np.interp(aa,np.arange(4),lane[:,1])]
    ah=np.linspace(pit_h,float(sample(h,*lane[-1])),len(lane));ad,ai=cKDTree(lane).query(np.c_[xx.ravel(),yy.ravel()],workers=4)
    weight=smooth((10-ad.reshape(N,N))/4);h=h*(1-weight)+ah[ai.reshape(N,N)]*weight
    offset=float(math.floor(h.min())-2);scale=float(math.ceil(h.max()-offset)+2)
    raw=np.uint16(np.rint((h-offset)/scale*65535));raw.astype('<u2').tofile(B/'terrain.raw')
    encoded=raw.astype(np.float32)/65535*scale+offset;assert np.max(abs(encoded-h))<.002
    np.savez_compressed(B/'terrain_preview.npz',x=x[::2],y=y[::2],height=encoded[::2,::2]-offset,route_xy=xy,offset=offset)
    np.savez_compressed(B/'design.npz',x=x,y=y,height=encoded-offset,base=base-offset,route_xy=xy,route_s=s,
                        pit=pit,access=lane,bypasses=np.stack(bypasses),offset=offset)
    # Lower-cost scenery retains measured terrain outside the arena.
    near=np.arange(-1680,1681,20,dtype=np.float32);mx,my=np.meshgrid(near,near[::-1]);mh,_=measured.dem_grid('shorty_2m.tif',mx,my)
    np.savez_compressed(B/'mid_preview.npz',x=near,y=near[::-1],height=mh-offset)
    far=np.arange(-11920,11921,160,dtype=np.float32);fx,fy=np.meshgrid(far,far[::-1]);fh,_=measured.dem_grid('valley_context_20m.tif',fx,fy,fill=True)
    radial=np.maximum(abs(fx),abs(fy));blend=radial<1760
    close,_=measured.dem_grid('shorty_2m.tif',fx[blend],fy[blend]);w=np.clip((1760-radial[blend])/80,0,1)
    fh[blend]=fh[blend]*(1-w)+close*w
    np.savez_compressed(B/'context_preview.npz',x=far,y=far[::-1],height=fh-offset)
    materials.B=B;mat=materials.build(xy,s,normal)
    # Native albedo atlas + tiled normal map. Authored ejecta detail is fictional.
    rng=np.random.default_rng(170003);noise=rng.normal(size=(N,N)).astype(np.float32)
    coarse=gaussian_filter(noise,20);coarse/=coarse.std();gray=125+coarse*4+gaussian_filter(noise,1)*5
    for j in JUMPS:
        r=np.hypot(xx-j['center'][0],yy-j['center'][1]);theta=np.arctan2(yy-j['center'][1],xx-j['center'][0])
        gray+=7*np.exp(-((r-j['radius'])/(j['radius']*.20))**2)*(1+.35*np.sin(theta*27+np.sin(theta*9)))
        gray-=6*(1-smooth((r/j['radius']-.15)/.65))
    color=np.uint8(np.clip(np.repeat(gray[:,:,None],3,axis=2),55,175))
    Image.fromarray(color).resize((2048,2048),Image.Resampling.LANCZOS).save(B/'v003_terrain_color.tga')
    materials.shader('v003_terrain_color','v002_regolith_n',800)
    shadow=directional_shadows(encoded);materials.mask('v003_shadow_mask.tga',shadow*.78)
    with Image.open(B/'v002_regolith.tga') as im:Image.fromarray(np.uint8(np.array(im)*.18)).save(B/'v003_shadow_tile.tga')
    materials.shader('v003_shadow_tile','v002_regolith_n',800)
    # No groom strip through empty air: gaps expose their complete crater bowls.
    route_mask=corridor.copy()
    for j in JUMPS:
        d=np.array(j['direction']);c=np.array(j['center']);u=(xx-c[0])*d[0]+(yy-c[1])*d[1]
        lat=(xx-c[0])*(-d[1])+(yy-c[1])*d[0]
        route_mask[(abs(u)<j['gap']/2-1)&(abs(lat)<42)]=0
    materials.mask('mask_v003_route.tga',route_mask*.9)
    materials.mask('mask_v003_micro.tga',.38+.62*smooth((np.maximum(abs(xx),abs(yy))-700)/80))
    bydist=cKDTree(np.vstack(bypasses)).query(np.c_[xx.ravel(),yy.ravel()],workers=4)[0].reshape(N,N)
    materials.mask('mask_v003_bypass.tga',smooth((8-bydist)/4)*.5)
    materials.mask('mask_racing.tga',np.maximum(corridor,smooth((8-bydist)/4)))
    materials.mask('mask_v003_pits.tga',pad);materials.mask('mask_v003_off.tga',smooth((np.maximum(abs(xx),abs(yy))-770)/20))
    start=np.exp(-((xx+540)/10)**8-((yy+440)/22)**8);materials.mask('mask_v003_start.tga',start)
    # HMF inputs must be power-of-two bitmaps, unlike the power-of-two-plus-one RAW.
    for image in B.glob('*.tga'):
        with Image.open(image) as im:
            if any(n&(n-1) for n in im.size):im.resize((2048,2048),Image.Resampling.BILINEAR).save(image)
    common=f'samples_x = {N}\nsamples_z = {N}\ndata = terrain.raw\nsize_x = 1600\nsize_z = 1600\nscale = {scale:g}\n'
    layers=[dict(map='v003_terrain_color.tga',repetitions=1),dict(map='v002_route.tga',mask='mask_v003_route.tga',repetitions=1,thickness=.02),
            dict(map='v002_fine.tga',mask='mask_v003_bypass.tga',repetitions=800,thickness=.01),
            dict(map='v002_regolith.tga',mask='mask_v003_micro.tga',repetitions=800),
            dict(map='v003_shadow_tile.tga',mask='v003_shadow_mask.tga',repetitions=800)]
    scene='scene0\n{\n name = scenery.edf\n pos\n {\n x = 800\n y = 0\n z = 800\n }\n rot\n {\n x = 0\n y = 0\n z = 0\n }\n}\n'
    (B/'track.hmf').write_text(common+'num_layers = 5\n'+''.join(block('layer'+str(i),v) for i,v in enumerate(layers))+scene)
    (B/'track.tht').write_text(common+'num_surface_layers = 3\n'+''.join(block('surface_layer'+str(i),dict(surface=surf,mask='mask_v003_'+key+'.tga')) for i,(surf,key) in enumerate([('off','off'),('pit','pits'),('start','start')]))+'num_material_layers = 2\n'+block('material_layer0',dict(material='compact soil'))+block('material_layer1',dict(material='soil',thickness=.02,mask='mask_racing.tga')))
    race.B=B;race.GAME=G;race.NAME=NAME
    race_data=race.build(xy,s,tangent,L,pit,pit_h-offset)
    rdf=G/(NAME+'.rdf');text=rdf.read_text().replace('long = 150.0\n','long = 60.0\n',1)
    text=text.replace('left = -14\n','left = -180\n').replace('right = 14\n','right = 180\n')
    rdf.write_text(text)
    for reset in G.glob('*.tl'):
        data=bytearray(reset.read_bytes());points=np.frombuffer(data,dtype='<f4',offset=8).reshape(-1,2)
        points[:,1]=np.sign(points[:,1])*180;reset.write_bytes(data)
    race_data['finish_station_m']=60.;race_data['reset_half_width_m']=180.
    save(B/'race_positions.json',race_data)
    ini=(G/(NAME+'.ini')).read_text().replace('Taurus-Littrow MX v002','Taurus-Littrow Crater Send v003').replace('Shorty Loop','Crater Send')
    (G/(NAME+'.ini')).write_text(ini)
    amb='sun_position\n{\n x = -8\n y = 4\n z = -6\n}\n'
    for weather in ['clear','cloudy','rainy']:
        amb+=weather+'\n{\n'+block(' ambient',dict(red=.19,green=.19,blue=.19))+block(' sun_color',dict(red=1,green=.99,blue=.97))+block(' sky_color',dict(red=0,green=0,blue=0))+block(' fog',dict(density=0,red=0,green=0,blue=0))+' sky = moon_v003_sky.edf\n sky_rot = 0\n}\n'
    (G/(NAME+'.amb')).write_text(amb)
    params='[params]\nlightdir_x=-8\nlightdir_y=4\nlightdir_z=-6\nshadowvolumes_create=0\nshadowmaps_create=0\nshadowmaps_scale=0.3\nshadowmaps_supersampling=1\nshadowmaps_terraincast=0\n'
    (B/'map_params.ini').write_text(params);(B/'edf_params.ini').write_text('[params]\ntype=0\nuse_normals=1\n');(B/'trh_params.ini').write_text('[params]\ntype=3\ntrackcode_filename=code.txt\n')
    (G/'gfx.cfg').write_text('dirt_color\n{\n red = .73\n green = .73\n blue = .73\n}\nparticles\n{\n soil\n {\n red = .65\n green = .65\n blue = .65\n }\n}\n')
    sky_spec=sky();flights=[]
    for j in JUMPS+[HERO]:
        c=np.array(j['center']);d=np.array(j['direction']);u=np.linspace(1,j['gap']+85,3000);p=c+d*(u-j['gap']/2)[:,None]
        trajectory=j['launch_height_absolute_m']+ballistic(u,j);ground=sample(encoded,p[:,0],p[:,1]);clearance=trajectory-ground
        candidates=np.flatnonzero((u>j['gap']-1)&(clearance<=.02));assert len(candidates),('No landing intercept',j['id'])
        hit=int(candidates[0]);touch=float(u[hit]);assert j['gap']-1<=touch<=j['gap']+75,(j['id'],touch)
        slope=(sample(encoded,*(c+d*(touch-j['gap']/2+.5)))-sample(encoded,*(c+d*(touch-j['gap']/2-.5))))
        impact=abs(math.degrees(math.atan(ballistic_slope(touch,j))-math.atan(float(slope))))
        assert impact<14,(j['id'],'nominal landing angle mismatch',impact)
        center_clearance=float(j['launch_height_absolute_m']+ballistic(j['gap']/2,j)-sample(encoded,*c))
        flights.append(dict(jump=j['id'],suggested_lip_speed_kmh=j['suggested_lip_speed_kmh'],nominal_contact_from_lip_m=round(touch,2),
                            landing_angle_difference_degrees=round(impact,2),crater_center_clearance_m=round(center_clearance,1),
                            model='point-mass ballistic calculation, no suspension, drag or rider input',in_game_verified=False))
    report=dict(version='moon-v003',name='Taurus-Littrow Crater Send',checks_pass=True,source_raw_sha256=sha(B/'terrain.raw'),
                terrain_size_m=SIZE,native_samples=N,native_scale_m=scale,terrain_height_offset_m=offset,
                route_length_m=round(L,1),half_gravity_m_s2=GRAVITY,features=JUMPS,optional_transfer=HERO,
                flight_validation=flights,measured_shorty_90m_retained=True,legacy_rollers_removed=True,
                sky=sky_spec,source_baked_terrain_shadow_mask=True,native_shadow_bake_disabled=True,
                imported_kboltz_asset_files=[],reference_only='KBOLTZ MOONED gameplay, archive structure and lighting approach',
                material=mat,race=race_data,in_game_test=False,
                limitations=['Giant craters and launch/landing earthworks are fictional additions to the mapped lunar setting.',
                             'Visible stars and oversized Earth are an artistic sky treatment.',
                             'Ballistic checks do not establish rideability; bike, rider input and lip speed must be tested.',
                             'Soil grip and dust use provisional MX Bikes materials; no vacuum or granular physics model.'])
    save(B/'source_validation.json',report);save(V/'source/v003_design.json',report)
    print('V003_SOURCE_PASS',json.dumps(dict(raw_sha256=report['source_raw_sha256'],scale=scale,features=len(JUMPS),flights=flights)),flush=True)

if __name__=='__main__':main()
