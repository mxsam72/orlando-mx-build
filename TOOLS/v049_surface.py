"""Matte accepted-colour dirt, finish through triple, with no added layers.

Only the existing normal atlas and wear mask change. Every albedo, photographic
micro texture, shader, HMF, physical surface and scenery source stays exact.
"""
from pathlib import Path
import json,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,gaussian_filter
from v048_surface import Sample as Geometry,normal_map,sha,save,smooth,window,tga,SIZE,R,BASE,DIRT

O=R/'V049_OUTPUT';M=O/'materials';SPEC=R/'V049_SOURCE/visual_spec.json'
NORMAL='v044_route_detail_n.tga';WEAR='mask_v046_wear.tga'

class Sample(Geometry):
    def __init__(self):
        super().__init__();self.spec=json.loads(SPEC.read_text())
        self.dirt=np.asarray(Image.open(DIRT/'materials/mask_v046_section.tga').getchannel('A'),np.float32)/255
        local=np.arange(-4,192,.1)
        centers=np.stack([np.interp(np.mod(local,self.length),self.q[:,3],self.q[:,k]) for k in [0,1]],1)
        h=gaussian_filter(self.ground(centers[:,0],centers[:,1]),1)
        ds=np.sqrt(np.sum(np.diff(centers,axis=0)**2,axis=1)+np.diff(h)**2)
        self.arc_station=local;self.arc_distance=np.r_[0,np.cumsum(ds)]
        self.arc_distance-=np.interp(0,local,self.arc_distance)
        self.rng=np.random.default_rng(self.spec['seed'])
        self.noises=[self.rng.random((1024,384),dtype=np.float32) for _ in range(5)]
        self.grooves=[(c+self.rng.uniform(-.09,.09),self.rng.uniform(.067,.13),self.rng.uniform(.018,.040),self.rng.uniform(0,6.28)) for c in np.arange(-8.1,8.11,.37)]
        profiles=json.loads((BASE/'jump_profiles.json').read_text());self.profiles=[]
        for p in profiles:
            if p['id'] not in self.spec['features']:continue
            s=np.asarray(p['profile_s'])+p['lip_s'];h=np.asarray(p['profile_h'])
            self.profiles.append(dict(id=p['id'],s=s,h=h,g=np.gradient(h,s),lo=p['station_start_m'],hi=p['station_end_m'],lip=p['lip_s']))
        active=(self.q[:,3]<=192)|(self.q[:,3]>=self.length-5)
        p=self.p[active];margin=float(self.route['width'][active].max()/2+5)
        self.bounds=[float(p[:,0].min()-margin),float(p[:,1].min()-margin),float(p[:,0].max()+margin),float(p[:,1].max()+margin)]

    def scope(self,x,z):
        s,l=self.coords(x,z)
        along=window(s,self.spec['station_start_m'],self.spec['station_end_m'],self.spec['end_feather_m'])
        # Keep the accepted dirt/grass/road boundary exactly. No new dirt over
        # grass or pit roads, and no separate bank mask that scales package size.
        dirt=map_coordinates(self.dirt,[(SIZE-z)/SIZE*(self.dirt.shape[0]-1),x/SIZE*(self.dirt.shape[1]-1)],order=1,mode='nearest')
        return along*dirt

    def phases(self,s):
        face=np.zeros_like(s);landing=np.zeros_like(s);crest=np.zeros_like(s);deck=np.zeros_like(s);feature=np.zeros_like(s)
        for p in self.profiles:
            env=window(s,p['lo']-.7,p['hi']+1.5,1.5)
            g=np.interp(s,p['s'],p['g'],left=0,right=0);h=np.interp(s,p['s'],p['h'],left=0,right=0)
            face=np.maximum(face,env*smooth(g/.18));landing=np.maximum(landing,env*smooth(-g/.15))
            high=smooth((h-.8)/1.2);flat=1-smooth(np.abs(g)/.08)
            crest=np.maximum(crest,env*high*flat)
            if p['id']=='R01':deck=np.maximum(deck,window(s,14,32,1.5))
            feature=np.maximum(feature,env)
        return face,landing,crest,deck,feature

    def fields(self,x,z):
        s,l=self.coords(x,z);a=np.interp(s,self.arc_station,self.arc_distance)
        face,landing,crest,deck,feature=self.phases(s)
        half=np.interp(np.mod(s,self.length),self.q[:,3],self.route['width'])/2
        bank=smooth((np.abs(l)-half*.78)/np.maximum(half*.42,.9))
        n0=self.noise(a,l,.25,0);n1=self.noise(a,l,.51,1);n2=self.noise(a,l,1.06,2)
        clod=np.maximum(0,.58*n1+.42*n2-.43)**2*6.6
        relief=(clod-.25)*(.018+.010*face+.010*landing)*(1-deck*.62)
        relief+=(n0-.5)*.005+(n1-.5)*.009
        for c,w,d,seed in self.grooves:
            center=c+.046*np.sin(a*.39+seed)+.028*np.sin(a*.97+seed*3)
            width=w*(.82+.45*n2);g=np.exp(-((l-center)/width)**2)
            activity=.35+.65*self.noise(a+seed*2,l,1.8,3)
            strength=.16+.85*face+.48*landing-.08*deck
            relief-=g*d*activity*strength*(1-bank*.8)
            ridge=np.exp(-((l-center-w*1.65)/(w*.9))**2)
            relief+=ridge*d*.32*activity*strength*(1-bank*.8)
        # Match the existing accepted albedo's wheel lines. Avoid introducing
        # four unrelated dark lines or pebble-like repeating rings.
        tire=np.zeros_like(s);impact=np.zeros_like(s)
        for offset,width,depth,seed in [(-1.15,.19,.034,0),(1.65,.22,.029,1.2),(.2,.16,.023,2.3)]:
            center=offset+.48*np.sin(s*.026+seed)+.16*np.sin(s*.073+seed)
            activity=.38+.62*np.sin(s*.018+seed)**2
            track=np.exp(-((l-center)/(width+.055*landing))**2)*activity
            relief-=track*depth*(.82+.35*face+.50*landing)*(1-bank*.7)
            churn=np.exp(-((l-center-.24)/.38)**2)*landing*(.3+.7*n1)
            relief+=churn*clod*.018;impact=np.maximum(impact,churn);tire=np.maximum(tire,track)
        relief*=1-.38*crest*(1-bank)
        erosion=np.exp(-(np.sin((a+.26*np.sin(l*1.6))*np.pi/.79)/.25)**2)
        relief+=bank*feature*((clod-.25)*.022+(n2-.5)*.017-erosion*.017)
        wear_alpha=np.clip(.30+face*.12+landing*.09+deck*.12+bank*.15+tire*.29+impact*.08,.30,.80)
        return dict(scope=self.scope(x,z),station=s,lateral=l,relief=relief,wear_alpha=wear_alpha,
                    face=face,landing=landing,crest=crest,deck=deck,bank=bank,tire=tire)

def patch(sample):
    counts={};bounds=sample.bounds
    for name in [NORMAL,WEAR]:
        im=Image.open(DIRT/'materials'/name);a=np.array(im);n=im.width;dx=SIZE/n
        assert im.mode=='RGBA';count=0
        x0=max(1,int(bounds[0]/dx)-3);x1=min(n-1,int(bounds[2]/dx)+3)
        y0=max(1,int((SIZE-bounds[3])/dx)-3);y1=min(n-1,int((SIZE-bounds[1])/dx)+3)
        for row in range(y0,y1,64):
            end=min(row+64,y1);ys=np.arange(row-1,end+1);xs=np.arange(x0,x1)
            xx,zz=np.meshgrid((xs+.5)*dx,SIZE-(ys+.5)*dx);f=sample.fields(xx,zz);sc=f['scope'][1:-1]
            active=sc>0
            if name==NORMAL:
                rgb=normal_map(sample,xx,zz,f['relief'],dx)[1:-1]
                old=a[row:end,x0:x1,:3].copy()
                v=(old.astype(np.float32)/127.5-1)*(1-sc[:,:,None])+(rgb.astype(np.float32)/127.5-1)*sc[:,:,None]
                v/=np.maximum(np.linalg.norm(v,axis=2)[:,:,None],1e-7)
                new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)))
                new=np.where(active[:,:,None],new,old);a[row:end,x0:x1,:3]=new
                count+=np.count_nonzero(np.any(new!=old,axis=2))
                # Specular is normal-map ALPHA, not colour opacity or shininess.
                # Preserve the exact accepted level 2/255, including every edge.
                assert np.all(a[row:end,x0:x1,3]==sample.spec['normal_specular_alpha'])
            else:
                old=a[row:end,x0:x1,3].copy()
                target=f['wear_alpha'][1:-1]*255
                new=np.uint8(np.rint(old*(1-sc)+target*sc));new=np.where(active,new,old)
                a[row:end,x0:x1,3]=new;count+=np.count_nonzero(new!=old)
        tga(a,M/name);counts[name]=int(count)
    return counts

def verify_scope(sample):
    rows={}
    for name in [NORMAL,WEAR]:
        new=Image.open(M/name);old=Image.open(DIRT/'materials'/name);n=new.width;count=0;core=0
        for y0 in range(0,n,128):
            a=np.asarray(new.crop((0,y0,n,min(n,y0+128))));b=np.asarray(old.crop((0,y0,n,min(n,y0+128))))
            if name==NORMAL:assert np.array_equal(a[:,:,3],b[:,:,3]) and np.all(a[:,:,3]==2),'Specular channel changed'
            yy,xx=np.where(np.any(a!=b,axis=2));count+=len(xx)
            if len(xx):
                f=sample.fields((xx+.5)*SIZE/n,SIZE-(yy+y0+.5)*SIZE/n)
                assert np.all(f['scope']>0),(name,'edit escaped finish-through-triple scope')
                core+=np.count_nonzero(f['scope']>.99)
        assert count>0;rows[name]=dict(changed_pixels=int(count),pixels_changed_outside_section=0,core_changed_pixels=int(core))
        print('Verified exact edit scope',name,count,flush=True)
    return rows

def main():
    M.mkdir(parents=True,exist_ok=True);sample=Sample()
    assert sha(BASE/'terrain.raw')==sample.spec['baseline_terrain_sha256']
    baseline={p.relative_to(DIRT).as_posix():sha(p) for p in DIRT.rglob('*') if p.is_file()}
    q=json.loads((DIRT/'v046_surface_validation.json').read_text());assert q['checks_pass']
    for name,row in q['new_files'].items():assert sha(DIRT/name)==row['sha256'],name
    for name,digest in q['baseline_files'].items():assert sha(BASE/name)==digest,name
    shutil.copy2(DIRT/'compiled_track.hmf',O/'compiled_track.hmf')
    counts=patch(sample);pixels=verify_scope(sample)
    assert sha(O/'compiled_track.hmf')==sha(DIRT/'compiled_track.hmf')
    assert all(sha(DIRT/name)==digest for name,digest in baseline.items())
    coverage={}
    for p in sample.profiles:
        stations=np.arange(p['lo']+.8,p['hi']-.5,.25)
        x=np.interp(stations,sample.q[:,3],sample.q[:,0]);z=np.interp(stations,sample.q[:,3],sample.q[:,1])
        scope=sample.scope(x,z);assert np.all(scope>.99),(p['id'],'coverage gap')
        f=sample.fields(x,z)
        coverage[p['id']]=dict(centerline_coverage_min=float(scope.min()),ascending_face_samples=int(np.count_nonzero(f['face']>.5)),landing_samples=int(np.count_nonzero(f['landing']>.5)),crest_samples=int(np.count_nonzero(f['crest']>.5)))
    assert coverage['R02']['ascending_face_samples']>40 and coverage['R02']['landing_samples']>40
    save(O/'v049_surface_validation.json',dict(version='v049',checks_pass=True,spec=sample.spec,
        feature_coverage=coverage,all_accepted_albedo_textures_identical=True,macro_colour_atlas_identical=True,
        photographic_micro_colour_and_normal_tiles_identical=True,all_shaders_identical=True,hmf_identical_to_v046=True,
        layer_count=14,added_layers=0,added_textures=0,added_masks=0,added_texture_pixels=0,
        visual_layer_depths_m={'11':4.,'12':4.,'13':4.},accepted_specular_alpha=2,normal_specular_channel_identical=True,
        physical_terrain_modified=False,scenery_modified=False,lighting_modified=False,terrain_sha256=sha(BASE/'terrain.raw'),
        changed_pixels=counts,pixel_scope_validation=pixels,pixels_changed_outside_sample=0,
        v048_additional_layers_and_clod_tile_removed=True,baseline_dirt_source_unchanged=True,baseline_dirt_files=baseline,
        overridden_baseline_atlas_files=[NORMAL],work_bounds_world_xz_m=sample.bounds,
        files={p.relative_to(O).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.rglob('*')) if p.is_file() and p.name!='v049_surface_validation.json'},
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False))
    print('Matte accepted-colour section through all three triple crests ready; 14 layers, no new textures.',flush=True)

if __name__=='__main__':main()
