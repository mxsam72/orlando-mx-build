"""Source-only albedo previews using the actual v026 material inputs.

These omit native normal response, object rendering, engine shadows and weather.
They are not MX Bikes screenshots or a guarantee of the final game appearance.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from render_v025_previews import scene, sample, layers
R=Path(__file__).resolve().parents[1];O=R/'V026_OUTPUT';D=R/'DOCUMENTATION/v026_previews';SIZE=600.;CACHE={}
def source_image(name,ver,mask=False):
    key=(name,ver,mask)
    if key not in CACHE:
        folder=R/('V025_OUTPUT' if ver=='v025' else 'V026_OUTPUT')/'materials';p=folder/name
        if not p.exists():
            p=R/'V025_AUDIT'/('masks' if mask else 'textures')/Path(name.removeprefix('mask_') if mask else name).with_suffix('.png').name
        if not p.exists() and mask:p=R/'V024_OUTPUT/masks'/name.removeprefix('mask_')
        im=Image.open(p)
        if mask:im=im.getchannel('A') if im.mode=='RGBA' else im.convert('L')
        else:im=im.convert('RGB')
        CACHE[key]=np.asarray(im,np.float32)/255
    return CACHE[key]
def albedo(x,z,ver):
    folder=R/('V025_OUTPUT' if ver=='v025' else 'V026_OUTPUT')/'materials';result=np.zeros((len(x),3),np.float32)
    for name,reps,mask in layers((folder/'track.hmf').read_text()):
        ar=source_image(name,ver)
        if reps>1:
            k=('mip',name,ver)
            if k not in CACHE:CACHE[k]=np.asarray(Image.fromarray(np.uint8(ar*255)).resize((512,512),Image.Resampling.LANCZOS),np.float32)/255
            ar=CACHE[k]
        rgb=sample(ar,x,z,reps);alpha=np.ones(len(x)) if not mask else sample(source_image(mask,ver,True),x,z,1)
        result=result*(1-alpha[:,None])+rgb*alpha[:,None]
    return result
def main():
    D.mkdir(parents=True,exist_ok=True);manifest={'renderer':'source heightfield and diffuse materials; NOT MX Bikes','native_normals_objects_shadows_weather_omitted':True,'cameras':[]}
    for title,s,up in [('R10_takeoff',738,False),('R10_landing_T09',790,True),('corner_T09',832,True),('control_R17',1260,False)]:
        frames=[]
        for ver in ['v025','v026']:
            folder=R/('V024_OUTPUT' if ver=='v025' else 'V026_OUTPUT');H=np.fromfile(folder/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18;q=np.load(folder/'route.npz')['q']
            # The control view uses the same fixed world position after native
            # distance remapping. The changed sector follows its own new route.
            station=s
            if ver=='v026' and s>900:
                d=np.load(O/'route.npz');old=np.load(R/'V024_OUTPUT/route.npz')['q'];station=float(np.interp(s,old[:,3],d['old_to_new_station']))
            (w,h),directions,idx,x,z,shade=scene(H,q,station,up)
            ar=np.array([.62,.76,.85])[None,:]+np.clip(directions[:,1],0,1)[:,None]*[-.11,-.07,-.01];ar[idx]=albedo(x,z,ver)*shade[:,None]
            im=Image.fromarray(np.uint8(np.rint(np.clip(ar.reshape(h,w,3),0,1)*255)));draw=ImageDraw.Draw(im);draw.rectangle((0,0,w,40),fill=(20,24,25));draw.text((12,10),ver+' | '+title+' | SOURCE PREVIEW - NOT IN GAME',fill='white');im.save(D/(title+'_'+ver+'.png'));frames.append(im)
        pair=Image.new('RGB',(w*2,h));pair.paste(frames[0],(0,0));pair.paste(frames[1],(w,0));pair.save(D/(title+'_comparison.png'));manifest['cameras'].append(dict(name=title,station_m=s,elevated=up))
        print('Source preview',title,flush=True)
    (D/'preview_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
