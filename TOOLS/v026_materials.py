"""Independent neutral soil structures; local wear is a mask of fine tiles.

No low-resolution diffuse/normal atlas can replace close-up dirt detail.
Large-scale direction is in masks; microstructure is in tiled normal maps.
"""
from pathlib import Path
import json, hashlib, re
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw, ImageFont
from v025_materials import periodic_image, normals, save_mask, macro_noise, ease
R=Path(__file__).resolve().parents[1];S=R/'V026_SOURCE';O=R/'V026_OUTPUT';M=O/'materials';SIZE=600.
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def tiles(spec):
    n=spec['tile_size'];provenance=read(S/'asset_provenance.json');r=np.random.default_rng(spec['seed']);arrays={};qa=[]
    for family in ['soil','prepared','worked','sand']:
        p=S/provenance[family]['file'];assert sha(p)==provenance[family]['sha256']
        a=periodic_image(Image.open(p).convert('RGB').resize((n,n),Image.Resampling.LANCZOS));lum=a@np.array([.2126,.7152,.0722]);lum-=gaussian_filter(lum,60,mode='wrap')
        # Local fragments survive without repeating a broad photographic shade.
        detail=np.clip(lum,-46,46);tint=a-a.mean(axis=2)[...,None];tint-=tint.mean(axis=(0,1));tint*=.16
        arrays[family]=(detail,tint)
    for name,family in spec['source_families'].items():
        detail,tint=arrays[family];d=detail.copy()
        if name in ['prepared','packed','face']:d=gaussian_filter(d,.32,mode='wrap')
        gain={'soil':.85,'prepared':.72,'worked':.88,'sand':.64,'packed':.68,'face':.71}[name]
        rgb=np.clip(np.array(spec['palette'][name])+gain*d[...,None]+tint,0,255)
        # Periodic edge values also protect normal-map seams at tile wraps.
        rgb[[0,-1],:]=rgb[[0,-1],:].mean(axis=0);rgb[:,[0,-1]]=rgb[:,[0,-1]].mean(axis=1)[:,None]
        dry=np.uint8(np.rint(rgb));Image.fromarray(dry).save(M/f'v026_{name}.tga')
        # Relief is an art-directed granular height field, not a claim that
        # diffuse shadows in reference photos measure physical depressions.
        structure=gaussian_filter(d,1.0,mode='wrap')-gaussian_filter(d,15,mode='wrap')
        structure/=max(float(structure.std()),1.0);structure=np.clip(structure,-2.4,2.4)
        micro=r.standard_normal((n,n));micro=gaussian_filter(micro,.55,mode='wrap');micro/=max(float(micro.std()),1e-6)
        h=(structure*.65+micro*.13)*spec['height_amplitude_m'][name]
        normal=normals(h,(SIZE/spec['repetitions'][name])/n,1.,spec['specular_alpha'][name]);Image.fromarray(normal).save(M/f'v026_{name}_n.tga')
        factor=.85+.045*np.tanh(gaussian_filter(structure,35,mode='wrap'))
        Image.fromarray(np.uint8(np.rint(dry*factor[...,None]))).save(M/f'v026_{name}_wet.tga')
        for wet in ['', '_wet']:
            (M/f'v026_{name}{wet}.shd').write_text(f'bump\n{{\n map = v026_{name}_n.tga\n repetitions = 0\n}}\nspecular\n{{\n shininess = 8\n}}\n')
        interior=float(np.abs(dry.astype(float)[1:]-dry.astype(float)[:-1]).mean());seam=float(np.abs(dry[0].astype(float)-dry[-1].astype(float)).mean())
        qa.append(dict(material=name,source_family=family,mean_rgb=np.round(dry.mean(axis=(0,1)),2).tolist(),world_tile_m=SIZE/spec['repetitions'][name],normal_height_amplitude_m=spec['height_amplitude_m'][name],edge_jump_mean=seam,interior_neighbor_mean=interior))
    gp=R/'BUILD/v009_work/04_TEXTURES/grass.tga'
    if not gp.exists():gp=R/'V025_OUTPUT/materials/v025_grass.tga'
    g=np.array(Image.open(gp).convert('RGB').resize((1024,1024)),float);g=g-g.mean(axis=(0,1))+spec['palette']['grass'];Image.fromarray(np.uint8(np.clip(g,0,255))).save(M/'v026_grass.tga')
    (M/'v026_grass.shd').write_text('bump\n{\n map = grass_n.tga\n repetitions = 0\n}\nspecular\n{\n shininess = 10\n}\n')
    return qa

def fields(spec):
    n=spec['mask_size'];d=dict(np.load(O/'route.npz'));q=d['q'];w=d['width'];tree=cKDTree(q[:-1,:2]);turns=read(O/'turns.json');geom=read(O/'geometry_spec.json');profiles=read(O/'jump_profiles.json');bc={t['id']:t for t in geom['berms']}
    r=np.random.default_rng(spec['seed']+1);medium=macro_noise(n,r,180);fine=macro_noise(n,r,700);macro=macro_noise(n,r,32)
    prepared=np.zeros((n,n),np.float32);worked=prepared.copy();packed=prepared.copy();face=prepared.copy();margin=prepared.copy();distance=prepared.copy();stations=prepared.copy();widths=prepared.copy()
    axis=np.linspace(0,SIZE,n);L=q[-1,3]
    pd=lambda s,c:(s-c+L/2)%L-L/2
    for row in range(0,n,64):
        z,x=np.meshgrid(SIZE-axis[row:row+64],axis,indexing='ij');pts=np.c_[x.ravel(),z.ravel()];dist,i=tree.query(pts,workers=2);th=q[i,2];dv=pts-q[i,:2];lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th);s=(q[i,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th))%L
        width=np.full_like(s,8.6);corner=np.zeros_like(s);channel=np.zeros_like(s);deposits=np.zeros_like(s)
        sh=x.shape;sl=slice(row,row+len(x));noise=medium[sl].ravel();fi=fine[sl].ravel();ma=macro[sl].ravel()
        for k,t in enumerate(turns):
            c=bc[t['id']];extent=(t['arc_end']-t['arc_start'])/2;dd=pd(s,t['mid']);lead=5 if t['id']=='T09' else 12;fade=ease((dd+extent+lead)/16)*(1-ease((dd-extent+3)/15));phase=np.clip((dd+extent)/(2*extent),0,1)
            width+=(c['effective_width_m']-8.6)*fade;corner=np.maximum(corner,fade)
            for j,path in enumerate(c['rut_paths']):
                out=np.where(phase<.5,path['entry_out_m']+(path['apex_out_m']-path['entry_out_m'])*ease(phase*2),path['apex_out_m']+(path['exit_out_m']-path['apex_out_m'])*ease(phase*2-1));center=-np.sign(t['angle'])*out
                wander=.06*np.sin(dd*.16+k*1.7)+.035*noise;spread=.35+.12*j+.05*np.sin(dd*.1+k)
                broken=np.clip(.75+.11*ma+.08*fi,.25,1);line=np.exp(-((lat-center-wander)/spread)**2)*fade*broken
                channel=np.maximum(channel,line)
                bank=np.exp(-((abs(lat-center-wander)-(.75+.18*j))/.55)**2)*fade*np.clip(.55+.18*noise+.12*fi,.1,1)
                deposits=np.maximum(deposits,bank)
        jumpface=np.zeros_like(s);landwear=np.zeros_like(s)
        for p in profiles:
            if p['kind']=='none':continue
            lip=p['lip_s'];a=lip-p['face_m'];b=lip+p['landmarks_m'].get('deck_start',0)+2
            jf=ease((s-a+2)/4)*(1-ease((s-b)/5));jumpface=np.maximum(jumpface,jf)
            lb=lip+p['landmarks_m'].get('landing_break',0);end=lip+p['landmarks_m']['runout_end'];landwear=np.maximum(landwear,np.exp(-((s-(lb+end)/2)/max((end-lb)*.6,3))**2))
        half=width/2;core=(1-ease((abs(lat)-half+.25-.10*noise)/1.8))*(1-ease((dist-half+.25)/1.8));shoulder=(1-ease((dist-half-.5)/3.0))*(1-core)
        # Thin discontinuous selected paths, gently varying across entries,
        # apexes and exits. No dark whole-lap ribbon and no atlas-color stripe.
        center=.35*np.sin(s*.012)+.18*np.sin(s*.032);straight=np.exp(-((lat-center)/(.55+.15*landwear))**2)*np.clip(.42+.20*ma+.12*noise,0,.85)*(1-corner)
        wear=np.clip(channel*.42+straight*.24+landwear*.10,0,spec['packed_max_opacity'])*core
        churn=np.clip(deposits*.56+shoulder*.36+.10*landwear*(1-wear),0,.63)*np.clip(.85+.12*noise,.3,1)
        prepared[sl]=(core*np.clip(.87+.035*noise+.025*ma,.66,.97)).reshape(sh);worked[sl]=churn.reshape(sh);packed[sl]=wear.reshape(sh);face[sl]=(jumpface*core*np.clip(.72+.035*noise,.45,.78)*(1-corner*.55)).reshape(sh);margin[sl]=shoulder.reshape(sh);distance[sl]=dist.reshape(sh);stations[sl]=s.reshape(sh);widths[sl]=w[i].reshape(sh)
        if row%1024==0:print('v026 fine-material masks row',row,flush=True)
    def original(name):return np.asarray(Image.open(R/'V024_OUTPUT/masks'/f'{name}.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    # Preserve off-course visuals while adding only route-local treatment.
    original_racing=original('visual_racing');original_worked=original('visual_worked');grass=original('visual_grass')
    patch=np.asarray(Image.open(O/'local_patch_region.png').resize((n,n),Image.Resampling.NEAREST),np.float32)/255
    racing=np.maximum(original_racing*(1-patch),prepared)
    churn=np.maximum(original_worked*.18*(1-patch),worked)
    grass=grass*(1-prepared*.80)*(1-margin*np.clip(.26+.08*medium,.03,.5));grass*=1-patch*(1-ease((distance-widths/2)/2.5))
    for name,a in [('visual_racing',racing),('visual_worked',churn),('visual_grass',grass),('v026_face',face)]:
        small=np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR));save_mask(M/f'mask_{name}.tga',small)
    save_mask(M/'mask_v026_packed.tga',packed)
    # Only physical mask coverage follows the relocated corridor; names and
    # thicknesses in THT stay exact. Pits/start and gravel are copied unchanged.
    patch_small=np.asarray(Image.fromarray(patch).resize((2048,2048),Image.Resampling.NEAREST));dist_small=np.asarray(Image.fromarray(distance).resize((2048,2048)));width_small=np.asarray(Image.fromarray(widths).resize((2048,2048)))
    newlane=1-ease((dist_small-width_small/2+.3)/1.1)
    physical=[]
    for name in ['racing','shoulder','off','grass','sand','worked']:
        old=np.asarray(Image.open(O/'masks'/f'{name}.tga').getchannel('A'),np.float32)/255
        if name in ['racing','shoulder']:local=newlane
        elif name=='off':local=1-ease((dist_small-width_small/2)/2.5)
        else:local=old*(1-newlane)
        if name=='off':local=1-local
        a=old*(1-patch_small)+local*patch_small;save_mask(O/'masks'/f'{name}.tga',a)
        assert np.array_equal(np.uint8(np.rint(a[patch_small==0]*255)),np.uint8(np.rint(old[patch_small==0]*255)))
        physical.append(name)
    return dict(mask_size=n,packed_max_opacity=float(packed.max()),mean_packed_active_opacity=float(packed[packed>.03].mean()),low_resolution_diffuse_overlay=False,all_wear_layers_have_tiled_color_and_normals=True,physics_mask_coverage_changes_local_only=physical,source_color_atlas_removed=True)

def hmf(spec):
    p=R/'BUILD/v009_work/BUILD/track.hmf';text=p.read_text();count=int(re.search(r'num_layers\s*=\s*(\d+)',text)[1]);assert count==6
    text=re.sub(r'num_layers\s*=\s*6','num_layers = 8',text,count=1)
    for name in ['soil','prepared','sand','worked','grass']:
        text=re.sub(r'(\bmap\s*=\s*)'+name+r'(_wet)?\.tga',lambda m:m[1]+f'v026_{name}'+(m[2] or '')+'.tga',text)
        if name!='grass':text=re.sub(r'(map\s*=\s*v026_'+name+r'\.tga\s+repetitions\s*=\s*)\d+',lambda m:m[1]+str(spec['repetitions'][name]),text)
    for i,name in [(6,'packed'),(7,'face')]:
        text+=f'\nlayer{i}\n{{\n map = v026_{name}.tga\n repetitions = {spec["repetitions"][name]}\n mask = mask_v026_{name}.tga\n frame1\n {{\n  map = v026_{name}_wet.tga\n }}\n}}\n'
    (M/'track.hmf').write_text(text)

def preview(spec):
    font=ImageFont.truetype('DejaVuSans.ttf',19) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').exists() else ImageFont.load_default()
    names=['soil','prepared','worked','sand','packed','face'];im=Image.new('RGB',(1536,1140),(24,27,27));draw=ImageDraw.Draw(im)
    for i,n in enumerate(names):
        a=Image.open(M/f'v026_{n}.tga').resize((512,512),Image.Resampling.LANCZOS);x=i%3*512;y=i//3*570;im.paste(a,(x,y));draw.text((x+12,y+525),'v026 '+n+' | source tile, not game',font=font,fill='white')
    im.save(O/'material_tiles.png')

def main():
    M.mkdir(parents=True,exist_ok=True);spec=read(S/'material_spec.json');qa={'tiles':tiles(spec)};qa.update(fields(spec));hmf(spec);preview(spec)
    qa.update(version='v026',source_checks_pass=True,generated_asset_provenance=read(S/'asset_provenance.json'),dry_matte=True,in_game_visual_check=False,files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.iterdir()) if p.is_file()})
    assert all(x['edge_jump_mean']==0 for x in qa['tiles'])
    for p in M.glob('*.tga'):
        im=Image.open(p);assert im.width>0 and not im.width&(im.width-1) and not im.height&(im.height-1)
    save(O/'material_validation.json',qa);print('v026 independent granular materials validated',flush=True)
if __name__=='__main__':main()
