"""Matched before/after previews of actual HMF layers and accepted terrain.

CPU source rendering, not MX Bikes screenshots. No invented displacement or
scenery is added; the sole difference is the scoped dirt material sample.
"""
import json,math,re
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import map_coordinates
from v048_surface import R,BASE,DIRT,O,M,SIZE,Sample,sha,save

OUT=R/'BUILD/v048_authoring_renders'
BOX=(283.,162.,368.,209.)
def font(n):
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(path).exists():return ImageFont.truetype(path,n)
    return ImageFont.load_default()
def layers(text):
    for m in re.finditer(r'(?m)^layer(\d+)\s*\{',text):
        i=m.end();depth=1
        while depth:
            if text[i]=='{':depth+=1
            elif text[i]=='}':depth-=1
            i+=1
        yield int(m[1]),text[m.start():i]
def source(name,version):
    folders=([M] if version=='v048' else [])+[DIRT/'materials',BASE/'materials',BASE]
    for folder in folders:
        if (folder/name).is_file():return folder/name
    if name.startswith('mask_') and (BASE/'masks'/name[5:]).is_file():return BASE/'masks'/name[5:]
    raise FileNotFoundError(name)
def mip(path,rep,n):
    im=Image.open(path).convert('RGB')
    foot=max(BOX[2]-BOX[0],BOX[3]-BOX[1])/n*rep/SIZE*im.width
    div=2**max(0,int(math.floor(math.log2(max(1.,foot)))))
    if div>1:im=im.resize((max(4,im.width//div),max(4,im.height//div)),Image.Resampling.BOX)
    return np.asarray(im)
def composite(version,n=2304):
    x=np.linspace(BOX[0],BOX[2],n,dtype=np.float32);z=np.linspace(BOX[3],BOX[1],n,dtype=np.float32)
    rgb=np.zeros((n,n,3),np.float32);normal=np.zeros_like(rgb);normal[:]=[128,128,255]
    for index,block in layers(((O if version=='v048' else DIRT)/'compiled_track.hmf').read_text()):
        if index==0:continue
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1];rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        tex=mip(source(name,version),rep,n);shader=source(name,version).with_suffix('.shd')
        if not shader.exists():shader=BASE/'materials'/Path(name).with_suffix('.shd')
        nt=None;nrep=rep
        if shader.exists():
            sh=shader.read_text();m=re.search(r'map\s*=\s*(\S+)',sh)
            if m:
                r=re.search(r'repetitions\s*=\s*([\d.]+)',sh);nrep=float(r[1]) if r else rep;nrep=nrep or rep
                nt=mip(source(m[1],version),nrep,n)
        mm=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        mask=np.asarray(Image.open(source(mm[1],version)).getchannel('A')) if mm else None
        for row in range(0,n,64):
            xx,zz=np.meshgrid(x,z[row:row+64]);coords=[np.mod((SIZE-zz)/SIZE*rep,1)*tex.shape[0]-.5,np.mod(xx/SIZE*rep,1)*tex.shape[1]-.5]
            color=np.stack([map_coordinates(tex[:,:,k],coords,order=1,mode='grid-wrap') for k in range(3)],2).astype(np.float32)
            a=np.ones(xx.shape,np.float32) if mask is None else map_coordinates(mask,[(SIZE-zz)/SIZE*mask.shape[0]-.5,xx/SIZE*mask.shape[1]-.5],order=1,mode='nearest').astype(np.float32)/255
            rgb[row:row+len(zz)]=rgb[row:row+len(zz)]*(1-a[:,:,None])+color*a[:,:,None]
            if nt is not None:
                coords=[np.mod((SIZE-zz)/SIZE*nrep,1)*nt.shape[0]-.5,np.mod(xx/SIZE*nrep,1)*nt.shape[1]-.5]
                color=np.stack([map_coordinates(nt[:,:,k],coords,order=1,mode='grid-wrap') for k in range(3)],2).astype(np.float32)
                normal[row:row+len(zz)]=normal[row:row+len(zz)]*(1-a[:,:,None])+color*a[:,:,None]
        print('Composited',version,'native source layer',index,name,flush=True)
    vector=normal/127.5-1;vector/=np.maximum(np.linalg.norm(vector,axis=2)[:,:,None],1e-6)
    return np.uint8(np.rint(np.clip(rgb,0,255))),np.uint8(np.rint(vector*127.5+127.5))

def render(version,label,colors,normals,sample,eye,target,width=1440,height=900):
    sy,sx=np.mgrid[:height,:width].astype(np.float32)
    eye=np.asarray(eye,np.float32);target=np.asarray(target,np.float32)
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
    point=eye+rays*hi[:,:,None];px=point[:,:,0];pz=point[:,:,1]
    coords=[(BOX[3]-pz)/(BOX[3]-BOX[1])*(colors.shape[0]-1),(px-BOX[0])/(BOX[2]-BOX[0])*(colors.shape[1]-1)]
    diffuse=np.stack([map_coordinates(colors[:,:,k],coords,order=1,mode='nearest') for k in range(3)],2).astype(np.float32)/255
    tn=np.stack([map_coordinates(normals[:,:,k],coords,order=1,mode='nearest') for k in range(3)],2).astype(np.float32)/127.5-1
    hx,hz=sample.slope(px,pz);base=np.stack([-hx,-hz,np.ones_like(hx)],2);base/=np.linalg.norm(base,axis=2)[:,:,None]
    tangent=np.stack([np.ones_like(hx),np.zeros_like(hx),hx],2);tangent/=np.linalg.norm(tangent,axis=2)[:,:,None];bitangent=np.cross(base,tangent)
    normal=tn[:,:,0,None]*tangent+tn[:,:,1,None]*bitangent+tn[:,:,2,None]*base;normal/=np.maximum(np.linalg.norm(normal,axis=2)[:,:,None],1e-6)
    light=np.array([2,-7,10],np.float32);light/=np.linalg.norm(light)
    intensity=.38+.70*np.maximum(0,np.sum(normal*light,axis=2))
    # Identical neutral daylight in both versions. No colour grading or fake shadows.
    pixels=np.uint8(np.rint(np.clip(diffuse**2.2*intensity[:,:,None],0,1)**(1/2.2)*255))
    valid=hit&(px>=BOX[0])&(px<=BOX[2])&(pz>=BOX[1])&(pz<=BOX[3])
    sky=np.empty_like(pixels);sky[:]=[157,194,226];pixels=np.where(valid[:,:,None],pixels,sky)
    im=Image.fromarray(pixels);d=ImageDraw.Draw(im);d.rectangle((0,0,width,42),fill=(22,25,29))
    d.text((15,10),version+' '+label+' — actual terrain/material source preview; not game footage',font=font(20),fill='white')
    p=OUT/(version+'_'+label+'.jpg');im.save(p,quality=95)
    print('Rendered',version,label,flush=True);return p

def main():
    OUT.mkdir(parents=True,exist_ok=True);sample=Sample();renders=[]
    def loc(x,z,above):return [x,z,float(sample.ground(np.array([x]),np.array([z]))[0])+above]
    shots=[('takeoff',loc(295,184,1.8),loc(317,184.7,1.2)),('banks',loc(318,164,6.),loc(326,184.5,1.)),('landing',loc(355,189,1.8),loc(334,184.5,1.))]
    before={name:sha(O/'materials'/name) for name in ['v044_route_detail.tga','v044_route_detail_n.tga']}
    for version in ['v047','v048']:
        color,normal=composite(version)
        Image.fromarray(color).save(OUT/(version+'_composite.jpg'),quality=94);Image.fromarray(normal).save(OUT/(version+'_normals.png'))
        for label,eye,target in shots:
            p=render(version,label,color,normal,sample,eye,target);renders.append(dict(version=version,view=label,file=p.name,sha256=sha(p),camera_xyz=eye,target_xyz=target))
    for label,_,_ in shots:
        a=Image.open(OUT/('v047_'+label+'.jpg'));b=Image.open(OUT/('v048_'+label+'.jpg'))
        sheet=Image.new('RGB',(a.width*2,a.height),(22,25,29));sheet.paste(a,(0,0));sheet.paste(b,(a.width,0));sheet.save(OUT/('comparison_'+label+'.jpg'),quality=95)
    assert all(sha(O/'materials'/name)==digest for name,digest in before.items())
    save(OUT/'manifest.json',dict(renders=renders,source_only=True,game_captures=False,source_files_unchanged=True,identical_camera_and_daylight=True,scenery_omitted_in_both=True,terrain_sha256=sha(BASE/'terrain.raw'),box_world_xz_m=list(BOX)))

if __name__=='__main__':main()
