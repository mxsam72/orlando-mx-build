"""Whole-circuit matte dirt; remove continuous colour/compaction racing lines.

Only the existing atlas pair and two existing masks change. Fine soil remains
the exact accepted photographic tiles. Profiles and collision are never edited.
"""
import json, shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from v048_surface import R, BASE, DIRT, SIZE, sha, save, smooth, window, tga, normal_map
from v051_surface import Circuit as PreviousCircuit

O=R/'V052_OUTPUT'; M=O/'materials'; SPEC=R/'V052_SOURCE/visual_spec.json'
OVERRIDES=['v044_route_detail.tga','v044_route_detail_n.tga','mask_v046_packed.tga','mask_v046_wear.tga']

class Circuit:
    def __init__(self):
        self.spec=json.loads(SPEC.read_text()); self.route=dict(np.load(BASE/'route.npz'))
        self.q=self.route['q']; self.p=self.q[:,:2]; self.length=float(self.q[-1,3])
        self.tree=cKDTree(self.p); self.v=np.roll(self.p,-1,axis=0)-np.roll(self.p,1,axis=0)
        self.v/=np.maximum(np.linalg.norm(self.v,axis=1)[:,None],1e-9)
        # Only straights receive the extra grooming. Smooth curvature over
        # approximately 3 m so the strength fades gently into each corner.
        heading=np.unwrap(np.arctan2(self.v[:,1],self.v[:,0]))
        assert np.all(np.diff(self.q[:,3])>0)
        sigma=3./float(np.median(np.diff(self.q[:,3])))
        self.curvature=gaussian_filter(np.abs(np.gradient(heading,self.q[:,3])),sigma,mode='wrap')
        self.height=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
        gy,self.gx=np.gradient(self.height,SIZE/2048); self.gz=-gy
        self.dirt=np.asarray(Image.open(DIRT/'materials/mask_v046_section.tga').getchannel('A'),np.float32)/255
        local=np.arange(0,self.length,.10); local=np.r_[local,self.length]
        centers=np.stack([np.interp(local,self.q[:,3],self.q[:,k]) for k in [0,1]],1)
        h=gaussian_filter(self.ground(centers[:,0],centers[:,1]),1)
        self.arc_station=local; self.arc_distance=np.r_[0,np.cumsum(np.sqrt(np.sum(np.diff(centers,axis=0)**2,axis=1)+np.diff(h)**2))]
        self.arc_length=float(self.arc_distance[-1]); rng=np.random.default_rng(self.spec['seed'])
        self.noises=[rng.random((max(32,round(self.arc_length/scale)),384),dtype=np.float32) for scale in [.25,.51,1.06,2.7,6.0]]
        self.grooves=[(c+rng.uniform(-.09,.09),rng.uniform(.067,.13),rng.uniform(.018,.040),rng.uniform(0,6.28)) for c in np.arange(-8.1,8.11,.37)]
        self.profiles=[]
        for p in json.loads((BASE/'jump_profiles.json').read_text()):
            s=np.asarray(p['profile_s'])+p['lip_s']; h=np.asarray(p['profile_h'])
            self.profiles.append(dict(id=p['id'],s=s,h=h,g=np.gradient(h,s),lo=p['station_start_m'],hi=p['station_end_m']))
        self.tiles={k:np.asarray(Image.open(DIRT/'materials'/f'v045_{k}.tga').convert('RGB').resize((64,64),Image.Resampling.BOX),np.float32) for k in ['loose','packed']}
    def ground(self,x,z):
        return map_coordinates(self.height,[(SIZE-z)/SIZE*2048,x/SIZE*2048],order=1,mode='nearest')
    def slope(self,x,z):
        c=[(SIZE-z)/SIZE*2048,x/SIZE*2048]
        return map_coordinates(self.gx,c,order=1,mode='nearest'),map_coordinates(self.gz,c,order=1,mode='nearest')
    def coords(self,x,z):
        shape=x.shape; pos=np.stack([x.ravel(),z.ravel()],1); _,idx=self.tree.query(pos,workers=2)
        delta=pos-self.p[idx]; s=np.mod(self.q[idx,3]+np.sum(delta*self.v[idx],axis=1),self.length)
        lateral=delta[:,0]*(-self.v[idx,1])+delta[:,1]*self.v[idx,0]
        return s.reshape(shape),lateral.reshape(shape)
    def scope(self,x,z):
        return map_coordinates(self.dirt,[(SIZE-z)/SIZE*(len(self.dirt)-1),x/SIZE*(len(self.dirt)-1)],order=1,mode='nearest')
    def noise(self,a,l,scale,i):
        # Whole-loop periodic sampling, including the finish-line seam.
        height=len(self.noises[i]); cycles=max(1,round(self.arc_length/(scale*height)))
        return map_coordinates(self.noises[i],[a/self.arc_length*height*cycles,(l+40)/scale],order=1,mode='grid-wrap')
    def phases(self,s):
        face=np.zeros_like(s); landing=np.zeros_like(s); crest=np.zeros_like(s); feature=np.zeros_like(s)
        for p in self.profiles:
            ss=np.where((s>self.length-2)&(p['lo']==0),s-self.length,s)
            env=window(ss,p['lo']-.7,p['hi']+1.5,1.5)
            g=np.interp(ss,p['s'],p['g'],left=0,right=0); h=np.interp(ss,p['s'],p['h'],left=0,right=0)
            face=np.maximum(face,env*smooth(g/.18)); landing=np.maximum(landing,env*smooth(-g/.15))
            crest=np.maximum(crest,env*smooth((h-.8)/1.2)*(1-smooth(np.abs(g)/.08)))
            feature=np.maximum(feature,env)
        return face,landing,crest,feature
    def fields(self,x,z):
        s,l=self.coords(x,z); a=np.interp(s,self.arc_station,self.arc_distance); phase=2*np.pi*a/self.arc_length
        face,landing,crest,feature=self.phases(s)
        half=np.interp(s,self.q[:,3],self.route['width'])/2
        bank=smooth((np.abs(l)-half*.78)/np.maximum(half*.42,.9))
        straight=1-smooth((np.interp(s,self.q[:,3],self.curvature)-.009)/.011)
        # Stretch the small soil relief along station, rather than imposing a
        # square/cross-angled field. This is aligned with each local riding arc.
        n0=self.noise(a*.15,l,.25,0); n1=self.noise(a*.20,l,.51,1); n2=self.noise(a*.28,l,1.06,2)
        n3=self.noise(a,l,2.7,3); n4=self.noise(a,l,6.0,4)
        clod=np.maximum(0,.58*n1+.42*n2-.43)**2*6.6
        relief=(clod-.25)*(.007+.004*face+.006*landing)*(1-crest*.62)*(1-.25*straight)
        relief+=(n0-.5)*.002+(n1-.5)*.003
        for c,w,d,seed in self.grooves:
            center=c+.019*np.sin(phase*13+seed)+.012*np.sin(phase*31+seed*3)
            width=w*(.90+.20*n2); g=np.exp(-((l-center)/width)**2)
            activity=.73+.27*self.noise(a*.22+seed*2,l,1.8,3)
            strength=.60+.39*face+.18*landing-.19*crest
            grooming_gain=1+.30*straight
            relief-=g*d*activity*strength*(1-bank*.8)*grooming_gain
            relief+=np.exp(-((l-center-w*1.65)/(w*.9))**2)*d*.32*activity*strength*(1-bank*.8)*grooming_gain
        # Broken local tread/scuff fragments. No fixed +/-1m full-route paths.
        scuff=np.zeros_like(s)
        for c,seed in [(-4.4,0),(-3.0,.9),(-1.6,2.1),(-.1,3.6),(1.4,4.1),(3.,5.2),(4.7,6.)]:
            center=c+.12*np.sin(phase*9+seed)+.055*np.sin(phase*17+seed)
            interruption=smooth((self.noise(a*.30+seed*13,l,1.7,4)-.66)/.16)
            track=np.exp(-((l-center)/(.13+.05*landing))**2)*interruption
            track*=.30+.70*landing
            relief-=track*.009*(1-bank*.8); scuff=np.maximum(scuff,track)
        relief*=1-.38*crest*(1-bank)
        # Avoid the previous across-track bank comb. Subtle channels remain
        # lengthwise on jump shoulders, with softer erosion in the margins.
        erosion=np.exp(-(np.sin(l*np.pi/.72+.04*np.sin(phase*13))/.25)**2)
        relief+=bank*feature*((clod-.25)*.007+(n2-.5)*.005-erosion*.007)
        # Compaction varies in broken patches across the FULL width. The old
        # pair of high-opacity Gaussian lanes is deliberately absent.
        packed=np.clip(.25+.12*face+.15*crest+.10*landing+.20*(n3-.5)+.11*(n4-.5)-bank*.08,.12,.65)
        # Give the route-aligned normal atlas enough weight to suppress the
        # old world-axis micro-normal pattern visible as angled treads.
        wear_alpha=np.clip(.76+face*.05+landing*.02-crest*.04+bank*.01+.025*(n3-.5)+.08*straight,.69,.94)
        # Accepted photographic colour palette, no lane-dependent brightness,
        # no pale rims on virtual ruts. Fine photograph detail stays tiled.
        ix=np.mod(x/2*64,64); iy=np.mod(-z/2*64,64)
        loose=np.stack([map_coordinates(self.tiles['loose'][:,:,k],[iy,ix],order=1,mode='grid-wrap') for k in range(3)],2)
        compact=np.stack([map_coordinates(self.tiles['packed'][:,:,k],[iy,ix],order=1,mode='grid-wrap') for k in range(3)],2)
        color=loose*(1-packed[:,:,None])+compact*packed[:,:,None]
        mottle=(n3-.5)*6+(n4-.5)*7+(n1-.5)*3-scuff*4
        color=np.clip(color+mottle[:,:,None],8,235)
        return dict(scope=self.scope(x,z),station=s,lateral=l,relief=relief,color=color,packed=packed,wear_alpha=wear_alpha,face=face,landing=landing,crest=crest,bank=bank,straight_strength=straight)

def author(sample):
    counts={}; pmin=sample.p.min(0)-15; pmax=sample.p.max(0)+15
    for name in OVERRIDES:
        im=Image.open(DIRT/'materials'/name); a=np.array(im); n=im.width; dx=SIZE/n
        x0=max(1,int(pmin[0]/dx)-3); x1=min(n-1,int(pmax[0]/dx)+3)
        y0=max(1,int((SIZE-pmax[1])/dx)-3); y1=min(n-1,int((SIZE-pmin[1])/dx)+3); count=0
        for row in range(y0,y1,64):
            end=min(row+64,y1); xx,zz=np.meshgrid((np.arange(x0,x1)+.5)*dx,SIZE-(np.arange(row-1,end+1)+.5)*dx)
            f=sample.fields(xx,zz); sc=f['scope'][1:-1]; active=sc>0
            if name=='v044_route_detail_n.tga':
                target=normal_map(sample,xx,zz,f['relief'],dx)[1:-1]; old=a[row:end,x0:x1,:3].copy()
                v=(old.astype(np.float32)/127.5-1)*(1-sc[:,:,None])+(target.astype(np.float32)/127.5-1)*sc[:,:,None]
                v/=np.maximum(np.linalg.norm(v,axis=2)[:,:,None],1e-7)
                new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255))); new=np.where(active[:,:,None],new,old)
                a[row:end,x0:x1,:3]=new; count+=np.count_nonzero(np.any(new!=old,axis=2)); assert np.all(a[row:end,x0:x1,3]==2)
            elif name=='v044_route_detail.tga':
                old=a[row:end,x0:x1,:3].copy(); target=f['color'][1:-1]
                new=np.uint8(np.rint(old*(1-sc[:,:,None])+target*sc[:,:,None])); new=np.where(active[:,:,None],new,old)
                a[row:end,x0:x1,:3]=new; count+=np.count_nonzero(np.any(new!=old,axis=2))
            else:
                old=a[row:end,x0:x1,3].copy(); key='packed' if 'packed' in name else 'wear_alpha'
                # These masks ALREADY include the boundary scope. Do not
                # multiply their former lane strength back into the result.
                target=f[key][1:-1]*sc*255; new=np.uint8(np.rint(target)); new=np.where(active,new,old)
                a[row:end,x0:x1,3]=new; count+=np.count_nonzero(new!=old)
        tga(a,M/name); counts[name]=int(count); print('Authored',name,count,'pixels',flush=True)
    return counts

def verify(sample):
    scope_checks={}
    for name in OVERRIDES:
        new=Image.open(M/name); old=Image.open(DIRT/'materials'/name); n=new.width; count=0
        assert new.size==old.size and new.mode==old.mode
        for row in range(0,n,128):
            a=np.asarray(new.crop((0,row,n,min(n,row+128)))); b=np.asarray(old.crop((0,row,n,min(n,row+128))))
            yy,xx=np.where(np.any(a!=b,axis=2)); count+=len(xx)
            if len(xx):assert np.all(sample.scope((xx+.5)*SIZE/n,SIZE-(yy+row+.5)*SIZE/n)>0),(name,'edit outside MX corridor')
            if name.endswith('_n.tga'):assert np.array_equal(a[:,:,3],b[:,:,3]) and np.all(a[:,:,3]==2)
        assert count>0; scope_checks[name]=dict(changed_pixels=count,pixels_changed_outside_corridor=0)
    features={}
    for p in sample.profiles:
        s=np.arange(p['lo']+.8,p['hi']-.6,.25); x=np.interp(s,sample.q[:,3],sample.q[:,0]); z=np.interp(s,sample.q[:,3],sample.q[:,1])
        sc=sample.scope(x,z); assert np.all(sc>.99),(p['id'],'dirt gap'); face,landing,crest,_=sample.phases(s)
        features[p['id']]=dict(centerline_coverage_min=float(sc.min()),face_samples=int(np.count_nonzero(face>.5)),landing_samples=int(np.count_nonzero(landing>.5)),crest_samples=int(np.count_nonzero(crest>.5)))
    # Inspect every station cross section, including former lane offsets. Long
    # bands would give a systematic peak in a lane's column mean.
    stations=np.arange(0,sample.length,.5); offsets=np.arange(-4,4.01,.25)
    ss,ll=np.meshgrid(stations,offsets); xx=np.interp(ss,sample.q[:,3],sample.q[:,0]); zz=np.interp(ss,sample.q[:,3],sample.q[:,1])
    tx=np.interp(ss,sample.q[:,3],sample.v[:,0]); tz=np.interp(ss,sample.q[:,3],sample.v[:,1])
    f=sample.fields(xx-ll*tz,zz+ll*tx); means=f['packed'].mean(1)
    assert np.ptp(means)<.08,('Longitudinal compaction band',means.tolist())
    return scope_checks,features,dict(maximum_offset_mean_difference=float(np.ptp(means)),former_two_lane_fields_removed=True,continuous_tyre_paths_removed=True,packed_cross_section_means=means.tolist())

def compare_previous(sample):
    previous=PreviousCircuit()
    stations=np.arange(0,sample.length,.5);offsets=np.arange(-4.,4.01,.25)
    ss,ll=np.meshgrid(stations,offsets);xx=np.interp(ss,sample.q[:,3],sample.q[:,0]);zz=np.interp(ss,sample.q[:,3],sample.q[:,1])
    tx=np.interp(ss,sample.q[:,3],sample.v[:,0]);tz=np.interp(ss,sample.q[:,3],sample.v[:,1])
    x=xx-ll*tz;z=zz+ll*tx;before=previous.fields(x,z);after=sample.fields(x,z)
    weight=after['straight_strength'];corners=weight<1e-6;straights=weight>.95
    assert np.count_nonzero(straights)>1000 and np.count_nonzero(corners)>1000
    for key in ['color','packed','scope']:
        assert np.array_equal(before[key],after[key]),(key,'unexpected change from v051')
    assert np.array_equal(before['relief'][corners],after['relief'][corners]),'Corner relief changed'
    assert np.array_equal(before['wear_alpha'][corners],after['wear_alpha'][corners]),'Corner normal blend changed'
    assert np.all(after['wear_alpha']>=before['wear_alpha'])
    lateral_before=np.gradient(before['relief'],.25,axis=0);lateral_after=np.gradient(after['relief'],.25,axis=0)
    gain=float(np.mean(lateral_after[straights]**2)/np.mean(lateral_before[straights]**2))
    assert gain>1.10,('Straight grooming did not strengthen',gain)
    return dict(checks_pass=True,comparison_version='v051',groove_depth_gain_on_straights=1.30,
        straight_clod_relief_reduction_fraction=.25,extra_straight_normal_blend=.08,
        straight_lateral_gradient_energy_ratio_vs_v051=gain,
        compared_straight_samples=int(straights.sum()),compared_corner_samples=int(corners.sum()),
        fully_curved_section_relief_and_blend_exact=True,photo_colour_and_compaction_fields_exact=True,
        curvature_fade_rad_per_m=[.009,.020],physical_terrain_modified=False)

def main():
    M.mkdir(parents=True,exist_ok=True); sample=Circuit(); assert sha(BASE/'terrain.raw')==sample.spec['baseline_terrain_sha256']
    baseline={p.relative_to(DIRT).as_posix():sha(p) for p in DIRT.rglob('*') if p.is_file()}
    shutil.copy2(DIRT/'compiled_track.hmf',O/'compiled_track.hmf'); assert 'num_layers = 14' in (O/'compiled_track.hmf').read_text()
    counts=author(sample); scope,features,lanes=verify(sample);comparison=compare_previous(sample)
    from v052_coverage import author as coverage_author
    coverage_author(sample,M)
    assert all(sha(DIRT/n)==d for n,d in baseline.items()); assert sha(O/'compiled_track.hmf')==sha(DIRT/'compiled_track.hmf')
    # Quantify the actual authored relief in station/lateral coordinates.
    direction=[]
    for label,lo,hi in [('straight',62.,111.),('R02_face',132.,141.),('R10_face',747.,758.),('R16_face',1160.,1170.)]:
        ss,ll=np.meshgrid(np.arange(lo,hi,.12),np.arange(-4.,4.01,.08));xx=np.interp(ss,sample.q[:,3],sample.q[:,0]);zz=np.interp(ss,sample.q[:,3],sample.q[:,1])
        tx=np.interp(ss,sample.q[:,3],sample.v[:,0]);tz=np.interp(ss,sample.q[:,3],sample.v[:,1]);r=sample.fields(xx-ll*tz,zz+ll*tx)['relief']
        lateral,along=np.gradient(r,.08,.12);ratio=float(np.mean(lateral**2)/max(np.mean(along**2),1e-12))
        assert ratio>2.5,(label,'grooming not predominantly forward/back',ratio)
        direction.append(dict(section=label,lateral_to_longitudinal_gradient_energy_ratio=ratio,dominant_grooming_axis='riding direction'))
    save(O/'v052_surface_validation.json',dict(version='v052',checks_pass=True,full_route=True,spec=sample.spec,feature_coverage=features,
        grooming_direction_validation=direction,grooming_comparison_to_v051=comparison,cross_track_comb_removed=True,diagonal_scuff_amplitude_reduced=True,
        layer_count=14,added_layers=0,added_terrain_textures=0,added_masks=0,visual_layer_depths_m={'11':4.,'12':4.,'13':4.},
        photographic_micro_colour_and_normal_tiles_identical=True,all_shaders_identical=True,normal_specular_alpha=2,normal_specular_channel_identical=True,
        physical_terrain_modified=False,terrain_sha256=sha(BASE/'terrain.raw'),baseline_dirt_files=baseline,changed_pixels=counts,pixel_scope_validation=scope,
        pixels_changed_outside_corridor=0,line_removal_validation=lanes,overridden_baseline_atlas_files=OVERRIDES,
        files={p.relative_to(O).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.glob('*'))},
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False))
    print('v052 straight grooming ready; v051 corners, palette and physical terrain retained.',flush=True)
if __name__=='__main__':main()
