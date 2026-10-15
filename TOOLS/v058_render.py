"""Perspective-aware source renderer for the three v058 dirt studies.

Sample actual texture pyramids at ray hits, not a preblurred world composite.
Use trilinear mip selection and up to eight directional footprint samples.
The dry diffuse/normal/specular-alpha model is approximate, not the game.
"""
import gc
import json
import math
import re
import sys
from collections import OrderedDict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates, gaussian_filter
from v058_trials import R, PREV, O, M, OUT, S, CACHE, Section, METHODS, source, sha, save
from v049_previews import font, layers

WIDTH,HEIGHT=1600,1000
MAX_AF=8
VIEWS=[
 dict(id='01_tabletop',title='Finish tabletop / riding height',eye_s=6.,target_s=32.,eye_h=1.8,target_h=.55,eye_l=0.,target_l=0.,fov=64.),
 dict(id='02_flat',title='Flat / forward cultivation',eye_s=58.,target_s=79.,eye_h=1.75,target_h=.30,eye_l=.2,target_l=0.,fov=64.),
 dict(id='03_triple',title='Triple approach / jump face',eye_s=120.,target_s=142.,eye_h=1.7,target_h=.65,eye_l=0.,target_l=0.,fov=64.),
 dict(id='04_close',title='Close soil detail / original track edge',eye_s=56.,target_s=59.2,eye_h=.60,target_h=.02,eye_l=3.1,target_l=3.0,fov=59.),
]


class Texture:
    def __init__(self,path):
        self.path=Path(path);im=Image.open(path)
        rgba=im.mode=='RGBA';rgb=im.convert('RGB');alpha=im.getchannel('A') if rgba else None
        self.levels=[];self.width=im.width
        while True:
            a=np.asarray(rgb)
            if rgba:a=np.dstack([a,np.asarray(alpha)])
            self.levels.append(np.ascontiguousarray(a))
            if rgb.width<=2 and rgb.height<=2:break
            size=(max(1,rgb.width//2),max(1,rgb.height//2))
            rgb=rgb.resize(size,Image.Resampling.BOX)
            if rgba:alpha=alpha.resize(size,Image.Resampling.BOX)

    def sample(self,ctx,rep,indices=None):
        if indices is None:indices=np.arange(ctx['x'].size)
        x=ctx['x'][indices];z=ctx['z'][indices]
        major=ctx['major'][indices];minor=ctx['minor'][indices]
        # Ensure the long footprint never exceeds the available anisotropy.
        texels=self.width*rep/600
        width=np.maximum(np.maximum(minor,major/MAX_AF),1/texels)
        lod=np.clip(np.log2(width*texels),0,len(self.levels)-1.001)
        low=lod.astype(np.int16);frac=lod-low
        taps=np.clip(np.ceil(major/width),1,MAX_AF).astype(np.int16)
        output=np.zeros((len(x),self.levels[0].shape[2]),np.float32)
        ex=ctx['ex'][indices];ez=ctx['ez'][indices]
        for tap in range(MAX_AF):
            use=np.flatnonzero(tap<taps)
            if len(use)==0:continue
            offset=((tap+.5)/taps[use]-.5)*major[use]
            xx=x[use]+ex[use]*offset;zz=z[use]+ez[use]*offset
            for level in np.unique(low[use]):
                local=np.flatnonzero(low[use]==level);ids=use[local]
                for delta,weight in [(0,1-frac[ids]),(1,frac[ids])]:
                    li=min(int(level)+delta,len(self.levels)-1);a=self.levels[li]
                    coords=[np.mod((600-zz[local])*rep/600,1)*a.shape[0]-.5,np.mod(xx[local]*rep/600,1)*a.shape[1]-.5]
                    for channel in range(a.shape[2]):
                        sampled=map_coordinates(a[:,:,channel],coords,order=1,mode='grid-wrap',output=np.float32)
                        output[ids,channel]+=sampled*weight/taps[ids]
        return output


class Materials:
    def __init__(self):
        self.textures={};self.masks={}
        self.blocks=list(layers((PREV/'compiled_track.hmf').read_text()))

    def texture(self,path):
        path=str(Path(path))
        if path not in self.textures:self.textures[path]=Texture(path)
        return self.textures[path]

    def sample(self,name,ctx,rep,indices=None):
        path=M/name if name.startswith('v058_') else source(name)
        return self.texture(path).sample(ctx,rep,indices)

    def mask(self,name,ctx):
        if name not in self.masks:self.masks[name]=np.asarray(Image.open(source(name)).getchannel('A'),np.float32)/255
        a=self.masks[name]
        return map_coordinates(a,[(600-ctx['z'])/600*a.shape[0]-.5,ctx['x']/600*a.shape[1]-.5],order=1,mode='nearest')

    def layer(self,index,ctx,override=None):
        block=next(b for i,b in self.blocks if i==index)
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1]
        rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        mm=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        alpha=self.mask(mm[1],ctx) if mm else np.ones(ctx['x'].size,np.float32)
        paths=[PREV/'materials',R/'V054_OUTPUT/materials',R/'V052_OUTPUT/materials',R/'V046_OUTPUT/materials',R/'V044_OUTPUT/materials']
        sh=next((p/Path(name).with_suffix('.shd') for p in paths if (p/Path(name).with_suffix('.shd')).is_file()),None)
        normal_name=None;nrep=rep
        if sh:
            st=sh.read_text();bump=re.search(r'bump\s*\{([^}]+)\}',st)
            if bump:
                normal_name=re.search(r'map\s*=\s*(\S+)',bump[1])[1]
                rr=re.search(r'repetitions\s*=\s*([\d.]+)',bump[1]);nrep=float(rr[1]) if rr else rep
                # This inheritance is a source-preview assumption shared by
                # reference and candidates. Native zero semantics are unproven.
                nrep=nrep or rep
        if override:
            name=override.get('map',name);rep=override.get('rep',rep)
            normal_name=override.get('normal',normal_name);nrep=override.get('nrep',nrep)
            alpha=alpha*override.get('alpha_scale',1.)
        idx=np.flatnonzero(alpha>1e-5)
        rgb=np.zeros((ctx['x'].size,3),np.float32)
        normal=np.empty((ctx['x'].size,4),np.float32);normal[:]=[127.5,127.5,255.,0.]
        if len(idx):
            rgb[idx]=self.sample(name,ctx,rep,idx)[:,:3]
            if normal_name:
                sampled=self.sample(normal_name,ctx,nrep,idx)
                normal[idx,:sampled.shape[1]]=sampled
        return rgb,normal,alpha


def blend(base,candidate,alpha):
    return base*(1-alpha[:,None])+candidate*alpha[:,None]


def location(section,station,lateral,height):
    x=np.interp(station,section.q[:,3],section.q[:,0]);z=np.interp(station,section.q[:,3],section.q[:,1])
    tx=np.interp(station,section.q[:,3],section.v[:,0]);tz=np.interp(station,section.q[:,3],section.v[:,1])
    x-=lateral*tz;z+=lateral*tx
    return np.array([x,z,float(section.terrain.ground(np.array([x]),np.array([z]))[0])+height],np.float32)


def footprint(x,z):
    xy,xx=np.gradient(x);zy,zx=np.gradient(z)
    a=xx*xx+xy*xy;b=xx*zx+xy*zy;d=zx*zx+zy*zy
    root=np.sqrt(np.maximum((a-d)**2+4*b*b,0))
    l1=np.maximum((a+d+root)/2,1e-12);l2=np.maximum((a+d-root)/2,1e-12)
    ex=b;ez=l1-a;den=np.hypot(ex,ez)
    ex=np.where(den>1e-12,ex/np.maximum(den,1e-12),1.)
    ez=np.where(den>1e-12,ez/np.maximum(den,1e-12),0.)
    return dict(major=np.sqrt(l1).ravel().astype(np.float32),minor=np.sqrt(l2).ravel().astype(np.float32),ex=ex.ravel().astype(np.float32),ez=ez.ravel().astype(np.float32))


def trace(section,view):
    filename=CACHE/(view['id']+'_hits.npz')
    eye=location(section,view['eye_s'],view['eye_l'],view['eye_h'])
    target=location(section,view['target_s'],view['target_l'],view['target_h'])
    if filename.exists():
        data=dict(np.load(filename));assert int(data['width'])==WIDTH and int(data['height'])==HEIGHT
        return {k:v for k,v in data.items() if k not in ['width','height']}
    sy,sx=np.mgrid[:HEIGHT,:WIDTH].astype(np.float32)
    forward=target-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    tangent=math.tan(math.radians(view['fov']/2))
    rx=(sx+.5-WIDTH/2)/(WIDTH/2)*tangent;ry=-(sy+.5-HEIGHT/2)/(WIDTH/2)*tangent
    rays=forward+rx[:,:,None]*right+ry[:,:,None]*up;rays/=np.linalg.norm(rays,axis=2,keepdims=True);rays=rays.astype(np.float32)
    hit=np.zeros((HEIGHT,WIDTH),bool);lo=np.zeros((HEIGHT,WIDTH),np.float32);hi=lo.copy()
    for distance in np.r_[.15,np.arange(.65,160.1,1.5)]:
        p=eye+rays*distance;below=p[:,:,2]<=section.terrain.ground(p[:,:,0],p[:,:,1]);new=below&~hit
        lo[new]=max(0,distance-1.5);hi[new]=distance;hit|=new
    for _ in range(15):
        distance=(lo+hi)/2;p=eye+rays*distance[:,:,None];below=p[:,:,2]<=section.terrain.ground(p[:,:,0],p[:,:,1])
        hi=np.where(hit&below,distance,hi);lo=np.where(hit&~below,distance,lo)
    p=eye+rays*hi[:,:,None];x=p[:,:,0];z=p[:,:,1]
    # Invalid sky pixels use a smooth far plane so they do not poison nearby
    # texture derivatives. Their colours are replaced by the same sky later.
    far=eye+rays*160;x=np.where(hit,x,far[:,:,0]);z=np.where(hit,z,far[:,:,1])
    result=dict(x=x.ravel(),z=z.ravel(),ground=p[:,:,2].ravel(),hit=hit.ravel(),eye=eye,target=target,**footprint(x,z))
    np.savez_compressed(filename,width=WIDTH,height=HEIGHT,**result)
    print('Traced',view['id'],int(hit.sum()),'terrain pixels',flush=True)
    return result


def context(section,data):
    result=data.copy();x,z=result['x'],result['z']
    result['scope']=section.section(x.reshape(HEIGHT,WIDTH),z.reshape(HEIGHT,WIDTH)).ravel()
    hx,hz=section.terrain.slope(x,z)
    base=np.stack([-hx,-hz,np.ones_like(hx)],1);base/=np.linalg.norm(base,axis=1,keepdims=True)
    tangent=np.stack([np.ones_like(hx),np.zeros_like(hx),hx],1);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
    result.update(base=base,tangent=tangent,bitangent=np.cross(base,tangent))
    return result


def shade(section,ctx,rgb,raw_normal):
    tn=raw_normal[:,:3]/127.5-1;tn/=np.maximum(np.linalg.norm(tn,axis=1,keepdims=True),1e-7)
    n=tn[:,0,None]*ctx['tangent']+tn[:,1,None]*ctx['bitangent']+tn[:,2,None]*ctx['base']
    n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-7)
    light=np.array([2.,-7.,10.],np.float32);light/=np.linalg.norm(light)
    diffuse=.38+.70*np.maximum(n@light,0)
    point=np.stack([ctx['x'],ctx['z'],ctx['ground']],1);view=ctx['eye']-point;view/=np.maximum(np.linalg.norm(view,axis=1,keepdims=True),1e-7)
    halfway=view+light;halfway/=np.maximum(np.linalg.norm(halfway,axis=1,keepdims=True),1e-7)
    specular=raw_normal[:,3]/255*np.maximum(np.sum(n*halfway,axis=1),0)**8*.45
    result=np.uint8(np.rint(np.clip((rgb/255)**2.2*diffuse[:,None]+specular[:,None],0,1)**(1/2.2)*255))
    valid=ctx['hit']&(ctx['x']>=0)&(ctx['x']<=600)&(ctx['z']>=0)&(ctx['z']<=600)
    result[~valid]=[157,194,226]
    return Image.fromarray(result.reshape(HEIGHT,WIDTH,3))


def render_view(section,materials,view):
    OUT.mkdir(parents=True,exist_ok=True)
    ctx=context(section,trace(section,view));prefix_rgb=np.zeros((WIDTH*HEIGHT,3),np.float32);prefix_n=np.empty((WIDTH*HEIGHT,4),np.float32);prefix_n[:]=[127.5,127.5,255,0]
    for index,block in materials.blocks:
        if index>10:break
        rgb,n,alpha=materials.layer(index,ctx);prefix_rgb=blend(prefix_rgb,rgb,alpha);prefix_n=blend(prefix_n,n,alpha)
    rgb11,n11,a11=materials.layer(11,ctx);rgb12,n12,a12=materials.layer(12,ctx);rgb13,n13,a13=materials.layer(13,ctx)
    base_rgb=blend(blend(prefix_rgb,rgb11,a11),rgb12,a12);base_n=blend(blend(prefix_n,n11,a11),n12,a12)
    reference_rgb=blend(base_rgb,rgb13,a13);reference_n=blend(base_n,n13,a13)
    candidates=OrderedDict(v056=(reference_rgb,reference_n))
    # A is the missing one-variable control from the canceled v057 experiment.
    cap=63/255/(232/255)
    candidates['A']=(blend(base_rgb,rgb13,a13*cap),blend(base_n,n13,a13*cap))
    # B changes colour frequency only. The normal field is exactly v056.
    candidates['B']=(blend(base_rgb,rgb11,a13),reference_n.copy())
    crgb,cn,ca=materials.layer(11,ctx,dict(map='v058_c_loose.tga',rep=200,nrep=200))
    cmacro=materials.sample('v058_c_macro_n.tga',ctx,1.)
    cbase_rgb=blend(blend(prefix_rgb,crgb,ca),rgb12,a12*.70)
    cbase_n=blend(blend(prefix_n,cn,ca),n12,a12*.70)
    strength=.55/(232/255)
    candidates['C']=(blend(cbase_rgb,crgb,a13*strength),blend(cbase_n,cmacro,a13*strength))
    rows=[];scope=ctx['scope'];valid_scope=scope>.98
    assert np.count_nonzero(valid_scope)>WIDTH*HEIGHT*.04,('Camera misses test section',view['id'])
    for method,(rgb,n) in candidates.items():
        if method!='v056':
            rgb=blend(reference_rgb,rgb,scope)
            n=reference_n if method=='B' else blend(reference_n,n,scope)
            outside=scope==0
            assert np.array_equal(rgb[outside],reference_rgb[outside]) and np.array_equal(n[outside],reference_n[outside])
            if method=='B':assert np.array_equal(n,reference_n)
        im=shade(section,ctx,rgb,n);draw=ImageDraw.Draw(im);draw.rectangle((0,0,WIDTH,68),fill=(22,25,29))
        draw.text((16,9),METHODS[method]['title']+' | '+view['title'],font=font(24),fill='white')
        draw.text((16,39),'Source material study - identical terrain/light/camera - not an MX Bikes capture',font=font(18),fill=(199,211,219))
        path=OUT/(method+'_'+view['id']+'.jpg');im.save(path,quality=96,subsampling=0)
        rows.append(dict(method=method,view=view['id'],file=path.name,sha256=sha(path),eye_xzy_m=ctx['eye'].tolist(),target_xzy_m=ctx['target'].tolist(),
            pixels_in_full_strength_section=int(valid_scope.sum()),changes_outside_section=0,
            mean_abs_colour_difference_to_v056=float(np.mean(np.abs(rgb[valid_scope]-reference_rgb[valid_scope]))),
            mean_abs_normal_difference_to_v056=float(np.mean(np.abs(n[valid_scope,:3]-reference_n[valid_scope,:3])))))
        print('Rendered',method,view['id'],flush=True)
    del ctx,candidates;gc.collect()
    return rows


def sheets():
    # Four complete, matched views per method, with v056 beside each one.
    for method in ['A','B','C']:
        sheet=Image.new('RGB',(WIDTH*2,HEIGHT*len(VIEWS)+115),(22,25,29));draw=ImageDraw.Draw(sheet)
        draw.text((24,15),METHODS[method]['title'],font=font(32),fill='white')
        draw.text((24,57),'LEFT: v056 reference    RIGHT: trial '+method+'    |    Same 210m section, cameras, lighting and geometry',font=font(25),fill=(209,219,225))
        for i,view in enumerate(VIEWS):
            sheet.paste(Image.open(OUT/('v056_'+view['id']+'.jpg')),(0,115+i*HEIGHT))
            sheet.paste(Image.open(OUT/(method+'_'+view['id']+'.jpg')),(WIDTH,115+i*HEIGHT))
        sheet.save(OUT/('Orlando_Dirt_Method_'+method+'_4Views.jpg'),quality=95,subsampling=0)
    for view in VIEWS:
        sheet=Image.new('RGB',(WIDTH*2,HEIGHT*2),(22,25,29))
        for i,method in enumerate(['v056','A','B','C']):sheet.paste(Image.open(OUT/(method+'_'+view['id']+'.jpg')),((i%2)*WIDTH,(i//2)*HEIGHT))
        sheet.save(OUT/('All_Methods_'+view['id']+'.jpg'),quality=95,subsampling=0)


def main():
    section=Section();materials=Materials();rows=[]
    views=VIEWS if len(sys.argv)==1 else [v for v in VIEWS if v['id']==sys.argv[1]]
    for view in views:
        cached=OUT/('render_rows_'+view['id']+'.json')
        if len(views)>1 and cached.exists():
            prior=json.loads(cached.read_text())
            if len(prior)==4 and all((OUT/r['file']).exists() and sha(OUT/r['file'])==r['sha256'] for r in prior):
                rows.extend(prior);print('Reused checked matched views',view['id'],flush=True);continue
        result=render_view(section,materials,view);rows.extend(result);save(cached,result)
    save(OUT/('render_rows_'+('all' if len(views)>1 else views[0]['id'])+'.json'),rows)
    if len(views)==len(VIEWS):
        sheets();save(OUT/'manifest.json',dict(source_only=True,not_game_captures=True,corrected_perspective_texture_sampling=True,
            camera_pixel_dimensions=[WIDTH,HEIGHT],trilinear_mip_filtering=True,maximum_anisotropic_taps=MAX_AF,
            matching_camera_terrain_lighting=True,real_clod_displacement_added=False,macro_normal_depth_only=True,
            approved_scenery_preserved_sha256=sha(R/'V057_OUTPUT/scenery.fbx'),renders=rows))
    print('V058_DIRECT_TEXTURE_SOURCE_RENDERING_COMPLETE',flush=True)


if __name__=='__main__':main()
