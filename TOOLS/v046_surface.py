"""Preserve v045 dirt, correct visual depth, extend to the whole riding circuit on v044.

All new layers are appended after the complete accepted stack. Every mask is
zero outside the selected route corridor. Collision and scenery are never edited.
"""
from pathlib import Path
import hashlib, json, re, shutil
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree

R=Path(__file__).resolve().parents[1]
BASE=R/'V044_OUTPUT'; O=R/'V046_OUTPUT'; M=O/'materials'
SPEC=R/'V046_SOURCE/visual_spec.json'; SIZE=600.

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    return h.hexdigest()

def save_json(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def smooth(a):
    a=np.clip(a,0,1);return a*a*(3-2*a)

def tga(im,p):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);im.save(p,format='TGA')

def mask_file(name,a):
    im=Image.new('RGBA',(a.shape[1],a.shape[0]),(255,255,255,0))
    im.putalpha(Image.fromarray(np.uint8(np.rint(np.clip(a,0,1)*255))))
    tga(im,M/name)

class Section:
    def __init__(self,spec):
        self.spec=spec;self.f=dict(np.load(BASE/'route.npz'));self.q=self.f['q'];self.p=self.q[:,:2]
        self.length=float(self.q[-1,3]);self.tree=cKDTree(self.p)
        self.v=np.roll(self.p,-1,axis=0)-np.roll(self.p,1,axis=0)
        self.v/=np.maximum(np.linalg.norm(self.v,axis=1)[:,None],1e-8)
        self.start=spec['station_start_m'];self.end=spec['station_end_m'];self.span=self.end-self.start
        self.grass=np.asarray(Image.open(BASE/'materials/mask_visual_grass.tga').getchannel('A'),np.float32)/255
        self.roads=np.asarray(Image.open(BASE/'masks/v024_pit_roads.tga').getchannel('A'),np.float32)/255

    def fields(self,x,z):
        shape=x.shape;pos=np.stack([x.ravel(),z.ravel()],1);_,idx=self.tree.query(pos,workers=2)
        delta=pos-self.p[idx];station=self.q[idx,3]+np.sum(delta*self.v[idx],axis=1)
        lateral=delta[:,0]*(-self.v[idx,1])+delta[:,1]*self.v[idx,0]
        station=station.reshape(shape);lat=lateral.reshape(shape)
        u=np.mod(station-self.start,self.length)
        along=np.ones(shape,np.float32) if self.spec['full_route'] else smooth(u/self.spec['end_feather_m'])*smooth((self.span-u)/self.spec['end_feather_m'])
        half=np.asarray(self.f['width'])[idx].reshape(shape)/2
        side=smooth((half+self.spec['shoulder_m']-np.abs(lat))/self.spec['side_feather_m'])
        coords=[(SIZE-z)/SIZE*(self.grass.shape[0]-1),x/SIZE*(self.grass.shape[1]-1)]
        g=map_coordinates(self.grass,coords,order=1,mode='nearest')
        coords=[(SIZE-z)/SIZE*(self.roads.shape[0]-1),x/SIZE*(self.roads.shape[1]-1)]
        road=map_coordinates(self.roads,coords,order=1,mode='nearest')
        scope=along*side*(1-smooth(g/.65))*(1-smooth(road/.25))
        curve=np.asarray(self.f['curvature'])[idx].reshape(shape)
        turn=np.clip(np.abs(curve)/.065,0,1)
        main=(-1.15+.5*np.sin(station*.026)+turn*.55)
        alternate=(1.65+.45*np.sin(station*.019+1.2)-turn*.4)
        traffic=np.maximum(np.exp(-((lat-main)/.72)**2),.75*np.exp(-((lat-alternate)/.9)**2))
        faces=np.zeros(shape,np.float32)
        for lo,hi in self.spec['packed_feature_ranges_m']:faces=np.maximum(faces,smooth((station-lo)/4)*smooth((hi-station)/4))
        packed=np.clip(.13+.61*traffic+.12*faces,.05,.82)
        drift=.09*np.sin(station*.16)+.035*np.sin(station*.71)
        phase=2*np.pi*(lat+drift)/.29
        shoulder=np.clip((np.abs(lat)-half*.63)/np.maximum(half*.37,.7),0,1)
        groom=(1-.85*traffic)*(.0065*np.sin(phase)+.0018*np.sin(2*phase+.7))
        height=groom.copy();tire=np.zeros(shape,np.float32);tread=np.zeros(shape,np.float32)
        for offset,width,depth,seed in [(-1.15,.19,.034,0),(1.65,.22,.029,1.2),(.2,.16,.023,2.3)]:
            center=offset+.48*np.sin(station*.026+seed)+.16*np.sin(station*.073+seed)
            activity=.38+.62*np.sin(station*.018+seed)**2
            track=np.exp(-((lat-center)/width)**2)*activity
            height-=track*depth
            # Alternating knob imprints: oriented with each actual riding path.
            knobs=(.5+.5*np.cos(station*2*np.pi/.31+seed))*np.exp(-((lat-center)/.25)**2)*activity
            height+=knobs*.0035;tread=np.maximum(tread,knobs);tire=np.maximum(tire,track)
        broken=np.sin(x*.57+np.sin(z*.41))*np.sin(z*.91+np.sin(x*.33))
        macro=3.7*np.sin(x*.22+np.sin(z*.31))+2.8*np.sin(z*.53+x*.38)+broken*2.0
        height+=shoulder*broken*.006
        darkness=tire*29+tread*6
        color=groom/.0083*10+macro-darkness+shoulder*2
        detail_alpha=np.clip(.18+.22*shoulder+.58*tire+.10*tread,.18,.90)
        return dict(scope=scope,packed=packed,station=station,lateral=lat,height=height,color=color,detail_alpha=detail_alpha,tire=tire)

def make_tiles(spec):
    accepted=R/'V045_OUTPUT'
    qa=json.loads((accepted/'v045_surface_validation.json').read_text())
    assert qa['checks_pass'] and qa['atlas_changed_pixels_outside_section']==0
    for family in ['loose','packed']:
        for suffix in ['.tga','_n.tga','.shd']:
            name=f'v045_{family}{suffix}'
            assert sha(accepted/'materials'/name)==qa['new_files']['materials/'+name]['sha256'],name
            shutil.copy2(accepted/'materials'/name,M/name)
    provenance=json.loads((accepted/'v045_asset_provenance.json').read_text())
    save_json(O/'v046_asset_provenance.json',provenance)
    print('Exact accepted v045 photographic dirt and normal maps retained.',flush=True)
    return qa['families']

def check_visual_depths(text,spec):
    depths={}
    for i in [11,12,13]:
        block=re.search(r'(?m)^layer'+str(i)+r'\s*\{([^{}]*)\}',text)
        assert block,('Missing new visual layer',i)
        value=re.search(r'(?m)^\s*thickness\s*=\s*([0-9.]+)\s*$',block.group(1))
        assert value,('Visual layer has no deformation depth',i)
        depth=float(value.group(1))
        assert depth==spec['visual_layer_thickness_m'] and depth>spec['physical_finite_layer_depth_budget_m'],('Insufficient visual deformation depth',i,depth)
        depths[str(i)]=depth
    return depths

def verify_atlas_scope(section):
    counts={}
    for name in ['v044_route_detail.tga','v044_route_detail_n.tga']:
        with Image.open(M/name) as new,Image.open(BASE/'materials'/name) as old:
            count=0
            for y0 in range(0,8192,128):
                box=(0,y0,8192,min(y0+128,8192));a=np.asarray(new.crop(box));b=np.asarray(old.crop(box))
                yy,xx=np.where(np.any(a!=b,axis=2));count+=len(xx)
                if len(xx):
                    f=section.fields((xx+.5)*SIZE/8192,SIZE-(y0+yy+.5)*SIZE/8192)
                    u=np.mod(f['station']-section.start,section.length)
                    assert (section.spec['full_route'] or np.all((u>0)&(u<section.span))) and np.all(f['scope']>0),(name,'Atlas edit escaped the dirt sample')
            counts[name]=count
    print('Full atlas comparison: every changed pixel is inside the riding dirt corridor.',flush=True)
    return counts

def main():
    spec=json.loads(SPEC.read_text());M.mkdir(parents=True,exist_ok=True)
    before={p.relative_to(BASE).as_posix():sha(p) for p in sorted(BASE.rglob('*')) if p.is_file() and (p.parent.name in ['materials','masks'] or p.name in ['terrain.raw','route.npz','compiled_track.hmf','v024_pit_gravel.tga','grass_n.tga','basemap.tga'])}
    assert sha(BASE/'terrain.raw')==spec['baseline_terrain_sha256']
    families=make_tiles(spec);section=Section(spec)
    # Masks have 14.6 cm world texels: enough to hold the sample edge and lane
    # wear while the 4K repeating photographic maps carry sub-mm soil detail.
    n=4096;x=(np.arange(n,dtype=np.float32)+.5)*SIZE/n
    masks={k:np.zeros((n,n),np.float32) for k in ['scope','packed','detail']}
    for y0 in range(0,n,64):
        z=SIZE-(np.arange(y0,min(y0+64,n),dtype=np.float32)+.5)*SIZE/n
        xx,zz=np.meshgrid(x,z);f=section.fields(xx,zz)
        masks['scope'][y0:y0+len(z)]=f['scope']
        masks['packed'][y0:y0+len(z)]=f['scope']*f['packed']
        masks['detail'][y0:y0+len(z)]=f['scope']*f['detail_alpha']
    for kind,name in [('scope','mask_v046_section.tga'),('packed','mask_v046_packed.tga'),('detail','mask_v046_wear.tga')]:mask_file(name,masks[kind])
    n=8192;dx=SIZE/n
    # Reuse the existing 8K atlas sources; edit only the riding dirt corridor.
    rgb=np.array(Image.open(BASE/'materials/v044_route_detail.tga').convert('RGB'))
    normals=np.array(Image.open(BASE/'materials/v044_route_detail_n.tga').convert('RGBA'))
    assert rgb.shape==(n,n,3) and normals.shape==(n,n,4)
    valid=np.argwhere(masks['scope']>0);ymin,xmin=valid.min(0);ymax,xmax=valid.max(0)
    xlo=max(0,int(xmin)*2-4);xhi=min(n,(int(xmax)+1)*2+4)
    ylo=max(0,int(ymin)*2-4);yhi=min(n,(int(ymax)+1)*2+4)
    # Read the authored photographs at the macro-map footprint to avoid aliasing.
    tiles={k:np.asarray(Image.open(M/f'v045_{k}.tga').resize((32,32),Image.Resampling.BOX),np.float32) for k in ['loose','packed']}
    for y0 in range(ylo,yhi,64):
        ys=np.arange(max(0,y0-1),min(n,y0+65,yhi+1),dtype=np.float32)
        xs=(np.arange(xlo,xhi,dtype=np.float32)+.5)*dx
        xx,zz=np.meshgrid(xs,SIZE-(ys+.5)*dx);f=section.fields(xx,zz)
        pixels={}
        for k,t in tiles.items():
            coords=[np.mod((SIZE-zz)/2,1)*32,np.mod(xx/2,1)*32]
            pixels[k]=np.stack([map_coordinates(t[:,:,c],coords,order=1,mode='grid-wrap') for c in range(3)],2)
        color=pixels['loose']*(1-f['packed'][:,:,None])+pixels['packed']*f['packed'][:,:,None]
        color+=f['color'][:,:,None]
        gy,gx=np.gradient(f['height'],dx);den=np.sqrt(gx*gx+gy*gy+1)
        normal=np.stack([-gx/den,gy/den,1/den],2)*127.5+127.5
        begin=y0-int(ys[0]);count=min(64,yhi-y0)
        active=f['scope'][begin:begin+count]>0
        new_rgb=np.uint8(np.rint(np.clip(color[begin:begin+count],8,235)))
        new_normal=np.uint8(np.rint(normal[begin:begin+count]))
        rgb[y0:y0+count,xlo:xhi]=np.where(active[:,:,None],new_rgb,rgb[y0:y0+count,xlo:xhi])
        normals[y0:y0+count,xlo:xhi,:3]=np.where(active[:,:,None],new_normal,normals[y0:y0+count,xlo:xhi,:3])
    tga(Image.fromarray(rgb),M/'v044_route_detail.tga');tga(Image.fromarray(normals),M/'v044_route_detail_n.tga')
    for obsolete in ['v045_wear.tga','v045_wear_n.tga','v045_wear.shd']:
        p=M/obsolete
        if p.exists():p.unlink()
    text=(BASE/'compiled_track.hmf').read_text();assert re.search(r'num_layers\s*=\s*11',text)
    authored=re.sub(r'num_layers\s*=\s*11','num_layers = 14',text)
    thickness=spec['visual_layer_thickness_m']
    for i,kind,mask,reps in [(11,'loose','section',300),(12,'packed','packed',300),(13,'wear','wear',1)]:
        mapname='v044_route_detail.tga' if kind=='wear' else f'v045_{kind}.tga'
        authored+=f'\nlayer{i}\n{{\n map = {mapname}\n repetitions = {reps}\n mask = mask_v046_{mask}.tga\n thickness = {thickness}\n}}\n'
    (O/'compiled_track.hmf').write_text(authored)
    visual_depths=check_visual_depths(authored,spec)
    station=section.q[:,3]
    core=np.ones(len(station),bool) if spec['full_route'] else ((station>=0)&(station<=291)) | ((station>=1305.377644440556)&(station<=section.length))
    cf=section.fields(section.q[:,0],section.q[:,1]);core_coverage=cf['scope'][core]
    assert np.all(core_coverage>.95),('Insufficient core dirt replacement',np.percentile(core_coverage,[0,10,50,90,100]).tolist())
    feature_coverage={}
    for feature,(lo,hi) in spec['feature_ranges_m'].items():
        feature_coverage[feature]=float(np.mean(cf['scope'][(station>=lo)&(station<=hi)]>.95))
        assert feature_coverage[feature]==1.0,('A track feature has incomplete dirt coverage',feature)
    indices=valid;xp=(indices[:,1]+.5)*SIZE/4096;zp=SIZE-(indices[:,0]+.5)*SIZE/4096
    vf=section.fields(xp,zp);u=np.mod(vf['station']-section.start,section.length)
    assert spec['full_route'] or np.all((u>0)&(u<section.span)),'Section mask escaped longitudinal scope'
    assert re.sub(r'num_layers\s*=\s*14','num_layers = 11',authored[:len(re.sub(r'num_layers\s*=\s*11','num_layers = 14',text))])==text
    assert all(sha(BASE/p)==h for p,h in before.items()),'A baseline file changed'
    Image.fromarray(rgb[ylo:yhi,xlo:xhi]).resize((1800, max(1,int(1800*(yhi-ylo)/(xhi-xlo))))).save(O/'v046_route_detail_preview.png')
    del rgb,normals
    changed_pixels=verify_atlas_scope(section)
    qa=dict(checks_pass=True,version='v046',baseline_version='v044',section='Whole riding circuit, including both roller sections and every jump/turn',
        station_start_m=spec['station_start_m'],station_end_m=spec['station_end_m'],baseline_files=before,
        baseline_terrain_sha256=sha(BASE/'terrain.raw'),baseline_source_unchanged=True,all_new_masks_zero_outside_section=True,
        core_centerline_fraction_with_at_least_95_percent_new_soil=float(np.mean(core_coverage>.95)),
        new_soil_max_alpha=1.,families=families,visual_layer_depths_m=visual_depths,
        zero_depth_visual_layers_added=False,visual_depth_exceeds_finite_physical_layer_budget=True,
        physical_finite_layer_depth_budget_m=spec['physical_finite_layer_depth_budget_m'],
        accepted_v045_materials_identical=True,accepted_material_release_id=spec['accepted_material_release_id'],
        feature_ranges_m=spec['feature_ranges_m'],feature_centerline_coverage=feature_coverage,full_route=spec['full_route'],macro_atlas_size=[8192,8192],macro_texel_m=dx,
        authored_sample_area_m2=float(np.count_nonzero(masks['scope'])* (SIZE/4096)**2),
        photographic_pixel_world_m=2/4096,old_layer_count=11,new_layer_count=14,all_new_layers_after_baseline=True,
        physical_terrain_modified=False,scenery_modified=False,lighting_modified=False,in_game_visual_check=False,
        overridden_baseline_atlas_files=['v044_route_detail.tga','v044_route_detail_n.tga'],existing_atlas_reused=True,atlas_edits_clipped_to_section=True,
        changed_atlas_pixels=changed_pixels,atlas_changed_pixels_outside_section=0,
        new_files={p.relative_to(O).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.rglob('*')) if p.is_file() and p.name!='v046_surface_validation.json'})
    save_json(O/'v046_surface_validation.json',qa)
    print('v046 depth-corrected dirt authored; core coverage',qa['core_centerline_fraction_with_at_least_95_percent_new_soil'],'area m2',qa['authored_sample_area_m2'],flush=True)

if __name__=='__main__':main()
