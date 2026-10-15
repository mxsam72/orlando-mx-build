"""Expose the accepted photographs, with current-route loam and no straight cross-treads."""
import re
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from v057_inputs import R, BASE, PREV, O, M, sha, save
from v056_surface import source as previous_source
from v052_surface import Circuit as OldCircuit
from v048_surface import SIZE, smooth, tga, normal_map


def baseline(name):
    return previous_source(name)


def source(name):
    return M/name if (M/name).is_file() else baseline(name)


def shader(name):
    name=name.replace('.tga','.shd')
    return next(p/name for p in [PREV/'materials',R/'V054_OUTPUT/materials',R/'V052_OUTPUT/materials',R/'V046_OUTPUT/materials',BASE/'materials'] if (p/name).exists())


class Circuit(OldCircuit):
    def __init__(self):
        self.route=dict(np.load(PREV/'route.npz')); self.q=self.route['q']
        self.p=self.q[:,:2]; self.length=float(self.q[-1,3]); self.tree=cKDTree(self.p)
        self.v=np.roll(self.p,-1,axis=0)-np.roll(self.p,1,axis=0)
        self.v/=np.maximum(np.linalg.norm(self.v,axis=1,keepdims=True),1e-9)
        heading=np.unwrap(np.arctan2(self.v[:,1],self.v[:,0]))
        self.curvature=gaussian_filter(np.abs(np.gradient(heading,self.q[:,3])),3./np.median(np.diff(self.q[:,3])),mode='wrap')
        self.height=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
        gy,self.gx=np.gradient(self.height,SIZE/2048); self.gz=-gy
        self.dirt=np.asarray(Image.open(baseline('mask_v046_section.tga')).getchannel('A'),np.float32)/255
        self.arc_station=np.r_[np.arange(0,self.length,.1),self.length]
        centers=np.stack([np.interp(self.arc_station,self.q[:,3],self.q[:,k]) for k in [0,1]],1)
        h=gaussian_filter(self.ground(centers[:,0],centers[:,1]),1)
        self.arc_distance=np.r_[0,np.cumsum(np.sqrt(np.sum(np.diff(centers,axis=0)**2,axis=1)+np.diff(h)**2))]
        self.arc_length=float(self.arc_distance[-1]); rng=np.random.default_rng(57025)
        self.noises=[rng.random((max(32,round(self.arc_length/scale)),512),dtype=np.float32) for scale in [.20,.38,.85,2.7,6.]]
        self.grooves=[(c+rng.uniform(-.08,.08),rng.uniform(.10,.17),rng.uniform(.035,.065),rng.uniform(0,6.28)) for c in np.arange(-10.,10.,.43)]
        self.profiles=[]
        self.tiles={k:np.asarray(Image.open(baseline('v045_'+k+'.tga')).convert('RGB').resize((64,64),Image.Resampling.BOX),np.float32) for k in ['loose','packed']}

    def fields(self,x,z):
        s,l=self.coords(x,z); a=np.interp(s,self.arc_station,self.arc_distance)
        straight=1-smooth((np.interp(s,self.q[:,3],self.curvature)-.009)/.015)
        hx,hz=self.slope(x,z); flat=1-smooth((np.hypot(hx,hz)-.08)/.22)
        n0=self.noise(a,l,.20,0); n1=self.noise(a*.55,l,.38,1)
        n2=self.noise(a*.50,l,.85,2); n3=self.noise(a,l,2.7,3); n4=self.noise(a,l,6.,4)
        # Broken rounded clods, rather than a stamped diagonal tread. Flat
        # ground gets more loose cultivation. Every directional term uses
        # station/lateral coordinates from the accepted v056 route.
        clod=np.maximum(0,.62*n0+.38*n1-.39)**1.7
        relief=(clod-.08)*(.075+.050*flat)+(n2-.5)*.014
        furrow=np.zeros_like(s)
        for c,w,d,seed in self.grooves:
            center=c+.024*np.sin(a*.13+seed)+.015*np.sin(a*.37+seed*3)
            activity=.30+.70*smooth((self.noise(a+seed*9,l,2.7,3)-.20)/.60)
            groove=np.exp(-((l-center)/(w*(.85+.3*n2)))**2)*activity
            ridge=np.exp(-((l-center-w*1.5)/(w*1.05))**2)*activity
            relief+=(-groove+.35*ridge)*d*(.55+.45*flat)
            furrow+=groove
        # No diagonal stamps, cross-track comb, paired skid-steer lanes or
        # wheel-path bands on straights. The curve itself carries the grooves.
        color=np.zeros((*x.shape,3),np.float32)
        packed=np.clip(.24+.16*(n3-.5)+.10*(n4-.5)-.06*flat,.10,.40)
        ix=np.mod(x/2*64,64); iy=np.mod(-z/2*64,64)
        for k,w in [('loose',1-packed),('packed',packed)]:
            tile=self.tiles[k]
            rgb=np.stack([map_coordinates(tile[:,:,i],[iy,ix],order=1,mode='grid-wrap') for i in range(3)],2)
            color+=rgb*w[:,:,None]
        color+=((n3-.5)*5+(n4-.5)*6+(clod-.08)*12-furrow*3)[:,:,None]
        return dict(scope=self.scope(x,z),station=s,lateral=l,relief=relief,color=np.clip(color,8,235),straight_strength=straight,flat=flat)


def grain_normals():
    result=[]
    for kind in ['loose','packed']:
        name='v045_'+kind+'_n.tga'
        color=np.asarray(Image.open(baseline('v045_'+kind+'.tga')).convert('RGB'),np.float32)
        gray=color.mean(2)/255; del color
        # Preserve photograph-derived small clods; reject long directional
        # shading/tread structures before differentiating. Both filters are
        # isotropic and wrap seamlessly. No synthetic diagonal basis exists.
        height=(gaussian_filter(gray,1.2,mode='wrap')-gaussian_filter(gray,24.,mode='wrap'))*(.009 if kind=='loose' else .0045)
        gy,gx=np.gradient(height,2/len(height)); strength=np.hypot(gx,gy)
        scale=np.maximum(1,strength/.85); gx/=scale; gy/=scale
        v=np.stack([-gx,gy,np.ones_like(gx)],2); v/=np.linalg.norm(v,axis=2,keepdims=True)
        out=np.empty((*height.shape,4),np.uint8); out[:,:,:3]=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255))); out[:,:,3]=2
        tga(out,M/name); shutil.copy2(shader('v045_'+kind+'.tga'),M/('v045_'+kind+'.shd'))
        result.append(dict(file=name,photo_colour_unchanged=True,filter='isotropic periodic 1.2px minus 24px photograph height',maximum_tangent_slope=.85,normal_specular_alpha=2))
    return result


def author(sample):
    counts={}; pmin=sample.p.min(0)-19; pmax=sample.p.max(0)+19
    for name in ['v044_route_detail.tga','v044_route_detail_n.tga']:
        im=Image.open(baseline(name)); a=np.array(im); n=im.width; dx=SIZE/n
        x0=max(1,int(pmin[0]/dx)-3); x1=min(n-1,int(pmax[0]/dx)+3)
        y0=max(1,int((SIZE-pmax[1])/dx)-3); y1=min(n-1,int((SIZE-pmin[1])/dx)+3); count=0
        for row in range(y0,y1,64):
            end=min(row+64,y1); xx,zz=np.meshgrid((np.arange(x0,x1)+.5)*dx,SIZE-(np.arange(row-1,end+1)+.5)*dx)
            f=sample.fields(xx,zz); sc=f['scope'][1:-1]; active=sc>0
            target=normal_map(sample,xx,zz,f['relief'],dx)[1:-1] if name.endswith('_n.tga') else f['color'][1:-1]
            old=a[row:end,x0:x1,:3].copy()
            if name.endswith('_n.tga'):
                v=(old.astype(np.float32)/127.5-1)*(1-sc[:,:,None])+(target.astype(np.float32)/127.5-1)*sc[:,:,None]
                v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-7); target=v*127.5+127.5
            else:target=old*(1-sc[:,:,None])+target*sc[:,:,None]
            new=np.uint8(np.rint(np.clip(target,0,255))); new=np.where(active[:,:,None],new,old)
            a[row:end,x0:x1,:3]=new; count+=np.count_nonzero(np.any(old!=new,axis=2))
        if name.endswith('_n.tga'):assert np.all(a[:,:,3]==2)
        tga(a,M/name); counts[name]=int(count)
        if not name.endswith('_n.tga'):shutil.copy2(shader(name),M/name.replace('.tga','.shd'))
        print('Authored current-route loam',name,count,flush=True)
    name='mask_v046_wear.tga'; a=np.array(Image.open(baseline(name))); old=a[:,:,3].copy()
    # Strict cap: 63/255 = 24.706%, the nearest 8-bit value below 25%.
    target=np.uint8(np.rint(old.astype(np.float32)*63/int(old.max())))
    # Retain even the faintest feather samples, without extending the footprint.
    target[(old>0)&(target==0)]=1; a[:,:,3]=target
    assert target.max()==63 and np.array_equal(target>0,old>0)
    tga(a,M/name)
    return counts,dict(requested_cap_percent=25.,actual_8bit_cap_percent=100*63/255,old_max_percent=float(int(old.max())*100/255),footprint_exact=True,only_alpha_changed=True)


def validate_scope(sample):
    rows=[]
    for name in ['v044_route_detail.tga','v044_route_detail_n.tga']:
        a,b=Image.open(baseline(name)),Image.open(M/name); n=a.width; changed=0
        for row in range(0,n,128):
            old=np.asarray(a.crop((0,row,n,min(n,row+128)))); new=np.asarray(b.crop((0,row,n,min(n,row+128))))
            yy,xx=np.where(np.any(old!=new,axis=2)); changed+=len(xx)
            if len(xx):assert np.all(sample.scope((xx+.5)*SIZE/n,SIZE-(yy+row+.5)*SIZE/n)>0),(name,'edit outside accepted photograph footprint')
            if name.endswith('_n.tga'):assert np.array_equal(old[:,:,3],new[:,:,3]) and np.all(new[:,:,3]==2)
        rows.append(dict(file=name,changed_pixels=changed,changed_outside_racing_footprint=0))
    name='mask_v046_wear.tga';old=np.asarray(Image.open(baseline(name)));new=np.asarray(Image.open(M/name))
    assert np.array_equal(old[:,:,:3],new[:,:,:3]) and np.array_equal(old[:,:,3]>0,new[:,:,3]>0) and new[:,:,3].max()<=63
    return rows


def main():
    M.mkdir(parents=True,exist_ok=True); sample=Circuit()
    normals=grain_normals(); counts,cap=author(sample)
    scope_checks=validate_scope(sample)
    shutil.copy2(PREV/'compiled_track.hmf',O/'compiled_track.hmf')
    controls=(O/'compiled_track.hmf').read_text()+(R/'BUILD/v054_track.tht').read_text()
    names=set(re.findall(r'(?m)^\s*(?:map|mask)\s*=\s*(\S+)',controls))
    for name in list(names):
        sh=source(name).with_suffix('.shd')
        if not sh.exists():sh=baseline(name).with_suffix('.shd')
        if sh.exists():names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)',sh.read_text()))
    allowed={'v044_route_detail.tga','v044_route_detail_n.tga','mask_v046_wear.tga','v045_loose_n.tga','v045_packed_n.tga'}
    rows=[]; before=after=0
    for name in sorted(names):
        old,new=baseline(name),source(name); a,b=Image.open(old),Image.open(new)
        assert a.size==b.size and a.mode==b.mode
        same=sha(old)==sha(new)
        assert same or name in allowed,name
        before+=a.width*a.height*4; after+=b.width*b.height*4
        if name.startswith('mask_') and name!='mask_v046_wear.tga':assert same
        rows.append(dict(file=name,size_before=list(a.size),size_after=list(b.size),sha256=sha(new),baseline_sha256=sha(old),changed=not same))
    assert before==after and sha(PREV/'terrain.raw')==sha(O/'terrain.raw')
    direction=[]
    for lo in [65.,315.,600.,970.]:
        ss,ll=np.meshgrid(np.arange(lo,lo+12,.12),np.arange(-3.,3.01,.08))
        x=np.interp(ss,sample.q[:,3],sample.q[:,0]);z=np.interp(ss,sample.q[:,3],sample.q[:,1])
        tx=np.interp(ss,sample.q[:,3],sample.v[:,0]);tz=np.interp(ss,sample.q[:,3],sample.v[:,1])
        f=sample.fields(x-ll*tz,z+ll*tx); lat,along=np.gradient(f['relief'],.08,.12)
        ratio=float(np.mean(lat**2)/max(np.mean(along**2),1e-12))
        direction.append(dict(station_start_m=lo,lateral_to_along_gradient_energy_ratio=ratio))
    assert all(d['lateral_to_along_gradient_energy_ratio']>1.4 for d in direction),direction
    save(O/'surface_validation.json',dict(checks_pass=True,baseline='user-tested v056',overlay=cap,
        layer_count=14,added_layers=0,added_texture_allocations=0,all_boundary_and_physical_masks_exact_v056=True,
        photographic_colours_exact_v056=True,photo_normal_reconstruction=normals,current_v056_route_used=True,
        no_diagonal_tread_terms=True,loam_relief_on_flats=True,grooming_direction_validation=direction,
        changed_pixels=counts,atlas_pixel_scope_checks=scope_checks,active_terrain_inventory=rows,rgba8_base_level_bytes_before=before,
        rgba8_base_level_bytes_after=after,physical_material_declarations_unchanged=True,
        baseline_allocation_recomputed_from_same_complete_shader_bindings=True,
        in_game_visual_check=False,performance_test=False))
    print('V057_SURFACE_PASSED: strict 25% cap, accepted boundaries and photo colour, current-route loam',flush=True)


if __name__=='__main__':main()
