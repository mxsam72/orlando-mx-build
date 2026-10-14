"""Matched source views sampling actual HMF textures at rider-height footprints.

The CPU renderer includes accepted terrain and all HMF material layers. It
samples finer mips near the camera, instead of flattening an entire view into
one low-resolution world composite. These are source previews, not game shots.
"""
import json,math,re
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import map_coordinates
from v053_surface import R,BASE,DIRT,PREVIOUS,O,M,SIZE,Circuit,sha,save
from v049_previews import layers,font

OUT=R/'BUILD/v053_review'
def source(name,version):
    for folder in [M if version=='v053' else PREVIOUS/'materials',DIRT/'materials',BASE/'materials',BASE]:
        if (folder/name).is_file():return folder/name
    p=BASE/'masks'/name.removeprefix('mask_')
    if p.is_file():return p
    raise FileNotFoundError(name)

def location(sample,s,l=0.,above=1.7):
    s=s%sample.length
    x=np.interp(s,sample.q[:,3],sample.q[:,0]); z=np.interp(s,sample.q[:,3],sample.q[:,1])
    tx=np.interp(s,sample.q[:,3],sample.v[:,0]); tz=np.interp(s,sample.q[:,3],sample.v[:,1])
    x-=l*tz; z+=l*tx
    return np.array([x,z,float(sample.ground(np.array([x]),np.array([z]))[0])+above],np.float32)

def hit_terrain(sample,eye,target,width=1200,height=750):
    sy,sx=np.mgrid[:height,:width].astype(np.float32)
    forward=target-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    rx=(sx+.5-width/2)/(width/2)*math.tan(math.radians(42));ry=-(sy+.5-height/2)/(width/2)*math.tan(math.radians(42))
    rays=forward+rx[:,:,None]*right+ry[:,:,None]*up;rays/=np.linalg.norm(rays,axis=2)[:,:,None];rays=rays.astype(np.float32)
    hit=np.zeros((height,width),bool);lo=np.zeros((height,width),np.float32);hi=np.zeros_like(lo)
    for dist in np.arange(.2,110.1,2.):
        point=eye+rays*dist;below=point[:,:,2]<=sample.ground(point[:,:,0],point[:,:,1]);new=below&~hit
        lo[new]=max(0,dist-2);hi[new]=dist;hit|=new
    for _ in range(11):
        dist=(lo+hi)/2;point=eye+rays*dist[:,:,None];below=point[:,:,2]<=sample.ground(point[:,:,0],point[:,:,1])
        hi=np.where(below&hit,dist,hi);lo=np.where(~below&hit,dist,lo)
    point=eye+rays*hi[:,:,None]
    dx=np.linalg.norm(np.gradient(point[:,:,:2],axis=1),axis=2)
    dy=np.linalg.norm(np.gradient(point[:,:,:2],axis=0),axis=2)
    footprint=np.clip(np.maximum(dx,dy),.001,6.)
    return point,hit,footprint

def tiled(path,rep,x,z,footprint,channels=3):
    im=Image.open(path).convert('RGBA' if channels==4 else 'RGB')
    foot=np.maximum(1.,footprint*rep/SIZE*im.width)
    levels=np.clip(np.floor(np.log2(foot)).astype(np.int16),0,int(math.log2(im.width))-2)
    out=np.empty((*x.shape,channels),np.float32)
    for level in np.unique(levels):
        sel=levels==level; size=(max(4,im.width//2**int(level)),max(4,im.height//2**int(level)))
        if channels==4:
            # Normal alpha is specular intensity, not transparency.
            rgb=im.convert('RGB').resize(size,Image.Resampling.BOX); alpha=im.getchannel('A').resize(size,Image.Resampling.BOX)
            mip=rgb.convert('RGBA');mip.putalpha(alpha)
        else:mip=im.resize(size,Image.Resampling.BOX)
        tex=np.asarray(mip)
        coords=[np.mod((SIZE-z[sel])/SIZE*rep,1)*tex.shape[0]-.5,np.mod(x[sel]/SIZE*rep,1)*tex.shape[1]-.5]
        for k in range(channels):out[:,:,k][sel]=map_coordinates(tex[:,:,k],coords,order=1,mode='grid-wrap')
    return out

def composite(version,point,footprint):
    x=point[:,:,0];z=point[:,:,1];rgb=np.zeros((*x.shape,3),np.float32)
    normal=np.empty((*x.shape,4),np.float32);normal[:]=[128,128,255,0]
    root=O if version=='v053' else PREVIOUS
    for index,block in layers((root/'compiled_track.hmf').read_text()):
        if index==0:continue
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1];rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        mm=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        if mm:
            mask=np.asarray(Image.open(source(mm[1],version)).getchannel('A'))
            a=map_coordinates(mask,[(SIZE-z)/SIZE*mask.shape[0]-.5,x/SIZE*mask.shape[1]-.5],order=1,mode='nearest').astype(np.float32)/255
        else:a=np.ones(x.shape,np.float32)
        if not np.any(a):continue
        texture=source(name,version); color=tiled(texture,rep,x,z,footprint)
        rgb=rgb*(1-a[:,:,None])+color*a[:,:,None]
        shader=texture.with_suffix('.shd')
        if not shader.is_file():shader=BASE/'materials'/shader.name
        if shader.is_file():
            sh=shader.read_text();bump=re.search(r'bump\s*\{([^{}]+)\}',sh)
            if bump:
                nname=re.search(r'map\s*=\s*(\S+)',bump[1])[1]
                nr=re.search(r'repetitions\s*=\s*([\d.]+)',bump[1]);nrep=(float(nr[1]) if nr else rep) or rep
                n=tiled(source(nname,version),nrep,x,z,footprint,channels=4)
                normal=normal*(1-a[:,:,None])+n*a[:,:,None]
        print('Preview',version,'layer',index,name,flush=True)
    return rgb,normal

def render(version,label,sample,eye,target,geometry):
    point,hit,footprint=geometry;rgb,tn=composite(version,point,footprint)
    x=point[:,:,0];z=point[:,:,1];hx,hz=sample.slope(x,z)
    base=np.stack([-hx,-hz,np.ones_like(hx)],2);base/=np.linalg.norm(base,axis=2)[:,:,None]
    tangent=np.stack([np.ones_like(hx),np.zeros_like(hx),hx],2);tangent/=np.linalg.norm(tangent,axis=2)[:,:,None];bitangent=np.cross(base,tangent)
    t=tn[:,:,:3]/127.5-1;normal=t[:,:,0,None]*tangent+t[:,:,1,None]*bitangent+t[:,:,2,None]*base
    normal/=np.maximum(np.linalg.norm(normal,axis=2)[:,:,None],1e-6)
    light=np.array([2,-7,10],np.float32);light/=np.linalg.norm(light)
    intensity=.38+.70*np.maximum(0,np.sum(normal*light,axis=2))
    view=eye-point;view/=np.maximum(np.linalg.norm(view,axis=2)[:,:,None],1e-6)
    halfway=view+light;halfway/=np.maximum(np.linalg.norm(halfway,axis=2)[:,:,None],1e-6)
    highlight=tn[:,:,3]/255*np.maximum(0,np.sum(normal*halfway,axis=2))**8*.45
    pixels=np.uint8(np.rint(np.clip((rgb/255)**2.2*intensity[:,:,None]+highlight[:,:,None],0,1)**(1/2.2)*255))
    pixels[~hit]=[157,194,226]
    im=Image.fromarray(pixels);draw=ImageDraw.Draw(im);draw.rectangle((0,0,im.width,44),fill=(22,25,29))
    draw.text((15,11),f'{version} {label}: actual-source preview; not game footage',font=font(20),fill='white')
    out=OUT/f'{version}_{label}.jpg';im.save(out,quality=95)
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=True);sample=Circuit()
    # Choose the longest straight sample from actual route curvature, not a
    # guessed jump label. Other cameras use pinned accepted jump stations.
    straight=np.flatnonzero(sample.curvature<.006)
    groups=np.split(straight,np.where(np.diff(straight)>1)[0]+1);groups=[g for g in groups if len(g)>20]
    g=max(groups,key=len);s0=float(sample.q[g[len(g)//4],3])
    corners=np.flatnonzero((sample.curvature>.028)&(sample.q[:,3]>80)&(sample.q[:,3]<sample.length-80))
    cs=float(sample.q[corners[len(corners)//3],3])
    shots=[('straight',s0,s0+22,0.),('jump_face',740.,767.,0.),('corner',cs-8,cs+13,-.3),('landing',802.,823.,.8)]
    rows=[]
    for label,a,b,l in shots:
        eye=location(sample,a,l,1.7);target=location(sample,b,0.,.9)
        geometry=hit_terrain(sample,eye,target)
        frames=[]
        for version in ['v052','v053']:
            p=render(version,label,sample,eye,target,geometry);frames.append(Image.open(p).copy())
            rows.append(dict(version=version,view=label,file=p.name,sha256=sha(p),camera_world_xzh=eye.tolist(),target_world_xzh=target.tolist(),camera_station_m=a))
        sheet=Image.new('RGB',(frames[0].width*2,frames[0].height),(22,25,29));sheet.paste(frames[0],(0,0));sheet.paste(frames[1],(frames[0].width,0))
        sheet.save(OUT/f'comparison_{label}.jpg',quality=95)
        print('Matched source views ready:',label,flush=True)
    save(OUT/'manifest.json',dict(source_only=True,game_captures=False,actual_hmf_layers_sampled=True,
        per_pixel_ground_footprint_mips=True,identical_cameras_and_lighting=True,scenery_omitted_in_both=True,
        terrain_sha256=sha(BASE/'terrain.raw'),renders=rows,lighting_model='Approximate diffuse plus alpha-based specular stress preview; game testing remains required'))
if __name__=='__main__':main()
