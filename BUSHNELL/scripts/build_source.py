"""Author Bushnell v001 from the preserved route and individually cited features."""
from pathlib import Path
import csv, hashlib, json, math, re
import numpy as np
from PIL import Image
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates
from scipy.spatial import cKDTree, ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as Polygon
from matplotlib.colors import LightSource
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def validate_route(points):
    p = np.asarray(points, float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 4:
        raise ValueError('Expected east/north closed route.')
    if not np.isfinite(p).all():
        raise ValueError('Non-finite route position.')
    if np.linalg.norm(p[0] - p[-1]) > .001:
        raise ValueError('Approved route is open; do not invent a closing line.')
    if np.any(np.linalg.norm(np.diff(p, axis=0), axis=1) < 1e-6):
        raise ValueError('Duplicate adjacent vertices.')
    return p


def load_project():
    c = json.loads((ROOT / 'project.json').read_text())
    if c['project_id'] != 'bushnell-mx' or c['project_root'] != 'BUSHNELL':
        raise ValueError('Wrong project identity.')
    path = ROOT / c['approved_layout']
    if digest(path) != c['approved_layout_sha256']:
        raise ValueError('Approved route checksum changed; version the change explicitly.')
    layout = json.loads(path.read_text())
    return c, layout, validate_route(layout['points'])


def world_origin(points, size):
    return (points.min(axis=0) + points.max(axis=0)) / 2 - size / 2


def local_to_game(points, origin):
    return np.asarray(points, float) - np.asarray(origin)


def game_to_pixel(points, size, n):
    p = np.asarray(points, float)
    return np.column_stack((p[:, 0] / size * (n - 1), (size - p[:, 1]) / size * (n - 1)))


def sample_route(p, spacing=.5):
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    s = np.linspace(0, arc[-1], math.ceil(arc[-1] / spacing) + 1)
    return s, np.column_stack([np.interp(s, arc, p[:, i]) for i in range(2)])


def smoothstep(value):
    u = np.clip(value, 0, 1)
    return u * u * (3 - 2 * u)


def profile(feature, stations):
    """C1 toe/landing, steepening takeoff and a short rounded lip into the top."""
    ramp, deck, land = [feature[k] for k in ['takeoff_length_m', 'deck_length_m', 'landing_length_m']]
    height, lip = feature['height_m'], feature['lip_slope']
    if feature['kind'] == 'roller':
        x = np.array([0, ramp, ramp + deck, ramp + deck + land])
        y = np.array([0, height, height * .94, 0]); slopes = [0, .06, -.08, 0]
    else:
        x = np.array([0, ramp * .45, ramp, ramp + .85, ramp + deck, ramp + deck + land])
        y = np.array([0, height * .23, height, height + lip * .18, height, 0])
        slopes = [0, height / ramp * .9, lip, 0, -.13, 0]
    q = np.asarray(stations) - feature['station_start_m']
    spline = CubicHermiteSpline(x, y, slopes, extrapolate=False)
    return np.where((q >= 0) & (q <= x[-1]), np.nan_to_num(spline(q)), 0)


def riding_line(route, design):
    s, exact = sample_route(route, .25)
    step = float(np.median(np.diff(s)))
    sm = gaussian_filter1d(exact[:-1], design['riding_line_smoothing_sigma_m'] / step, axis=0, mode='wrap')
    delta = sm - exact[:-1]; distance = np.linalg.norm(delta, axis=1)
    limit = design['maximum_smoothed_point_displacement_m']
    delta *= np.minimum(1, limit / np.maximum(distance, 1e-9))[:, None]
    xy = np.vstack([exact[:-1] + delta, exact[0] + delta[0]])
    tangent = np.roll(xy[:-1], -1, axis=0) - np.roll(xy[:-1], 1, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    tangent = np.vstack([tangent, tangent[0]])
    heading = np.unwrap(np.arctan2(tangent[:, 1], tangent[:, 0]))
    curvature = gaussian_filter1d(np.gradient(heading, s), 3 / step, mode='wrap')
    tree = cKDTree(xy[:-1]); separation = np.full(len(xy) - 1, 100.)
    sub = np.arange(0, len(xy) - 1, 4)
    for i in sub:
        indices = np.array(tree.query_ball_point(xy[i], 22))
        along = abs(s[indices] - s[i])
        indices = indices[np.minimum(along, s[-1] - along) > 24]
        if len(indices):
            separation[i] = np.linalg.norm(xy[indices] - xy[i], axis=1).min()
    separation = np.interp(s[:-1], s[sub], separation[sub])
    desired = np.interp(s[:-1], *np.array(design['width_knots']).T)
    width = np.minimum(desired, separation - .85)
    if width.min() < 4.3:
        raise ValueError(f'Approved lanes need explicit review: minimum estimated width {width.min():.2f} m')
    width = np.minimum(width, gaussian_filter1d(width, 2 / step, mode='wrap'))
    shoulder = np.minimum(2.2, np.maximum(.35, (separation - width) / 2 - .15))
    return s, xy, tangent, curvature, np.r_[width, width[0]], np.r_[shoulder, shoulder[0]], float(np.linalg.norm(delta, axis=1).max())


def berm_field(station, lateral, width, curvature, features, lap):
    bank = np.zeros_like(station, dtype=float)
    for f in features:
        a, b = f['station_start_m'], f['station_end_m']
        ss = station + (station < a) * lap if b > lap else station
        envelope = smoothstep((ss - a) / 5) * smoothstep((b - ss) / 5)
        middle = (ss > a + 4) & (ss < b - 4)
        turn = np.median(curvature[middle]) if np.any(middle) else .01
        sign = np.sign(turn) or 1
        if f['id'] == 'B09': sign = np.where(curvature >= 0, 1, -1)
        cross = np.clip((lateral * sign / width + .48) / .96, 0, 1) ** f['bank_power']
        bank += f['height_m'] * envelope * cross
    return bank


def make_textures(out):
    rng = np.random.default_rng(225232); n = 512
    grain = rng.normal(0, 1, (n, n))
    clods = gaussian_filter(rng.normal(0, 1, (n, n)), 3.8, mode='wrap'); clods /= clods.std()
    fine = gaussian_filter(grain, .65, mode='wrap'); xx, yy = np.meshgrid(np.arange(n), np.arange(n))
    for name, color, strength in [('soil', (169,145,108),7), ('prepared',(147,115,78),7), ('grass',(99,110,63),9)]:
        field = clods * 6 + fine * strength
        if name == 'prepared': field += np.sin(xx * .19 + np.sin(yy * .023) * .5) * 5
        rgb = np.uint8(np.clip(np.array(color) + field[..., None], 0, 255))
        Image.fromarray(rgb).save(out / (name + '.tga'))
        Image.fromarray(np.uint8(rgb.astype(float) * [.78,.79,.80])).save(out / (name + '_wet.tga'))
        dy, dx = np.gradient(field / 34); normals = np.stack([-dx,-dy,np.ones_like(dx)],-1)
        normals /= np.linalg.norm(normals,axis=-1)[...,None]
        Image.fromarray(np.uint8((normals + 1) * 127.5)).save(out / (name + '_n.tga'))
        (out / (name + '.shd')).write_text('bump\n{\n map = ' + name + '_n.tga\n}\n')


def rgba_mask(out, name, weight):
    mask = Image.fromarray(np.uint8(np.clip(weight,0,1)*255)).resize((2048,2048),Image.Resampling.BILINEAR)
    rgba = Image.new('RGBA',mask.size,'white'); rgba.putalpha(mask); rgba.save(out / (name+'.tga'))
    return mask


def scene_plan(xy, origin, width):
    rng = np.random.default_rng(901225); tree = cKDTree(xy[:-1]); placements = []
    for _ in range(9000):
        p = rng.uniform([-89,-80],[104,158]); d,i = tree.query(p)
        if d < width[i]/2 + 3.4: continue
        wooded = p[0] < -55 or p[1] > 130 or (p[0] > 82 and p[1] > 35)
        inner = (-8 < p[0] < 16 and 12 < p[1] < 100) or (-29 < p[0] < -17 and 52 < p[1] < 93)
        if not wooded and not inner: continue
        if any(np.linalg.norm(p-np.array(t['local_position'])) < 7.7 for t in placements): continue
        placements.append(dict(local_position=p.tolist(),height_m=float(rng.uniform(8,14)),crown_radius_m=float(rng.uniform(3.0,5.2)),seed=len(placements)+225))
        if len(placements) >= 155: break
    return dict(coordinate_basis='local east/north, converted with native_origin; landmark positions are estimates',trees=placements,
        viewing_stands=[{'local_position':[-47.5,44.5],'deck_height_m':3.2},{'local_position':[-33.5,-3.0],'deck_height_m':3.0}],
        water_tower={'local_position':[117,-26],'height_m':27},
        water_basins=[{'local_position':[-25,-11],'radius_m':[5.5,3.2]},{'local_position':[-29,24],'radius_m':[5.8,3.7]}],
        white_pickup={'local_position':[38,135],'angle_degrees':0},
        shipping_container={'local_position':[-63,65],'size_m':[6,2.5,2.6]},
        red_utility_building={'local_position':[54,147],'size_m':[19,8,4]},
        pit_area={'local_position':[56,-83],'size_m':[36,18]},
        evidence='Shaded inner lanes in clips 1–4; perimeter, pickup and fence in 6; two viewing stands and container in 7; tower, cones, trailers and paddock in 1/4/8.')


def preview(c,route,s,xy,height,origin,features,plan,out):
    size=c['terrain']['size_m']; pre=ROOT/'previews'; pre.mkdir(exist_ok=True)
    extent=[origin[0],origin[0]+size,origin[1],origin[1]+size]
    rgb=np.asarray(Image.open(out/'basemap.png')).astype(float)/255
    shade=LightSource(azdeg=235,altdeg=48).shade_rgb(rgb,height,vert_exag=1,dx=size/2048,dy=size/2048,blend_mode='soft')
    fig,ax=plt.subplots(figsize=(10,12),facecolor='#f6f4ed'); ax.imshow(shade,extent=extent,origin='upper'); ax.plot(*xy.T,color='white',lw=.45,alpha=.6)
    for f in features['jumps']:
        st=f['station_start_m']+f['takeoff_length_m']; p=[np.interp(st,s,xy[:,i]) for i in range(2)]
        ax.text(*p,f['id'],fontsize=8,weight='bold',ha='center',va='center',color='white',bbox=dict(boxstyle='round,pad=.22',fc='#6c4020',ec='white',lw=.5))
    for f in features['berms']:
        st=((f['station_start_m']+f['station_end_m'])/2)%s[-1];p=[np.interp(st,s,xy[:,i]) for i in range(2)]
        ax.annotate(f['id'],p,xytext=(9,7),textcoords='offset points',fontsize=7,color='#153a30',bbox=dict(fc='#ffffffcc',ec='none',pad=1))
    for tree in plan['trees']: ax.add_patch(plt.Circle(tree['local_position'],tree['crown_radius_m']*.7,color='#35543b',alpha=.6,lw=0))
    lo=route.min(0)-[15,13];hi=route.max(0)+[18,15]
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),aspect='equal',xlabel='East from reference (m)',ylabel='North from reference (m)')
    ax.set_title('BUSHNELL MX  /  FIRST RIDE PASS\n19 jump / rise profiles · 12 banked turns',loc='left',fontsize=17,weight='bold',color='#173c32',pad=15)
    ax.text(.97,.97,'N ↑',transform=ax.transAxes,ha='right',va='top',fontsize=14,color='#173c32',bbox=dict(fc='white',ec='none',pad=4))
    fig.text(.5,.025,'Approved route preserved. Dimensions and landmark placements are authoring estimates from the eight videos.',ha='center',fontsize=8,color='#43594d')
    fig.tight_layout(rect=(0,.045,1,.98));fig.savefig(pre/'BushnellMX_v001_01_terrain_plan.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(5,4,figsize=(15,12),facecolor='#f6f4ed')
    for ax,f in zip(axes.flat,features['jumps']):
        length=sum(f[k] for k in ['takeoff_length_m','deck_length_m','landing_length_m'])
        station=np.linspace(f['station_start_m']-2,f['station_start_m']+length+2,500);h=profile(f,station)
        ax.fill_between(station-f['station_start_m'],h,color='#af8357',alpha=.7);ax.plot(station-f['station_start_m'],h,color='#64401f',lw=1.5)
        ax.set_title(f['id']+'  '+f['name'],fontsize=8,loc='left');ax.set(ylim=(-.15,4.1),xlabel='Along profile (m)',ylabel='Rise (m)');ax.grid(alpha=.18);ax.tick_params(labelsize=7)
    axes.flat[-1].axis('off');fig.suptitle('Bushnell v001 / authored profiles — estimated dimensions',fontsize=17,color='#173c32');fig.tight_layout(rect=(0,0,1,.96));fig.savefig(pre/'BushnellMX_v001_02_jump_profiles.png',dpi=140);plt.close(fig)


def main():
    c,layout,route=load_project();features=json.loads((ROOT/'source/terrain_features.json').read_text());t=c['terrain'];size,n=t['size_m'],t['samples']
    origin=world_origin(route,size);out=ROOT/'build'/c['version'];out.mkdir(parents=True,exist_ok=True)
    s,xy,tangent,curvature,width,shoulder,displacement=riding_line(route,features['authoring']);game=local_to_game(xy,origin);tree=cKDTree(game[:-1]);axes=np.linspace(0,size,n)
    distance=np.empty((n,n),np.float32);index=np.empty((n,n),np.int32);lateral=np.empty((n,n),np.float32);station=np.empty((n,n),np.float32)
    for row in range(0,n,64):
        zz,xx=np.meshgrid(size-axes[row:row+64],axes,indexing='ij');query=np.c_[xx.ravel(),zz.ravel()];d,idx=tree.query(query,workers=2);delta=query-game[idx];shape=xx.shape;rows=slice(row,row+len(xx))
        distance[rows]=d.reshape(shape);index[rows]=idx.reshape(shape);lateral[rows]=np.sum(delta*np.c_[tangent[idx,1],-tangent[idx,0]],axis=1).reshape(shape)
        station[rows]=((s[idx]+np.sum(delta*tangent[idx],axis=1))%s[-1]).reshape(shape)
    w,sh=width[index],shoulder[index];weight=1-smoothstep((distance-w/2)/sh);racing=1-smoothstep((distance-w/2+.2)/.5)
    xx,zz=np.meshgrid(axes+origin[0],size-axes+origin[1]);height=3+.07*np.sin(xx/53)+.10*np.cos(zz/67);jumps=np.zeros_like(station)
    for feature in features['jumps']: jumps+=profile(feature,station).astype(np.float32)
    bank=berm_field(station,lateral,w,curvature[index],features['berms'],s[-1]);ruts=np.zeros_like(station);bend=np.clip(abs(curvature[index])*10,0,1)
    for offset in [-1.6,0,1.6]:
        center=offset+.15*np.sin(station*.12+offset);ruts-=(.025+.06*bend)*np.exp(-((lateral-center)/.20)**2)
    roughness=.012*np.sin(station*1.9)*np.sin(lateral*7.3);height+=(jumps+bank+ruts+roughness)*weight;plan=scene_plan(xy,origin,width)
    for pond in plan['water_basins']:
        px,pz=pond['local_position'];rx,rz=pond['radius_m'];basin=np.exp(-(((xx-px)/rx)**2+((zz-pz)/rz)**2)*1.5)*(1-racing);height-=.65*basin
    raw=np.rint(height/t['native_height_scale_m']*65535).astype('<u2');height=raw.astype(np.float32)/65535*t['native_height_scale_m']
    if raw.min()==0 or raw.max()==65535: raise ValueError('Terrain height was clipped.')
    raw.tofile(out/'terrain.raw');np.save(out/'height_metres.npy',height);Image.fromarray(raw).save(out/'heightmap_16bit.png')
    rng=np.random.default_rng(90225);patches=gaussian_filter(rng.normal(0,1,(n,n)),12);patches/=patches.std();hull=Polygon(route[ConvexHull(route[:-1]).vertices]);inside=hull.contains_points(np.c_[xx.ravel(),zz.ravel()]).reshape(n,n)
    access=np.array([[56,-83],[53,-72],[46,-62],[39,-56]],float);access_distance=np.full(xx.shape,100.)
    for a,b in zip(access[:-1],access[1:]):
        v=b-a;u=np.clip(((xx-a[0])*v[0]+(zz-a[1])*v[1])/(v@v),0,1);access_distance=np.minimum(access_distance,np.hypot(xx-a[0]-u*v[0],zz-a[1]-u*v[1]))
    apron=1-smoothstep((access_distance-2.4)/1.1)
    grass_weight=np.clip(.85+patches*.10-inside*.72,0,1)*(1-weight)*(1-apron);sand=np.array([194,181,145]);grass=np.array([104,119,68]);dirt=np.array([148,114,76]);base=sand+(grass-sand)*grass_weight[...,None];base=base*(1-racing[...,None])+dirt*racing[...,None]
    base+=patches[...,None]*2.8+rng.normal(0,1.5,(n,n,1));base+=np.clip(ruts[...,None]*280,-25,0)*racing[...,None]
    grooming=np.sin((lateral+.12*np.sin(station*.045))*math.tau/.44)*3.6
    base+=grooming[...,None]*racing[...,None]
    rgb=np.uint8(np.clip(base,0,255));im=Image.fromarray(rgb).resize((2048,2048),Image.Resampling.LANCZOS);im.save(out/'basemap.tga');Image.fromarray(rgb).save(out/'basemap.png')
    rgba_mask(out,'mask_racing',racing).save(out/'mask_racing.png');rgba_mask(out,'mask_detail',racing*.63);rgba_mask(out,'mask_shoulder',np.clip(weight-racing,0,1)*.7);rgba_mask(out,'mask_grass',grass_weight*.55)
    pit=np.array(plan['pit_area']['local_position']);pitmask=smoothstep((19-abs(xx-pit[0]))/2)*smoothstep((10-abs(zz-pit[1]))/2);rgba_mask(out,'mask_pits',pitmask);make_textures(out)
    common=f'samples_x = {n}\nsamples_z = {n}\ndata = terrain.raw\nsize_x = {size:g}\nsize_z = {size:g}\nscale = {t["native_height_scale_m"]:g}\n'
    scene='scene0\n{\n name = scenery.edf\n pos\n {\n  x = 0\n  y = 0\n  z = 0\n }\n rot\n {\n  x = 0\n  y = 0\n  z = 0\n }\n}\n'
    hmf=common+'num_layers = 4\nlayer0\n{\n map = basemap.tga\n repetitions = 1\n}\n'
    for i,(tile,mask,reps) in enumerate([('grass','mask_grass',96),('soil','mask_shoulder',128),('prepared','mask_detail',128)],1):
        hmf+=f'layer{i}\n{{\n map = {tile}.tga\n repetitions = {reps}\n mask = {mask}.tga\n thickness = 0.035\n frame1\n {{\n  map = {tile}_wet.tga\n }}\n}}\n'
    (out/'track.hmf').write_text(hmf+scene)
    tht=common+'num_surface_layers = 1\nsurface_layer0\n{\n surface = pit\n mask = mask_pits.tga\n}\nnum_material_layers = 3\nmaterial_layer0\n{\n material = compact soil\n}\nmaterial_layer1\n{\n material = grass\n thickness = 0.025\n mask = mask_grass.tga\n}\nmaterial_layer2\n{\n material = soft soil\n thickness = 0.045\n mask = mask_racing.tga\n}\n'
    (out/'track.tht').write_text(tht+scene);(out/'map_params.ini').write_text('[params]\nlightdir_x=-6\nlightdir_y=10\nlightdir_z=-5\nshadowmaps_create=0\nshadowvolumes_create=0\nshadowmaps_terraincast=0\n');(out/'trh_params.ini').write_text('[params]\ntype=3\ntrackcode_filename=code.txt\n');(out/'edf_params.ini').write_text('[params]\ntype=0\nuse_normals=1\n')
    for file in [out/'track.hmf',out/'track.tht']:
        for name in re.findall(r'^\s*(?:map|mask|data)\s*=\s*(.+)$',file.read_text(),re.M):
            if not (out/name.strip()).is_file(): raise ValueError(f'Missing native source reference: {name}')
    np.savez_compressed(out/'design.npz',station=s,xy=xy,tangent=tangent,curvature=curvature,width=width,shoulder=shoulder,origin=origin)
    with (out/'centerline.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['approved_station_m','local_east_m','local_north_m','game_x_m','game_z_m','estimated_width_m']);writer.writerows(np.round(np.c_[s,xy,game,width],5))
    save(out/'scenery_plan.json',plan);preview(c,route,s,xy,height,origin,features,plan,out)
    center_heights=map_coordinates(height,[(size-game[:,1])/size*(n-1),game[:,0]/size*(n-1)],order=1);grade=np.gradient(center_heights,np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))])
    report=dict(project_id=c['project_id'],version=c['version'],stage='first_ride_source',checks_pass=True,approved_layout_sha256=digest(ROOT/c['approved_layout']),loop_closure_m=float(np.linalg.norm(xy[0]-xy[-1])),approximate_route_length_m=round(float(s[-1]),2),length_basis='GPS and user sketch; not surveyed',terrain_size_m=size,native_samples=n,sample_spacing_m=size/(n-1),raw_bytes=raw.nbytes,source_raw_sha256=digest(out/'terrain.raw'),native_origin_local_east_north_m=origin.tolist(),image_top_is_north=True,width_range_m=[round(float(width.min()),2),round(float(width.max()),2)],authored_jump_profiles=len(features['jumps']),authored_berms=len(features['berms']),terrain_height_range_m=[float(height.min()),float(height.max())],maximum_centerline_grade_degrees=float(np.degrees(np.arctan(abs(grade).max()))),riding_line_smoothing_sigma_m=features['authoring']['riding_line_smoothing_sigma_m'],maximum_riding_line_displacement_m=displacement,estimated_trees=len(plan['trees']),gps_altitude_used=False,physics_profile='standard_game',native_compiled=False,installable=False)
    save(out/'validation.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__': main()
