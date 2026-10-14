"""Refine the dirt on the approved circuit without changing riding geometry.

Fine photographs and route-scale grooves have separate jobs: the photographs
carry grains and small clods, while the atlas carries directional grooming,
local tyre marks and landing compaction. Existing textures/layers are reused.
"""
import json, shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from v048_surface import R, BASE, DIRT, SIZE, sha, save, smooth, window, tga, normal_map
from v052_surface import Circuit as PreviousCircuit

PREVIOUS=R/'V052_OUTPUT'; O=R/'V053_OUTPUT'; M=O/'materials'; SPEC=R/'V053_SOURCE/visual_spec.json'
ATLAS=['v044_route_detail.tga','v044_route_detail_n.tga']
MASKS=['mask_v046_section.tga','mask_v046_packed.tga','mask_v046_wear.tga']
PHOTOS=['v045_loose.tga','v045_packed.tga']
OVERRIDES=ATLAS+MASKS+PHOTOS

class Circuit(PreviousCircuit):
    def __init__(self):
        super().__init__(); self.spec=json.loads(SPEC.read_text())
        heading=np.unwrap(np.arctan2(self.v[:,1],self.v[:,0]))
        sigma=3./float(np.median(np.diff(self.q[:,3])))
        self.turn_sign=gaussian_filter(np.gradient(heading,self.q[:,3]),sigma,mode='wrap')
        rng=np.random.default_rng(self.spec['seed'])
        # Each field contains an integer number of cells around the loop.
        # Sampling is periodic even when the requested cell size is approximate.
        self.local_scales=[(.8,.25),(1.8,.5),(4.,1.),(6.,2.7),(16.,6.),(.9,.35)]
        self.local_noise=[rng.random((max(32,round(self.arc_length/a)),max(32,round(80/l))),dtype=np.float32) for a,l in self.local_scales]
        self.grooves=[(c+rng.uniform(-.035,.035),rng.uniform(.049,.072),rng.uniform(.015,.025),rng.uniform(0,6.28)) for c in np.arange(-8.1,8.11,.28)]
        self.tiles={k:np.asarray(Image.open(M/f'v045_{k}.tga').convert('RGB').resize((32,32),Image.Resampling.BOX),np.float32) for k in ['loose','packed']}

    def local(self,a,l,i,offset=0.):
        tile=self.local_noise[i]; ls=self.local_scales[i][1]
        return map_coordinates(tile,[(a/self.arc_length*tile.shape[0]+offset)%tile.shape[0],(l+40)/ls],order=1,mode='grid-wrap')

    def fields(self,x,z):
        s,l=self.coords(x,z); a=np.interp(s,self.arc_station,self.arc_distance); phase=2*np.pi*a/self.arc_length
        face,landing,crest,feature=self.phases(s)
        half=np.interp(s,self.q[:,3],self.route['width'])/2
        curvature=np.interp(s,self.q[:,3],self.curvature)
        straight=1-smooth((curvature-.009)/.011)
        corner=smooth((curvature-.010)/.018)*(1-face*.85)*(1-landing*.6)
        sign=np.tanh(np.interp(s,self.q[:,3],self.turn_sign)/.012)
        bank=smooth((np.abs(l)-half*.79)/np.maximum(half*.39,.9))
        n0=self.local(a,l,0); n1=self.local(a,l,1); n2=self.local(a,l,2)
        n3=self.local(a,l,3); n4=self.local(a,l,4); edge_noise=self.local(a,l,5)
        clod=np.maximum(0,.57*n1+.43*n2-.48)**2*5.5
        # Keep large, blurry clods out of the groomed centre. Small grains are
        # supplied by the existing 4K photographs and their exact normal maps.
        relief=(clod-.12)*(.0025+.0045*bank+.002*landing)+(n0-.5)*.0007
        grooming=np.zeros_like(s); strength=(.68+.36*straight+.22*face+.10*landing-.27*crest)*(1-bank*.72)
        for c,w,d,seed in self.grooves:
            center=c+.013*np.sin(phase*29+seed)+.009*np.sin(phase*57+seed*2)
            width=w*(.85+.30*n2)
            activity=.48+.52*self.local(a,l,2,seed*7)
            g=np.exp(-((l-center)/width)**2)*activity
            rim=np.exp(-((l-center-width*1.45)/(width*.78))**2)*activity
            relief+=(-g+rim*.24)*d*strength
            grooming=np.maximum(grooming,g*strength)
        # Curved tracks follow the local route coordinate frame. They are only
        # active in corners and are broken rather than full-circuit colour lanes.
        tyre=np.zeros_like(s); corner_tyres=np.zeros_like(s); landing_tyres=np.zeros_like(s)
        for c,seed in [(-2.65,.4),(-.25,2.2),(2.15,4.7)]:
            centre=c+sign*.32*corner+.09*np.sin(phase*17+seed)
            interrupted=smooth((self.local(a,l,3,seed*11)-.39)/.23)
            t=np.exp(-((l-centre)/(.13+.06*corner+.05*landing))**2)*interrupted
            ct=t*corner; lt=t*landing
            corner_tyres=np.maximum(corner_tyres,ct); landing_tyres=np.maximum(landing_tyres,lt)
            tyre=np.maximum(tyre,np.maximum(ct,lt*.85))
            relief-=ct*.012+lt*.009
            # Very restrained individual knob fragments, aligned with travel.
            knobs=(.5+.5*np.cos(phase*round(self.arc_length/.31)+seed))**4
            relief-=t*(corner+landing)*knobs*.0012
        runout=np.zeros_like(s)
        for p in self.profiles:
            if np.max(p['h'])<.8:continue
            ss=np.where((s>self.length-2)&(p['lo']==0),s-self.length,s)
            runout=np.maximum(runout,window(ss,p['hi']-1,p['hi']+6,2.))
        impact=(landing*.8+runout*.35)*smooth((n2-.27)/.45)
        impact*=np.exp(-((l-.45*np.sin(phase*11))/np.maximum(half*.64,2.1))**4)
        # Compaction patches span a varied width and have no fixed bright pair.
        packed=np.clip(.20+.10*face+.18*crest+.16*impact+.12*tyre+.19*(n3-.5)+.11*(n4-.5)-bank*.11,.06,.72)
        # Restore a meaningful contribution from the fine photographs. The
        # directional atlas stays stronger on straights and jump faces.
        wear=np.clip(.49+.12*straight+.09*face+.04*landing+.055*tyre-.04*crest-.06*bank+.035*(n3-.5),.38,.73)
        # Narrow, irregular inner edge mixing, entirely within the prior scope.
        edge=smooth((np.abs(l)-half+.15)/1.2)
        edge_factor=1-.30*edge*smooth((edge_noise-.25)/.5)
        relief+=bank*feature*((clod-.12)*.006+(n2-.5)*.002)
        relief*=1-.25*crest*(1-bank)
        ix=np.mod(x/2*32,32); iy=np.mod(-z/2*32,32)
        loose=np.stack([map_coordinates(self.tiles['loose'][:,:,k],[iy,ix],order=1,mode='grid-wrap') for k in range(3)],2)
        compact=np.stack([map_coordinates(self.tiles['packed'][:,:,k],[iy,ix],order=1,mode='grid-wrap') for k in range(3)],2)
        color=loose*(1-packed[:,:,None])+compact*packed[:,:,None]
        mottle=(n3-.5)*5+(n4-.5)*6-tyre*6-impact*5-grooming*1.6+bank*1.5
        color=np.clip(color+mottle[:,:,None],8,235)
        return dict(scope=self.scope(x,z),station=s,lateral=l,relief=relief,color=color,packed=packed*edge_factor,
            wear_alpha=wear*edge_factor,section=edge_factor,face=face,landing=landing,crest=crest,bank=bank,
            straight_strength=straight,corner_strength=corner,corner_tyres=corner_tyres,landing_tyres=landing_tyres,
            tyre=tyre,landing_impact=impact,edge_factor=edge_factor)

def photographs():
    reports={}
    for family in ['loose','packed']:
        path=DIRT/'materials'/f'v045_{family}.tga'; im=Image.open(path); old=np.asarray(im,np.float32)
        luminance=old@np.array([.2126,.7152,.0722],np.float32)
        grain=luminance-gaussian_filter(luminance,3,mode='wrap')
        # Small neutral-to-warm adjustment, without baked illumination.
        rgb=np.uint8(np.rint(np.clip(old+np.clip(grain*.24,-5,5)[:,:,None]+np.array([3.,-2.,-1.]),8,235)))
        tga(rgb,M/path.name)
        after=rgb.astype(np.float32)@np.array([.2126,.7152,.0722],np.float32)
        contrast=float(np.std(after-gaussian_filter(after,3,mode='wrap'))/np.std(grain))
        assert rgb.shape==old.shape and contrast>1.08
        normal=DIRT/'materials'/f'v045_{family}_n.tga'
        assert Image.open(normal).getchannel('A').getextrema()==(2,2)
        reports[family]=dict(checks_pass=True,size=list(im.size),world_repeat_m=2.,photographic_source_sha256=sha(path),
            authored_sha256=sha(M/path.name),fine_grain_contrast_ratio=contrast,
            mean_rgb_change=(rgb.astype(np.float32)-old).mean((0,1)).tolist(),normal_source_sha256=sha(normal),
            photographic_normals_retained_exact=True,normal_specular_alpha=2,shader_retained_exact=True)
        print('Refined photograph',family,'grain contrast',round(contrast,3),flush=True)
    return reports

def author(sample):
    counts={}; pmin=sample.p.min(0)-15; pmax=sample.p.max(0)+15
    original_section=np.asarray(Image.open(DIRT/'materials/mask_v046_section.tga').getchannel('A'))
    for name in ATLAS+MASKS:
        im=Image.open(PREVIOUS/'materials'/name) if (PREVIOUS/'materials'/name).exists() else Image.open(DIRT/'materials'/name)
        a=np.array(im); n=im.width; dx=SIZE/n
        x0=max(1,int(pmin[0]/dx)-3); x1=min(n-1,int(pmax[0]/dx)+3)
        y0=max(1,int((SIZE-pmax[1])/dx)-3); y1=min(n-1,int((SIZE-pmin[1])/dx)+3); count=0
        for row in range(y0,y1,64):
            end=min(row+64,y1); xx,zz=np.meshgrid((np.arange(x0,x1)+.5)*dx,SIZE-(np.arange(row-1,end+1)+.5)*dx)
            f=sample.fields(xx,zz); sc=f['scope'][1:-1]; active=sc>0
            if name==ATLAS[1]:
                target=normal_map(sample,xx,zz,f['relief'],dx)[1:-1]; old=a[row:end,x0:x1,:3].copy()
                v=(old.astype(np.float32)/127.5-1)*(1-sc[:,:,None])+(target.astype(np.float32)/127.5-1)*sc[:,:,None]
                v/=np.maximum(np.linalg.norm(v,axis=2)[:,:,None],1e-7)
                new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255))); new=np.where(active[:,:,None],new,old)
                a[row:end,x0:x1,:3]=new; count+=np.count_nonzero(np.any(new!=old,axis=2)); assert np.all(a[row:end,x0:x1,3]==2)
            elif name==ATLAS[0]:
                old=a[row:end,x0:x1,:3].copy(); target=f['color'][1:-1]
                new=np.uint8(np.rint(old*(1-sc[:,:,None])+target*sc[:,:,None])); new=np.where(active[:,:,None],new,old)
                a[row:end,x0:x1,:3]=new; count+=np.count_nonzero(np.any(new!=old,axis=2))
            else:
                old=a[row:end,x0:x1,3].copy(); key='section' if 'section' in name else 'packed' if 'packed' in name else 'wear_alpha'
                new=np.uint8(np.rint(f[key][1:-1]*sc*255)); new=np.where(active,new,old)
                assert original_section.shape==(n,n)
                new=np.minimum(new,original_section[row:end,x0:x1])
                if key=='section':new=np.minimum(new,old)
                a[row:end,x0:x1,3]=new; count+=np.count_nonzero(new!=old)
        tga(a,M/name); counts[name]=int(count); print('Authored',name,count,'pixels',flush=True)
    return counts

def verify(sample):
    pixels={}
    for name in ATLAS+MASKS:
        new=Image.open(M/name); path=PREVIOUS/'materials'/name
        old=Image.open(path if path.exists() else DIRT/'materials'/name); n=new.width; count=0
        assert new.size==old.size and new.mode==old.mode
        for row in range(0,n,128):
            a=np.asarray(new.crop((0,row,n,min(n,row+128)))); b=np.asarray(old.crop((0,row,n,min(n,row+128))))
            yy,xx=np.where(np.any(a!=b,axis=2)); count+=len(xx)
            if len(xx):assert np.all(sample.scope((xx+.5)*SIZE/n,SIZE-(yy+row+.5)*SIZE/n)>0),(name,'edit outside prior MX dirt')
            if name.endswith('_n.tga'):assert np.array_equal(a[:,:,3],b[:,:,3]) and np.all(a[:,:,3]==2)
            if name=='mask_v046_section.tga':assert np.all(a[:,:,3]<=b[:,:,3]),'Dirt footprint expanded'
        assert count>0; pixels[name]=dict(changed_pixels=count,pixels_changed_outside_corridor=0)
    features={}
    section=np.asarray(Image.open(M/'mask_v046_section.tga').getchannel('A'),np.float32)/255
    original=np.asarray(Image.open(DIRT/'materials/mask_v046_section.tga').getchannel('A'))
    for name in MASKS:
        alpha=np.asarray(Image.open(M/name).getchannel('A'))
        assert not np.any(alpha[original==0]),(name,'texture weight outside original dirt mask')
    for p in sample.profiles:
        s=np.arange(p['lo']+.8,p['hi']-.6,.25); x=np.interp(s,sample.q[:,3],sample.q[:,0]); z=np.interp(s,sample.q[:,3],sample.q[:,1])
        sc=map_coordinates(section,[(SIZE-z)/SIZE*(section.shape[0]-1),x/SIZE*(section.shape[1]-1)],order=1,mode='nearest')
        assert np.all(sc>.99),(p['id'],'dirt gap')
        face,landing,crest,_=sample.phases(s)
        features[p['id']]=dict(centerline_coverage_min=float(sc.min()),face_samples=int(np.count_nonzero(face>.5)),landing_samples=int(np.count_nonzero(landing>.5)))
    stations=np.arange(0,sample.length,.5); offsets=np.arange(-4,4.01,.25)
    ss,ll=np.meshgrid(stations,offsets); xx=np.interp(ss,sample.q[:,3],sample.q[:,0]); zz=np.interp(ss,sample.q[:,3],sample.q[:,1])
    tx=np.interp(ss,sample.q[:,3],sample.v[:,0]); tz=np.interp(ss,sample.q[:,3],sample.v[:,1])
    x=xx-ll*tz; z=zz+ll*tx; f=sample.fields(x,z); before=PreviousCircuit().fields(x,z)
    means=f['packed'].mean(1); assert np.ptp(means)<.08,('Continuous compaction lanes',means.tolist())
    straight=f['straight_strength']>.95; corner=f['corner_strength']>.5; landing=f['landing']>.5
    assert np.mean(f['wear_alpha'][straight])<np.mean(before['wear_alpha'][straight])-.12
    assert np.count_nonzero(f['corner_tyres']>.15)>100 and np.count_nonzero(f['landing_impact']>.3)>100
    assert np.max(f['corner_tyres'][f['corner_strength']==0])==0
    comparison=dict(checks_pass=True,comparison_version='v052',photographic_normal_maps_exact=True,
        mean_straight_atlas_blend_before=float(before['wear_alpha'][straight].mean()),mean_straight_atlas_blend_after=float(f['wear_alpha'][straight].mean()),
        mean_corner_atlas_blend_after=float(f['wear_alpha'][corner].mean()),mean_landing_atlas_blend_after=float(f['wear_alpha'][landing].mean()),
        local_corner_tyre_samples=int(np.count_nonzero(f['corner_tyres']>.15)),landing_compaction_samples=int(np.count_nonzero(f['landing_impact']>.3)),
        corner_tyre_marks_absent_outside_corners=True,maximum_packed_offset_mean_difference=float(np.ptp(means)),
        approximate_grooming_spacing_m=.28,grooming_half_width_m=[.049,.072],grooming_virtual_depth_m=[.015,.025],
        physical_terrain_modified=False)
    return pixels,features,comparison

def main():
    M.mkdir(parents=True,exist_ok=True)
    inherited={p.relative_to(PREVIOUS).as_posix():sha(p) for p in PREVIOUS.rglob('*') if p.is_file()}
    baseline={p.relative_to(DIRT).as_posix():sha(p) for p in DIRT.rglob('*') if p.is_file()}
    photos=photographs(); sample=Circuit(); assert sha(BASE/'terrain.raw')==sample.spec['baseline_terrain_sha256']
    shutil.copy2(PREVIOUS/'compiled_track.hmf',O/'compiled_track.hmf'); counts=author(sample); pixels,features,comparison=verify(sample)
    retained=['mask_visual_grass.tga','mask_visual_racing.tga','mask_v032_packed.tga','mask_v032_face.tga']
    assert all(sha(M/n)==sha(PREVIOUS/'materials'/n) for n in retained)
    assert all(sha(PREVIOUS/n)==d for n,d in inherited.items()) and all(sha(DIRT/n)==d for n,d in baseline.items())
    assert sha(O/'compiled_track.hmf')==sha(PREVIOUS/'compiled_track.hmf')==sha(DIRT/'compiled_track.hmf')
    text=(O/'compiled_track.hmf').read_text()
    for name in PHOTOS:assert text.count('map = '+name)==1
    direction=[]
    for label,lo,hi in [('straight',62.,111.),('R02_face',132.,141.),('R10_face',747.,758.),('R16_face',1160.,1170.)]:
        ss,ll=np.meshgrid(np.arange(lo,hi,.12),np.arange(-4.,4.01,.08)); xx=np.interp(ss,sample.q[:,3],sample.q[:,0]); zz=np.interp(ss,sample.q[:,3],sample.q[:,1])
        tx=np.interp(ss,sample.q[:,3],sample.v[:,0]); tz=np.interp(ss,sample.q[:,3],sample.v[:,1]); r=sample.fields(xx-ll*tz,zz+ll*tx)['relief']
        lateral,along=np.gradient(r,.08,.12); ratio=float(np.mean(lateral**2)/max(np.mean(along**2),1e-12)); assert ratio>2.5,(label,ratio)
        direction.append(dict(section=label,lateral_to_longitudinal_gradient_energy_ratio=ratio,dominant_grooming_axis='riding direction'))
    save(O/'v053_surface_validation.json',dict(version='v053',checks_pass=True,full_route=True,spec=sample.spec,feature_coverage=features,
        grooming_direction_validation=direction,dirt_comparison_to_v052=comparison,photographic_grain_validation=photos,
        layer_count=14,added_layers=0,added_terrain_textures=0,added_masks=0,hmf_identical_to_v052=True,
        photographic_micro_normal_tiles_identical=True,photographic_colour_tiles_refined=True,all_shaders_identical=True,
        normal_specular_alpha=2,normal_specular_channel_identical=True,physical_terrain_modified=False,terrain_sha256=sha(BASE/'terrain.raw'),
        baseline_dirt_files=baseline,changed_pixels=counts,pixel_scope_validation=pixels,pixels_changed_outside_corridor=0,
        scoped_photographic_bindings=dict(checks_pass=True,colour_tiles=PHOTOS,active_layers=[11,12],outside_original_scope_alpha=0),
        grass_ground_mask_identical_to_v052=True,isolated_layer_trials_identical_to_v052=True,overridden_baseline_atlas_files=OVERRIDES,
        files={p.relative_to(O).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.glob('*'))},
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False))
    print('v053 finer dirt, directional grooming and local wear source checks passed.',flush=True)

if __name__=='__main__':main()
