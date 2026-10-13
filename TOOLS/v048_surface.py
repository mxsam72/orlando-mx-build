"""One finish-tabletop visual benchmark on exact delivered v047/v046 inputs.

Virtual relief only: terrain.raw, native collision, scenery and accepted layers
stay exact. Existing atlases/masks are patched and two fully scoped visual layers
are appended; every changed atlas/mask pixel is scope checked.
"""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter
from scipy.spatial import cKDTree

R=Path(__file__).resolve().parents[1]
BASE=R/'V044_OUTPUT'; DIRT=R/'V046_OUTPUT'; O=R/'V048_OUTPUT'; M=O/'materials'
SPEC=R/'V048_SOURCE/visual_spec.json'; SIZE=600.
ATLAS=('v044_route_detail.tga','v044_route_detail_n.tga')
OLD_MASKS=('mask_v046_section.tga','mask_v046_packed.tga','mask_v046_wear.tga')
MASKS=(*OLD_MASKS,'mask_v048_clods.tga','mask_v048_relief.tga')

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def window(s,lo,hi,feather=1.5):return smooth((s-lo)/feather)*smooth((hi-s)/feather)
def tga(a,p):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(a).save(p,format='TGA')

class Sample:
    def __init__(self):
        self.spec=json.loads(SPEC.read_text());self.route=dict(np.load(BASE/'route.npz'))
        self.q=self.route['q'];self.p=self.q[:,:2];self.length=float(self.q[-1,3])
        self.tree=cKDTree(self.p)
        self.v=np.roll(self.p,-1,axis=0)-np.roll(self.p,1,axis=0)
        self.v/=np.maximum(np.linalg.norm(self.v,axis=1)[:,None],1e-10)
        self.height=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
        gy,self.gx=np.gradient(self.height,SIZE/2048);self.gz=-gy
        # Integrate the real accepted centerline height, smoothing grid quantisation.
        local=np.arange(-4,57,.1)
        centers=np.stack([np.interp(np.mod(local,self.length),self.q[:,3],self.q[:,k]) for k in [0,1]],1)
        ground=self.ground(centers[:,0],centers[:,1]);ground=gaussian_filter(ground,1.0)
        ds=np.sqrt(np.sum(np.diff(centers,axis=0)**2,axis=1)+np.diff(ground)**2)
        self.arc_station=local;self.arc_distance=np.r_[0,np.cumsum(ds)]
        self.arc_distance-=np.interp(0,local,self.arc_distance)
        self.roads=np.asarray(Image.open(BASE/'masks/v024_pit_roads.tga').getchannel('A'),np.float32)/255
        self.rng=np.random.default_rng(self.spec['seed'])
        self.noises=[self.rng.random((768,384),dtype=np.float32) for _ in range(5)]
        self.grooves=[]
        for center in np.arange(-7.,7.01,.37):
            self.grooves.append((center+self.rng.uniform(-.095,.095),self.rng.uniform(.064,.122),self.rng.uniform(.022,.047),self.rng.uniform(0,6.28)))
        self.tiles={k:np.asarray(Image.open(DIRT/'materials'/f'v045_{k}.tga').convert('RGB').resize((48,48),Image.Resampling.BOX),np.float32) for k in ['loose','packed']}

    def ground(self,x,z):return map_coordinates(self.height,[(SIZE-z)/SIZE*2048,x/SIZE*2048],order=1,mode='nearest')
    def slope(self,x,z):
        c=[(SIZE-z)/SIZE*2048,x/SIZE*2048]
        return map_coordinates(self.gx,c,order=1,mode='nearest'),map_coordinates(self.gz,c,order=1,mode='nearest')
    def coords(self,x,z):
        shape=x.shape;pos=np.stack([x.ravel(),z.ravel()],1);_,idx=self.tree.query(pos,workers=2)
        delta=pos-self.p[idx]
        s=self.q[idx,3]+np.sum(delta*self.v[idx],axis=1)
        s=np.mod(s+100,self.length)-100
        lat=delta[:,0]*(-self.v[idx,1])+delta[:,1]*self.v[idx,0]
        return s.reshape(shape),lat.reshape(shape)
    def scope(self,x,z):
        s,l=self.coords(x,z);sp=self.spec
        along=window(s,sp['station_start_m'],sp['station_end_m'],sp['end_feather_m'])
        side=smooth((sp['bank_outer_half_width_m']-np.abs(l))/sp['bank_feather_m'])
        road=map_coordinates(self.roads,[(SIZE-z)/SIZE*(self.roads.shape[0]-1),x/SIZE*(self.roads.shape[1]-1)],order=1,mode='nearest')
        return along*side*(1-smooth(road/.25))
    def noise(self,s,l,scale,i):
        return map_coordinates(self.noises[i],[(s+30)/scale,(l+30)/scale],order=1,mode='wrap')
    def fields(self,x,z):
        s,l=self.coords(x,z);a=np.interp(s,self.arc_station,self.arc_distance)
        face=window(s,0,13.5,1.7);landing=window(s,32.5,52,2.1)
        crest=window(s,10.8,15.3,1.3);deck=window(s,13.2,33.1,1.8)
        bank=smooth((np.abs(l)-4.65)/1.75)
        n0=self.noise(a,l,.23,0);n1=self.noise(a,l,.49,1)
        n2=self.noise(a,l,.97,2);n3=self.noise(a,l,2.3,3);n4=self.noise(a,l,5.8,4)
        # Sparse irregular clods, with a finer crumb field between them.
        clod=np.maximum(0,.58*n1+.42*n2-.44)**2*7.2
        crumb=(n0-.5)*.009+(n1-.5)*.013
        broken=(1-deck*.67)*(1-bank*.25)
        relief=(clod*.040+crumb)*broken
        groove=np.zeros_like(x,np.float32);ridge=np.zeros_like(x,np.float32)
        for center,width,depth,seed in self.grooves:
            wobble=.045*np.sin(a*.41+seed)+.026*np.sin(a*1.37+seed*3)
            c=center+wobble;w=width*(.72+.60*n2)
            g=np.exp(-((l-c)/w)**2)
            activity=.42+.58*self.noise(a+seed*3,l,1.8,3)
            strength=face*.95+landing*.56+deck*.14
            relief-=g*depth*activity*strength*(1-bank)
            r=np.exp(-((l-c-width*1.55)/(width*.8))**2)
            relief+=r*depth*.38*activity*strength*(1-bank)
            groove+=g*activity*strength*(1-bank);ridge+=r*activity*strength*(1-bank)
        wear=np.zeros_like(x,np.float32);impact=np.zeros_like(x,np.float32)
        # Wheel paths are independent of the cultivation furrows and widen on impact.
        for center,seed in [(-2.15,.2),(-.58,1.8),(1.22,3.1),(2.76,4.8)]:
            c=center+.16*np.sin(a*.12+seed)+.08*np.sin(a*.38+seed)
            width=.14+landing*.08
            w=np.exp(-((l-c)/width)**2)
            activity=.50+.50*smooth((self.noise(a+seed,l,2.1,4)-.27)/.45)
            depth=.012+landing*.030+face*.011
            relief-=w*depth*activity*(1-bank)
            wear=np.maximum(wear,w*activity*(1-bank))
            strike=window(s,36.8+seed*.4,47.0+seed*.45,2.2)
            churn=np.exp(-((l-c-.23)/.36)**2)*strike*(.2+.8*n1)
            relief+=churn*clod*.037
            impact=np.maximum(impact,churn)
        # Top/lip is compacted and scuffed; banks erode outward down the slopes.
        relief*=1-.36*crest*(1-bank)
        bank_phase=a+.38*np.sin(l*1.7)+.17*np.sin(l*3.1)
        bank_channels=np.exp(-(np.sin(bank_phase*np.pi/.67)/.20)**2)
        relief+=bank*((clod-.3)*.042+(n2-.5)*.025-bank_channels*.027)
        packed=np.clip(.16+face*.20+deck*.43+wear*.33+crest*.12-bank*.40,.04,.88)
        color=np.zeros((*x.shape,3),np.float32)
        for kind,weight in [('loose',1-packed),('packed',packed)]:
            tile=self.tiles[kind];c=[np.mod((SIZE-z)/2,1)*48,np.mod(x/2,1)*48]
            sample=np.stack([map_coordinates(tile[:,:,k],c,order=1,mode='grid-wrap') for k in range(3)],2)
            color+=sample*weight[:,:,None]
        # Broad moisture/soil variation and matched crevices. No baked light or shadow.
        color+=np.array([-6.,-10.,-12.],np.float32)
        color+=(n3-.5)[:,:,None]*13+(n4-.5)[:,:,None]*9
        color+=(clod-.32)[:,:,None]*13+(n0-.5)[:,:,None]*6
        color-=groove[:,:,None]*16+wear[:,:,None]*21+impact[:,:,None]*8
        color+=ridge[:,:,None]*3+(deck*3+crest*2)[:,:,None]
        color+=bank[:,:,None]*np.array([23.,16.,9.],np.float32)
        return dict(scope=self.scope(x,z),station=s,lateral=l,arc=a,relief=relief,color=color,packed=packed,
                    wear_alpha=.79+bank*.13+wear*.09,face=face,deck=deck,landing=landing,bank=bank)

def normal_map(sample,x,z,relief,dx):
    gy,gx=np.gradient(relief,dx);gz=-gy
    hx,hz=sample.slope(x,z)
    # Derivatives in the terrain's orthonormal tangent frame, rather than
    # treating a sloped face as a flat XY sheet. Green is the +world-Z tangent.
    tx=gx/np.sqrt(1+hx*hx)
    bz=(gz-gx*hx*hz/(1+hx*hx))/np.sqrt((1+hx*hx+hz*hz)/(1+hx*hx))
    den=np.sqrt(tx*tx+bz*bz+1)
    return np.uint8(np.rint(np.stack([-tx/den,-bz/den,1/den],2)*127.5+127.5))

def patch_masks(sample):
    n=4096;dx=SIZE/n;counts={}
    for name in MASKS:
        a=np.array(Image.open(DIRT/'materials'/name).convert('RGBA')) if name in OLD_MASKS else np.full((n,n,4),255,np.uint8)
        if name not in OLD_MASKS:a[:,:,3]=0
        count=0
        for y0 in range(int((SIZE-205)/dx),int((SIZE-165)/dx)+1,64):
            y1=min(n,y0+64);x0=int(285/dx);x1=int(363/dx)
            xx,zz=np.meshgrid((np.arange(x0,x1)+.5)*dx,SIZE-(np.arange(y0,y1)+.5)*dx)
            f=sample.fields(xx,zz);sc=f['scope']
            target={'mask_v046_section.tga':np.ones_like(sc),'mask_v046_packed.tga':f['packed'],'mask_v046_wear.tga':f['wear_alpha'],
                    'mask_v048_clods.tga':np.ones_like(sc),
                    'mask_v048_relief.tga':np.clip(.50+f['deck']*.22+f['bank']*.11,.5,.76)}[name]
            old=a[y0:y1,x0:x1,3].copy();new=np.uint8(np.rint(old*(1-sc)+target*255*sc))
            active=sc>0;a[y0:y1,x0:x1,3]=np.where(active,new,old);count+=np.count_nonzero(new!=old)
        tga(a,M/name);counts[name]=int(count)
    return counts

def clod_tile(sample):
    # A small repeating micro tile supplies millimetre texels; the atlas supplies
    # unique wheel paths and larger furrows. No static ground polygons are used.
    n=2048;dx=2/n;rng=np.random.default_rng(sample.spec['seed']+14)
    relief=np.zeros((n,n),np.float32);mottling=np.zeros_like(relief)
    for count,low,high in [(165,.020,.060),(1350,.004,.016)]:
        for _ in range(count):
            cx,cy=rng.uniform(0,n,2);radius=rng.uniform(low,high)/dx;ratio=rng.uniform(.55,1.2)
            ix=np.arange(int(cx-radius*1.7),int(cx+radius*1.7)+1);iy=np.arange(int(cy-radius*1.7),int(cy+radius*1.7)+1)
            xx,yy=np.meshgrid((ix-cx)/radius,(iy-cy)/radius)
            angle=rng.uniform(0,6.28);u=xx*np.cos(angle)+yy*np.sin(angle);v=(-xx*np.sin(angle)+yy*np.cos(angle))/ratio
            r2=u*u+v*v;shape=np.maximum(0,1-r2)**.72
            shape*=np.clip(1+.12*np.sin(u*7+angle)*np.sin(v*6-angle),.75,1.2)
            depth=rng.uniform(.004,.015) if count==165 else rng.uniform(.001,.004)
            relief[np.ix_(iy%n,ix%n)]+=shape*depth
            rim=np.exp(-((np.sqrt(r2)-1.02)/.18)**2)
            mottling[np.ix_(iy%n,ix%n)]+=shape*rng.uniform(4,13)-rim*3
    noise=rng.random((n,n),dtype=np.float32)
    relief+=(gaussian_filter(noise,2,mode='wrap')-.5)*.009
    # Use the accepted photographic soil as micro grain, rather than a uniform
    # procedural fill. Colour and normals share the authored clod geometry.
    photograph=np.asarray(Image.open(DIRT/'materials/v045_loose.tga').convert('RGB').resize((n,n),Image.Resampling.BOX),np.float32)
    rgb=np.clip(photograph+np.array([-8,-12,-14])+mottling[:,:,None]+(noise-.5)[:,:,None]*4,8,235)
    gy=(np.roll(relief,-1,0)-np.roll(relief,1,0))/(2*dx);gx=(np.roll(relief,-1,1)-np.roll(relief,1,1))/(2*dx)
    den=np.sqrt(gx*gx+gy*gy+1);normal=np.stack([-gx/den,gy/den,1/den],2)*127.5+127.5
    tga(np.uint8(np.rint(rgb)),M/'v048_clods.tga');tga(np.uint8(np.rint(normal)),M/'v048_clods_n.tga')
    (M/'v048_clods.shd').write_text('bump\n{\n map = v048_clods_n.tga\n repetitions = 0\n}\nspecular\n{\n shininess = 7\n}\n')
    return dict(size=[n,n],world_repeat_m=2.,texel_m=dx,coarse_clod_diameter_m=[.04,.12],fine_crumb_diameter_m=[.008,.032],tile_edges_use_periodic_relief=True)

def patch_atlas(sample):
    n=8192;dx=SIZE/n;counts={};x0=int(285/dx)-2;x1=int(363/dx)+2
    y0=int((SIZE-205)/dx)-2;y1=int((SIZE-165)/dx)+2
    for name in ATLAS:
        im=Image.open(DIRT/'materials'/name);a=np.array(im);count=0
        for start in range(y0,y1,64):
            end=min(start+64,y1);ys=np.arange(start-1,end+1);xs=np.arange(x0,x1)
            xx,zz=np.meshgrid((xs+.5)*dx,SIZE-(ys+.5)*dx);f=sample.fields(xx,zz)
            rgb=normal_map(sample,xx,zz,f['relief'],dx) if '_n.' in name else np.uint8(np.rint(np.clip(f['color'],8,235)))
            sc=f['scope'][1:-1,:,None];old=a[start:end,x0:x1,:3].copy()
            if '_n.' in name:
                vector=(old.astype(np.float32)/127.5-1)*(1-sc)+(rgb[1:-1].astype(np.float32)/127.5-1)*sc
                vector/=np.maximum(np.linalg.norm(vector,axis=2)[:,:,None],1e-7)
                new=np.uint8(np.rint(np.clip(vector*127.5+127.5,0,255)))
            else:new=np.uint8(np.rint(old*(1-sc)+rgb[1:-1]*sc))
            active=sc[:,:,0]>0;new=np.where(active[:,:,None],new,old)
            count+=np.count_nonzero(np.any(new!=old,axis=2));a[start:end,x0:x1,:3]=new
        tga(a,M/name);counts[name]=int(count)
    return counts

def verify_pixel_scope(sample,names):
    rows={}
    for name in names:
        new=Image.open(M/name);n=new.width;count=0
        if name in (*ATLAS,*OLD_MASKS):old=Image.open(DIRT/'materials'/name)
        else:old=Image.new('RGBA',new.size,(255,255,255,0))
        assert new.size==old.size and new.mode==old.mode,name
        for y0 in range(0,n,128):
            a=np.asarray(new.crop((0,y0,n,min(y0+128,n))));b=np.asarray(old.crop((0,y0,n,min(y0+128,n))))
            yy,xx=np.where(np.any(a!=b,axis=2));count+=len(xx)
            if len(xx):
                sc=sample.scope((xx+.5)*SIZE/n,SIZE-(yy+y0+.5)*SIZE/n)
                assert np.all(sc>0),(name,'changed pixels outside R01')
        assert count>0,name+' had no changes';rows[name]=dict(changed_pixels=count,pixels_changed_outside_sample=0)
        print('Verified local pixel scope:',name,count,flush=True)
    return rows

def main():
    sample=Sample();M.mkdir(parents=True,exist_ok=True)
    assert sha(BASE/'terrain.raw')==sample.spec['baseline_terrain_sha256']
    baseline={p.relative_to(DIRT).as_posix():sha(p) for p in DIRT.rglob('*') if p.is_file()}
    q=json.loads((DIRT/'v046_surface_validation.json').read_text());assert q['checks_pass']
    for name,row in q['new_files'].items():assert sha(DIRT/name)==row['sha256'],name
    # Retain every accepted layer and its depth. Append two fully scoped visual
    # layers: fine clods, then the unique macro relief. Both have 4 m cosmetic
    # depth, above the unchanged 0.31 m finite physical budget.
    text=(DIRT/'compiled_track.hmf').read_text();assert 'num_layers = 14' in text
    authored=text.replace('num_layers = 14','num_layers = 16',1)
    for i,name,rep,mask in [(14,'v048_clods.tga',300,'mask_v048_clods.tga'),(15,'v044_route_detail.tga',1,'mask_v048_relief.tga')]:
        authored+=f'\nlayer{i}\n{{\n map = {name}\n repetitions = {rep}\n mask = {mask}\n thickness = 4.0\n}}\n'
    (O/'compiled_track.hmf').write_text(authored)
    tile=clod_tile(sample);mask_counts=patch_masks(sample);atlas_counts=patch_atlas(sample)
    pixels=verify_pixel_scope(sample,[*MASKS,*ATLAS])
    assert all(sha(DIRT/name)==digest for name,digest in baseline.items()),'Baseline dirt changed'
    assert authored[:len(text)].replace('num_layers = 16','num_layers = 14',1)==text
    phases={}
    for label,(lo,hi) in [('face',(1,11.5)),('deck',(16,30)),('landing',(35,50)),('bank',(2,50))]:
        s,l=np.meshgrid(np.linspace(lo,hi,130),np.linspace(6.7,8.4,30) if label=='bank' else np.linspace(-4.8,4.8,90))
        x=np.interp(s,self_station:=sample.q[:,3],sample.q[:,0]);z=np.interp(s,self_station,sample.q[:,1])
        vx=np.interp(s,self_station,sample.v[:,0]);vz=np.interp(s,self_station,sample.v[:,1]);x-=l*vz;z+=l*vx
        f=sample.fields(x,z);phases[label]=dict(scope_min=float(f['scope'].min()),color_mean_rgb=f['color'].mean((0,1)).tolist(),virtual_relief_range_m=np.percentile(f['relief'],[5,50,95]).tolist(),packed_mean=float(f['packed'].mean()))
    assert phases['face']['scope_min']>.99 and phases['deck']['scope_min']>.99 and phases['landing']['scope_min']>.99
    result=dict(version='v048',checks_pass=True,feature='R01 finish tabletop only',spec=sample.spec,
        physical_terrain_modified=False,baseline_terrain_sha256=sha(BASE/'terrain.raw'),scenery_modified=False,
        all_accepted_hmf_layers_identical_to_v046=True,new_layers_added=2,existing_visual_depths_m={'11':4.,'12':4.,'13':4.},new_visual_depths_m={'14':4.,'15':4.},micro_tile=tile,
        photographic_micro_materials_and_shaders_retained_exact=True,changed_atlas_pixels=atlas_counts,changed_mask_pixels=mask_counts,
        pixel_scope_validation=pixels,pixels_changed_outside_sample=0,phase_statistics=phases,
        surface_distance_measured_from_accepted_heightfield=True,normal_gradients_in_surface_tangent_frame=True,
        baseline_dirt_source_unchanged=True,baseline_dirt_files=baseline,
        files={p.relative_to(O).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.rglob('*')) if p.is_file() and p.name!='v048_surface_validation.json'},
        in_game_visual_check=False,in_game_riding_test=False)
    save(O/'v048_surface_validation.json',result)
    print('R01 sample ready; original collision, trees, HMF and all pixels outside sample preserved.',flush=True)

if __name__=='__main__':main()
