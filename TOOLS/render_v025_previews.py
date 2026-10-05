"""Matched source material previews; these are explicitly not MX Bikes screenshots.

This small heightfield raycaster uses the same v024 terrain and camera for both
versions. Objects, engine shadows and engine-specific shader response are omitted.
"""
from pathlib import Path
import json, re, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates

R=Path(__file__).resolve().parents[1];A=R/'V025_AUDIT';M=R/'V025_OUTPUT/materials'
D=R/'DOCUMENTATION/v025_previews';SIZE=600.
CACHE={}

def layers(text):
    out=[]
    for m in re.finditer(r'\blayer(\d+)\s*\{',text):
        start=m.end();depth=1;end=start
        while depth:
            if text[end]=='{':depth+=1
            elif text[end]=='}':depth-=1
            end+=1
        body=text[start:end-1]
        get=lambda key:re.search(r'(?m)^\s*'+key+r'\s*=\s*(\S+)',body)
        out.append((get('map')[1],float(get('repetitions')[1]),get('mask')[1] if get('mask') else None))
    return out

def image_for(name,ver,mask=False):
    key=(name,ver,mask)
    if key not in CACHE:
        if ver=='v025' and (M/name).exists():p=M/name
        elif mask:p=A/'masks'/Path(name.removeprefix('mask_')).with_suffix('.png').name
        else:p=A/'textures'/Path(name).with_suffix('.png').name
        im=Image.open(p)
        if mask:im=im.getchannel('A') if im.mode=='RGBA' else im.convert('L')
        else:im=im.convert('RGB')
        CACHE[key]=np.asarray(im,np.float32)/255
    return CACHE[key]

def sample(ar,x,z,reps):
    h,w=ar.shape[:2]
    u=x/SIZE*reps*(w-1);v=(SIZE-z)/SIZE*reps*(h-1)
    if reps>1:u%=w;v%=h
    coords=[v,u]
    if ar.ndim==2:return map_coordinates(ar,coords,order=1,mode='nearest')
    return np.column_stack([map_coordinates(ar[...,i],coords,order=1,mode='nearest') for i in range(3)])

def albedo(x,z,ver):
    text=(A/'track.hmf' if ver=='v024' else M/'track.hmf').read_text()
    result=np.zeros((len(x),3),np.float32)
    for name,reps,mask in layers(text):
        ar=image_for(name,ver)
        # Matching low-pass filtering avoids fine-tile aliasing in broad previews.
        if reps>1:
            k=('mip',name,ver)
            if k not in CACHE:
                CACHE[k]=np.asarray(Image.fromarray(np.uint8(ar*255)).resize((512,512),Image.Resampling.LANCZOS),np.float32)/255
            ar=CACHE[k]
        rgb=sample(ar,x,z,reps)
        alpha=np.ones(len(x),np.float32) if not mask else sample(image_for(mask,ver,True),x,z,1)
        result=result*(1-alpha[:,None])+rgb*alpha[:,None]
    mask='mask_v024_pit_roads.tga'
    if (A/'masks/v024_pit_roads.png').exists():
        rgb=sample(image_for('v024_pit_gravel.tga',ver),x,z,95)
        alpha=sample(image_for(mask,ver,True),x,z,1)
        result=result*(1-alpha[:,None])+rgb*alpha[:,None]
    return result

def scene(H,q,station,elevated=False):
    i=np.argmin(abs(q[:,3]-station));position=q[i,:2]
    look=q[np.argmin(abs(q[:,3]-(station+40)))][:2]
    def terrain(x,z):
        out=map_coordinates(H,[(SIZE-np.atleast_1d(z))/SIZE*2048,np.atleast_1d(x)/SIZE*2048],order=1,mode='nearest')
        return out.item() if np.isscalar(x) else out
    if elevated:
        cam=np.array([position[0]-18,float(terrain(position[0],position[1]))+20,position[1]-22])
        target=np.array([look[0],float(terrain(look[0],look[1]))+.3,look[1]])
    else:
        cam=np.array([position[0],float(terrain(position[0],position[1]))+2.1,position[1]])
        target=np.array([look[0],float(terrain(look[0],look[1]))+1.2,look[1]])
    f=target-cam;f/=np.linalg.norm(f);right=np.cross(f,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,f)
    width,height=960,600
    yy,xx=np.meshgrid(np.linspace(1,-1,height),np.linspace(-1,1,width),indexing='ij')
    d=f+xx[...,None]*right*math.tan(math.radians(63)/2)+yy[...,None]*up*math.tan(math.radians(63)/2)*height/width
    d=d.reshape(-1,3);d/=np.linalg.norm(d,axis=1)[:,None]
    t=np.full(len(d),.25);hit=np.zeros(len(d),bool);active=np.ones(len(d),bool)
    last=t.copy()
    for it in range(450):
        idx=np.flatnonzero(active)
        if not len(idx):break
        pos=cam+d[idx]*t[idx,None]
        ground=terrain(pos[:,0],pos[:,2]);delta=pos[:,1]-ground
        h=delta<=0
        if h.any():
            ii=idx[h];a=last[ii].copy();b=t[ii].copy()
            for _ in range(7):
                middle=(a+b)/2;pp=cam+d[ii]*middle[:,None]
                above=pp[:,1]>terrain(pp[:,0],pp[:,2]);a=np.where(above,middle,a);b=np.where(above,b,middle)
            t[ii]=(a+b)/2;hit[ii]=True;active[ii]=False
        ii=idx[~h];pos=pos[~h];delta=delta[~h]
        outside=(pos[:,0]<0)|(pos[:,0]>600)|(pos[:,2]<0)|(pos[:,2]>600)|(t[ii]>240)
        active[ii[outside]]=False
        ii=ii[~outside];delta=delta[~outside];last[ii]=t[ii]
        t[ii]+=np.clip(delta*.38,.10,2.4)
    pp=cam+d*t[:,None]
    idx=np.flatnonzero(hit);x=pp[idx,0];z=pp[idx,2]
    gy,gx=np.gradient(H,600/2048)
    nx=-map_coordinates(gx,[(600-z)/600*2048,x/600*2048],order=1)
    nz=map_coordinates(gy,[(600-z)/600*2048,x/600*2048],order=1)
    normal=np.column_stack([nx,np.ones(len(nx)),nz]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    sun=np.array([2.,10.,-7.]);sun/=np.linalg.norm(sun)
    shade=.56+.44*np.clip(normal@sun,0,1)
    return (width,height),d,idx,x,z,shade

def main():
    D.mkdir(parents=True,exist_ok=True)
    H=np.fromfile(A/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
    q=np.load(A/'route.npz')['q']
    shots=[('R10_takeoff',730,False),('T09_berm',798,True),('R07_anthill',532,False),('R17_rollers',1240,True)]
    manifest={'renderer':'Matched software heightfield/albedo previews; not MX Bikes',
        'same_v024_geometry':True,'objects_omitted':True,'engine_shader_and_shadows_omitted':True,
        'baseline_diffuse_inputs':'1024px inspection copies from exact v024 audit',
        'cameras':[]}
    for title,s,elevated in shots:
        print('Source preview',title,flush=True)
        (w,h),d,idx,x,z,shade=scene(H,q,s,elevated)
        frames=[]
        for ver in ['v024','v025']:
            sky=np.array([.62,.76,.85])[None,:]+np.clip(d[:,1],0,1)[:,None]*[-.11,-.07,-.01]
            ar=sky.copy();ar[idx]=albedo(x,z,ver)*shade[:,None]
            im=Image.fromarray(np.uint8(np.rint(np.clip(ar.reshape(h,w,3),0,1)*255)))
            draw=ImageDraw.Draw(im);draw.rectangle((0,0,w,40),fill=(20,24,25))
            draw.text((12,9),ver+' | '+title+' | source material preview - NOT IN-GAME',fill='white')
            im.save(D/(title+'_'+ver+'.png'));frames.append(im)
        paired=Image.new('RGB',(w*2,h));paired.paste(frames[0],(0,0));paired.paste(frames[1],(w,0))
        paired.save(D/(title+'_comparison.png'))
        manifest['cameras'].append(dict(name=title,station_m=s,elevated=elevated))
    (D/'preview_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
