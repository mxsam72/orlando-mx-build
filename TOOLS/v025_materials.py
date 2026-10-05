"""Original, deterministic terrain appearance; never modifies physical inputs.

Fine granular tiles carry the close-up detail. A non-repeating 600 m wear atlas
uses the v024 route and individual authored rut trajectories for the middle and
large scales. Only native documented TGA/HMF/SHD features are emitted.
"""
from pathlib import Path
import argparse, json, hashlib, shutil, re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from v024_common import route

R = Path(__file__).resolve().parents[1]
S = R/'V025_SOURCE'
O = R/'V025_OUTPUT'
M = O/'materials'
SIZE = 600.

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def ease(x):
    x = np.clip(x,0,1)
    return x*x*x*(10-15*x+6*x*x)
def pd(s,c,L): return (s-c+L/2)%L-L/2

def periodic_image(im):
    """Periodic-plus-smooth decomposition removes photographic edge jumps."""
    a = np.asarray(im,dtype=np.float32)
    n,m = a.shape[:2]
    v = np.zeros_like(a)
    v[0] = a[-1]-a[0]; v[-1] = -v[0]
    v[:,0] += a[:,-1]-a[:,0]; v[:,-1] += a[:,0]-a[:,-1]
    denom = (2*np.cos(2*np.pi*np.arange(n)/n)[:,None] +
             2*np.cos(2*np.pi*np.arange(m)/m)[None,:]-4)
    denom[0,0] = 1
    f = np.fft.fft2(v,axes=(0,1))/denom[...,None]; f[0,0] = 0
    return a-np.fft.ifft2(f,axes=(0,1)).real.astype(np.float32)

def save_mask(path,a):
    ar=np.uint8(np.rint(np.clip(a,0,1)*255))
    im=Image.new('RGBA',(ar.shape[1],ar.shape[0]),'white')
    im.putalpha(Image.fromarray(ar)); im.save(path)

def normals(height,spacing,strength,alpha):
    gx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*spacing)
    gy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*spacing)
    v=np.stack([-gx*strength,gy*strength,np.ones_like(height)],axis=2)
    v/=np.linalg.norm(v,axis=2)[...,None]
    a=np.empty((*height.shape,4),np.uint8)
    a[...,:3]=np.uint8(np.rint(np.clip(v*.5+.5,0,1)*255))
    a[...,3]=alpha if np.isscalar(alpha) else np.uint8(alpha)
    return a

def tiles(spec):
    n=spec['tile_size'];rng=np.random.default_rng(spec['seed'])
    im=Image.open(S/spec['source_asset']).convert('RGB').resize((n,n),Image.Resampling.LANCZOS)
    base=periodic_image(im); luma=base@[.2126,.7152,.0722]
    detail=luma-gaussian_filter(luma,35,mode='wrap')
    detail=detail*.94 + (rng.standard_normal((n,n)).astype(np.float32))*1.1
    detail=np.clip(detail,-40,45)
    for name in ['soil','prepared','worked','sand']:
        d=detail.copy()
        if name=='prepared':d=gaussian_filter(d,.48,mode='wrap')*.84
        if name=='sand':d=gaussian_filter(d,.32,mode='wrap')*.58
        if name=='worked':d*=1.10
        mean=np.array(spec['palette'][name],np.float32)
        rgb=np.uint8(np.rint(np.clip(mean+d[...,None]*[1,.94,.82],0,255)))
        for wet in [False,True]:
            stem='v025_'+name+('_wet' if wet else '')
            ar=rgb if not wet else np.uint8(np.rint(rgb.astype(float)*spec['wet_color_factor']))
            Image.fromarray(ar).save(M/(stem+'.tga'))
            (M/(stem+'.shd')).write_text('bump\n{\n map = v025_'+name+'_n.tga\n repetitions = 0\n}\nspecular\n{\n shininess = 8\n}\n')
        h=(gaussian_filter(d,.6,mode='wrap')-gaussian_filter(d,7,mode='wrap'))/255
        Image.fromarray(normals(h,1.,spec['normal_strength'][name],spec['specular_alpha'][name])).save(M/('v025_'+name+'_n.tga'))
    grass=R/'BUILD/v009_work/04_TEXTURES/grass.tga'
    if not grass.exists():grass=R/'V025_AUDIT/textures/grass.png'
    g=np.asarray(Image.open(grass).convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS),np.float32)
    # Retain the original vegetation detail while restoring a modest Florida green.
    g=g-g.mean(axis=(0,1))+np.array([90,105,61],np.float32)
    Image.fromarray(np.uint8(np.rint(np.clip(g,0,255)))).save(M/'v025_grass.tga')
    (M/'v025_grass.shd').write_text('bump\n{\n map = grass_n.tga\n repetitions = 0\n}\nspecular\n{\n shininess = 10\n}\n')

def macro_noise(n,rng,knots):
    small=rng.standard_normal((knots,knots)).astype(np.float32)
    im=Image.fromarray(small).resize((n,n),Image.Resampling.BICUBIC)
    a=np.asarray(im,dtype=np.float32).copy()
    a=gaussian_filter(a,n/knots*.16)
    return np.clip(a/max(a.std(),1e-5),-2.5,2.5)

def build_atlas(spec):
    n=spec['atlas_size'];LUT=read(R/'V009_SOURCE/baseline_geometry.json')
    geom=read(R/'V024_SOURCE/v024_geometry_spec.json')
    profiles=read(R/'V024_OUTPUT/jump_profiles.json')
    q,w=route();L=q[-1,3];tree=cKDTree(q[:-1,:2])
    rng=np.random.default_rng(spec['seed']+1)
    macro=macro_noise(n,rng,22); medium=macro_noise(n,rng,180)
    fine=macro_noise(n,rng,800)
    color=np.zeros((n,n,3),np.uint8);opacity=np.zeros((n,n),np.float32)
    relief=np.zeros((n,n),np.float32)
    worked=np.zeros((n,n),np.float32);edge=np.zeros((n,n),np.float32)
    core_all=np.zeros((n,n),np.float32);groove_all=np.zeros((n,n),np.float32)
    axis=np.linspace(0,SIZE,n,dtype=np.float32)
    cfgs={t['id']:t for t in geom['berms']}
    def gauss(s,c,width):return np.exp(-(pd(s,c,L)/width)**2)
    for row in range(0,n,64):
        z,x=np.meshgrid(SIZE-axis[row:row+64],axis,indexing='ij')
        pts=np.column_stack([x.ravel(),z.ravel()])
        dist,ind=tree.query(pts,workers=2);th=q[ind,2];dv=pts-q[ind,:2]
        lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th)
        s=(q[ind,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th))%L
        effective=np.full_like(s,8.6)
        primary_center=.45*np.sin(2*np.pi*s/L*9)+.23*np.sin(2*np.pi*s/L*21)
        secondary_center=primary_center-2.0
        corner=np.zeros_like(s);brake=np.zeros_like(s);exitwear=np.zeros_like(s)
        turngroove=np.zeros_like(s)
        for turn in LUT['turns']:
            cfg=cfgs[turn['id']];dd=pd(s,turn['mid'],L)
            extent=(turn['arc_end']-turn['arc_start'])/2
            fade=ease((dd+extent+16)/18)*(1-ease((dd-extent+3)/18))
            effective+=(cfg['effective_width_m']-8.6)*fade
            phase=np.clip((dd+extent)/(2*extent),0,1)
            paths=[]
            for path in cfg['rut_paths']:
                pos=np.where(phase<.5,
                    path['entry_out_m']+(path['apex_out_m']-path['entry_out_m'])*ease(2*phase),
                    path['apex_out_m']+(path['exit_out_m']-path['apex_out_m'])*ease(2*phase-1))
                paths.append(-np.sign(turn['angle'])*pos)
            primary_center=primary_center*(1-fade)+paths[-1]*fade
            secondary_center=secondary_center*(1-fade)+paths[0]*fade
            corner=np.maximum(corner,fade)
            brake=np.maximum(brake,np.exp(-((dd+extent+5)/15)**4))
            exitwear=np.maximum(exitwear,np.exp(-((dd-extent-4)/12)**4))
            # Each corner has its own trajectories, spacing and broken lengths.
            for j,pos in enumerate(paths):
                wander=.08*np.sin(2*np.pi*s/L*(29+j*8)+j*1.6)
                channel=np.exp(-((lat-pos-wander)/(.18+.05*j))**2)
                broken=.55+.45*np.sin(dd*.18+j*1.7)**2
                turngroove=np.maximum(turngroove,channel*fade*broken)
        face=np.zeros_like(s);landing=np.zeros_like(s)
        for p in profiles:
            lip=p['lip_s'];lm=p['landmarks_m']
            face=np.maximum(face,gauss(s,lip-p['face_m']*.40,max(p['face_m']*.70,3)))
            offsets=p.get('crest_offsets_m') or [0]
            for off in offsets[1:]:
                face=np.maximum(face,gauss(s,lip+off-2.0,3.8)*.65)
            landbreak=lip+lm.get('landing_break',max(offsets))
            endpoint=lip+lm['runout_end']
            landing=np.maximum(landing,gauss(s,(landbreak+endpoint)/2,max((endpoint-landbreak)*.45,4)))
        sh=x.shape;sl=slice(row,row+len(x));ma=macro[sl].ravel();md=medium[sl].ravel();fi=fine[sl].ravel()
        half=effective/2
        core=(1-ease((np.abs(lat)-half+.35-.10*md)/1.35))*(1-ease((dist-half+.35)/1.35))
        shoulder=(1-ease((dist-half-.30)/2.8))*(1-core)
        activity=np.clip(.18+.32*corner+.25*brake+.25*exitwear+.18*face+.16*landing,0,1)
        primary=np.exp(-((lat-primary_center)/(1.10+.38*brake+.27*exitwear))**2)
        secondary=np.exp(-((lat-secondary_center)/(.65+.18*exitwear))**2)
        packed=np.clip(primary*.74+secondary*.30,0,1)*core
        directional=turngroove.copy()
        for j,off in enumerate([-1.48,-.93,-.42,.13,.65,1.21,1.72]):
            wander=.16*np.sin(2*np.pi*s/L*(24+j*6)+j)
            line=np.exp(-((lat-primary_center-off-wander)/(.15+.008*j))**2)
            broken=.36+.64*np.sin(2*np.pi*s/L*(43+j*13)+j*.91)**2
            directional=np.maximum(directional,line*broken*(.28+.72*np.maximum(face,landing)))
        directional*=core*(.32+.68*activity)
        churn=np.clip((brake*.40+exitwear*.65+corner*.20)*(1-packed*.7),0,1)*core
        dryside=np.clip((np.abs(lat)/np.maximum(half,1))**2,0,1)
        base=np.array(spec['palette']['prepared'],float)
        pc=np.array(spec['palette']['packed'],float)
        ec=np.array(spec['palette']['edge'],float)
        values=base[None,:]+packed[:,None]*(pc-base)[None,:]*.94
        values+=(dryside*(1-corner*.35))[:,None]*(ec-base)[None,:]*.65
        variation=(11.0*ma+5.0*md+1.7*fi)*(1-packed*.50)
        values+=(variation-24*directional-8*churn)[:,None]*[1,.92,.78]
        # Very mild moisture variation localized in wear, never uniformly wet.
        values-=np.clip(-ma-.85,0,.65)[:,None]*corner[:,None]*packed[:,None]*9
        amount=core*(.30+.38*packed+.20*directional+.12*activity)+shoulder*(.26+.06*md)
        amount=np.clip(amount,0,spec['atlas_max_opacity'])
        # Atlas opacity varies across the lane; no whole-lap painted stripe.
        color[sl]=np.uint8(np.rint(np.clip(values.reshape(*sh,3),0,255)))
        opacity[sl]=amount.reshape(sh)
        relief[sl]=(-spec['virtual_rut_depth_m']*directional+fi*.0014*churn).reshape(sh)
        worked[sl]=np.clip(churn*(.60+.10*fi),0,.7).reshape(sh)
        edge[sl]=shoulder.reshape(sh);core_all[sl]=core.reshape(sh);groove_all[sl]=directional.reshape(sh)
        if row%1024==0:print('v025 wear atlas row',row,flush=True)
    Image.fromarray(color).save(M/'v025_trackwear.tga')
    Image.fromarray(np.uint8(np.rint(color*spec['wet_color_factor']))).save(M/'v025_trackwear_wet.tga')
    save_mask(M/'mask_v025_wear.tga',opacity)
    # Low specularity in normal alpha; no unsupported PBR roughness shader.
    al=np.uint8(2+2*core_all)
    normal=normals(relief,SIZE/(n-1),1.,al)
    Image.fromarray(normal).save(M/'v025_trackwear_n.tga')
    for stem in ['v025_trackwear','v025_trackwear_wet']:
        (M/(stem+'.shd')).write_text('bump\n{\n map = v025_trackwear_n.tga\n repetitions = 1\n}\nspecular\n{\n shininess = 8\n}\n')
    # New visual masks are siblings; the original physics masks remain exact.
    maskdir=R/'V024_OUTPUT/masks'
    def original(name):
        return np.asarray(Image.open(maskdir/(name+'.tga')).getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    prepared=np.maximum(original('visual_racing'),core_all*.97)
    loose=np.clip(np.maximum(original('visual_worked')*.45,worked),0,.78)
    grass=original('visual_grass')
    grass*=np.clip(1-edge*(.42+.16*medium+.12*fine),.20,1)
    for name,a in [('visual_racing',prepared),('visual_worked',loose),('visual_grass',grass)]:
        small=Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR)
        save_mask(M/('mask_'+name+'.tga'),np.asarray(small))
    return dict(atlas_size=n,atlas_ground_pixel_m=SIZE/(n-1),
        wear_coverage_pixels=int((opacity>.02).sum()),max_opacity=float(opacity.max()),
        mean_core_opacity=float(opacity[core_all>.9].mean()),
        primary_secondary_grooves_pixels=int((groove_all>.4).sum()),
        normal_alpha_range=[int(normal[...,3].min()),int(normal[...,3].max())],
        physical_masks_modified=False,geometry_modified=False)

def hmf(spec):
    p=R/'BUILD/v009_work/BUILD/track.hmf'
    if not p.exists():return
    text=p.read_text();match=re.search(r'num_layers\s*=\s*(\d+)',text)
    count=int(match[1]);assert count==6,'Inspect changed baseline HMF before applying v025'
    for name in ['soil','prepared','sand','worked']:
        text=re.sub(r'(?m)(\bmap\s*=\s*)'+name+r'(_wet)?\.tga',lambda m:m[1]+'v025_'+name+(m[2] or '')+'.tga',text)
        # Edit only the containing layer's repetition; masks/thickness are retained.
        pattern=r'(map\s*=\s*v025_'+name+r'\.tga\s+repetitions\s*=\s*)\d+'
        text,n=re.subn(pattern,lambda m:m[1]+str(spec['repetitions'][name]),text)
        assert n==1,'Missing baseline layer for '+name
    text,n=re.subn(r'(?m)(\bmap\s*=\s*)grass\.tga',lambda m:m[1]+'v025_grass.tga',text)
    assert n==1,'Missing baseline grass layer'
    text=text[:match.start(1)]+str(count+1)+text[match.end(1):]
    text+='\nlayer'+str(count)+'\n{\n map = v025_trackwear.tga\n repetitions = 1\n mask = mask_v025_wear.tga\n frame1\n {\n  map = v025_trackwear_wet.tga\n }\n}\n'
    (M/'track.hmf').write_text(text)

def main():
    M.mkdir(parents=True,exist_ok=True);spec=read(S/'material_spec.json')
    assert digest(S/spec['source_asset'])==spec['source_asset_sha256'],'Original source texture changed'
    tiles(spec);qa=build_atlas(spec);hmf(spec)
    qa.update(version='v025',original_source_sha256=digest(S/spec['source_asset']),
        material_spec_sha256=digest(S/'material_spec.json'),in_game_visual_check=False,
        files={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(M.iterdir()) if p.is_file()})
    (O/'material_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
    print('v025 original materials generated; physics and geometry untouched.',flush=True)

if __name__=='__main__':main()
