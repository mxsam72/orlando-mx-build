"""Source-material and scope inspection; optional CPU terrain authoring render.

These are previews of the authored files, never MX Bikes screenshots.
"""
import json,math,re,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import map_coordinates
from v045_surface import R,BASE,O,M,SIZE,Section

def font(n):
    for name in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(name).exists():return ImageFont.truetype(name,n)
    return ImageFont.load_default()

def main():
    spec=json.loads((R/'V045_SOURCE/visual_spec.json').read_text());section=Section(spec)
    h=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
    shade=np.clip(110+h*7,35,215).astype(np.uint8)
    im=Image.fromarray(np.stack([shade,shade,shade],2)).resize((1200,1200))
    alpha=Image.open(M/'mask_v045_section.tga').getchannel('A').resize((1200,1200))
    overlay=Image.new('RGB',im.size,(205,122,44));im=Image.composite(overlay,im,alpha)
    d=ImageDraw.Draw(im)
    points=[(float(x/600*1200),float((600-z)/600*1200)) for x,z in section.p[::5]]
    d.line(points,fill=(220,230,239),width=2)
    for label,s in [('Finish tabletop',23),('Triple',151),('End of sample',193)]:
        q=section.q[np.argmin(abs(section.q[:,3]-s))];x=q[0]/600*1200;y=(600-q[1])/600*1200
        d.ellipse((x-5,y-5,x+5,y+5),fill='white');d.text((x+8,y-24 if label!='Triple' else y+7),label,font=font(18),fill='white',stroke_width=1,stroke_fill='black')
    d.rectangle((0,0,1200,75),fill=(22,25,29));d.text((24,15),'v045: finish tabletop to after triple — orange = dirt sample',font=font(25),fill='white')
    im.save(R/'BUILD/v045_scope_preview.png')
    sheet=Image.new('RGB',(1600,920),(22,25,29));d=ImageDraw.Draw(sheet)
    for i,(kind,title) in enumerate([('loose','Loose / disturbed soil — 4K, 2 m tile'),('packed','Packed riding line — 4K, 2 m tile')]):
        sheet.paste(Image.open(M/f'v045_{kind}.tga').resize((800,800),Image.Resampling.LANCZOS),(i*800,60))
        d.text((i*800+18,16),title,font=font(22),fill='white')
    d.text((18,879),'Actual authored colour maps; paired normal maps are included. This is not an in-game screenshot.',font=font(20),fill='white')
    sheet.save(R/'BUILD/v045_soil_material_preview.jpg',quality=94)
    print('Source scope and paired-material previews saved.',flush=True)
    if '--render' in sys.argv:render_terrain()

def layers(text):
    for match in re.finditer(r'(?m)^layer(\d+)\s*\{',text):
        start=match.start();i=match.end();depth=1
        while depth:
            if text[i]=='{':depth+=1
            elif text[i]=='}':depth-=1
            i+=1
        yield int(match[1]),text[start:i]

def source_file(name,override=True):
    for folder in ([M] if override else [])+[BASE/'materials',BASE]:
        if (folder/name).is_file():return folder/name
    if name.startswith('mask_') and (BASE/'masks'/name[5:]).is_file():return BASE/'masks'/name[5:]
    raise FileNotFoundError(name)

def composite(folder,box,n=2048):
    x=np.linspace(box[0],box[2],n,dtype=np.float32);z=np.linspace(box[3],box[1],n,dtype=np.float32)
    result=np.zeros((n,n,3),np.float32);normal=np.zeros_like(result);normal[:]=[128,128,255]
    for index,block in layers((folder/'compiled_track.hmf').read_text()):
        if index==0:continue
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1];rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        im=Image.open(source_file(name,folder==O)).convert('RGB')
        footprint=max(box[2]-box[0],box[3]-box[1])/n*rep/SIZE*im.width
        divisor=2**max(0,int(math.floor(math.log2(max(1,footprint)))))
        if divisor>1:im=im.resize((max(4,im.width//divisor),max(4,im.height//divisor)),Image.Resampling.BOX)
        tex=np.asarray(im);shd=source_file(name,folder==O).with_suffix('.shd');nt=None
        if not shd.exists() and (BASE/'materials'/Path(name).with_suffix('.shd')).exists():shd=BASE/'materials'/Path(name).with_suffix('.shd')
        if shd.exists():
            shader=shd.read_text();m=re.search(r'map\s*=\s*(\S+)',shader)
            if m:
                ni=Image.open(source_file(m[1],folder==O)).convert('RGB');nr=re.search(r'repetitions\s*=\s*([\d.]+)',shader)
                nrep=float(nr[1]) if nr else 1.;nrep=rep if nrep==0 else nrep
                foot=max(box[2]-box[0],box[3]-box[1])/n*nrep/SIZE*ni.width
                div=2**max(0,int(math.floor(math.log2(max(1,foot)))))
                if div>1:ni=ni.resize((max(4,ni.width//div),max(4,ni.height//div)),Image.Resampling.BOX)
                nt=np.asarray(ni)
        mm=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block);mask=np.asarray(Image.open(source_file(mm[1],folder==O)).getchannel('A')) if mm else None
        for y0 in range(0,n,64):
            xx,zz=np.meshgrid(x,z[y0:y0+64]);coords=[np.mod((SIZE-zz)/SIZE*rep,1)*tex.shape[0],np.mod(xx/SIZE*rep,1)*tex.shape[1]]
            color=np.stack([map_coordinates(tex[:,:,c],coords,order=1,mode='grid-wrap') for c in range(3)],2).astype(np.float32)
            a=np.ones(xx.shape,np.float32) if mask is None else map_coordinates(mask,[(SIZE-zz)/SIZE*(mask.shape[0]-1),xx/SIZE*(mask.shape[1]-1)],order=1,mode='nearest').astype(np.float32)/255
            result[y0:y0+len(zz)]=result[y0:y0+len(zz)]*(1-a[:,:,None])+color*a[:,:,None]
            if nt is not None:
                coords=[np.mod((SIZE-zz)/SIZE*nrep,1)*nt.shape[0],np.mod(xx/SIZE*nrep,1)*nt.shape[1]]
                color=np.stack([map_coordinates(nt[:,:,c],coords,order=1,mode='grid-wrap') for c in range(3)],2).astype(np.float32)
                normal[y0:y0+len(zz)]=normal[y0:y0+len(zz)]*(1-a[:,:,None])+color*a[:,:,None]
    vector=normal/127.5-1;vector/=np.maximum(np.linalg.norm(vector,axis=2)[:,:,None],1e-6)
    return Image.fromarray(np.uint8(np.rint(np.clip(result,0,255)))),Image.fromarray(np.uint8(np.rint(vector*127.5+127.5)))

def render_terrain():
    out=R/'BUILD/v045_authoring_renders';out.mkdir(exist_ok=True);box=(267.,166.,401.,246.)
    h=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
    gy,gx=np.gradient(h,SIZE/2048);gz=-gy
    def ground(x,z):return map_coordinates(h,[(600-z)/600*2048,x/600*2048],order=1,mode='nearest')
    def loc(x,z,above):return np.array([x,z,float(ground(np.array([x]),np.array([z]))[0])+above],np.float32)
    width,height=1600,900;sy,sx=np.mgrid[:height,:width].astype(np.float32)
    for version,folder in [('v044',BASE),('v045',O)]:
        print('Compositing actual source colour and normal layers:',version,flush=True)
        colour,normal=composite(folder,box);colour.save(out/(version+'_composite.png'))
        colors=np.asarray(colour);normals=np.asarray(normal)
        for label,eye,target in [('finish',loc(294,183,1.8),loc(329,186,.5)),('corner',loc(384,199,1.8),loc(373,218,.7)),('triple',loc(369,223,1.8),loc(331,222,.8))]:
            forward=target-eye;forward/=np.linalg.norm(forward)
            right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
            rx=(sx+.5-width/2)/(width/2)*math.tan(math.radians(52))
            ry=-(sy+.5-height/2)/(width/2)*math.tan(math.radians(52))
            rays=forward+rx[:,:,None]*right+ry[:,:,None]*up
            rays/=np.linalg.norm(rays,axis=2)[:,:,None];rays=rays.astype(np.float32)
            hit=np.zeros((height,width),bool);lo=np.zeros((height,width),np.float32);hi=np.zeros_like(lo)
            for dist in np.arange(.5,150.1,2.5):
                point=eye+rays*dist;below=point[:,:,2]<=ground(point[:,:,0],point[:,:,1]);new=below&~hit
                lo[new]=max(.0,dist-2.5);hi[new]=dist;hit|=new
            for _ in range(12):
                dist=(lo+hi)/2;point=eye+rays*dist[:,:,None]
                below=point[:,:,2]<=ground(point[:,:,0],point[:,:,1]);hi=np.where(below&hit,dist,hi);lo=np.where(~below&hit,dist,lo)
            point=eye+rays*hi[:,:,None];px=point[:,:,0];pz=point[:,:,1]
            coords=[(box[3]-pz)/(box[3]-box[1])*(colors.shape[0]-1),(px-box[0])/(box[2]-box[0])*(colors.shape[1]-1)]
            diffuse=np.stack([map_coordinates(colors[:,:,k],coords,order=1,mode='nearest') for k in range(3)],2).astype(np.float32)/255
            tn=np.stack([map_coordinates(normals[:,:,k],coords,order=1,mode='nearest') for k in range(3)],2).astype(np.float32)/127.5-1
            hc=[(600-pz)/600*2048,px/600*2048];dx=map_coordinates(gx,hc,order=1,mode='nearest');dz=map_coordinates(gz,hc,order=1,mode='nearest')
            base=np.stack([-dx,-dz,np.ones_like(dx)],2);base/=np.linalg.norm(base,axis=2)[:,:,None]
            tangent=np.stack([np.ones_like(dx),np.zeros_like(dx),dx],2);tangent/=np.linalg.norm(tangent,axis=2)[:,:,None];bitangent=np.cross(base,tangent)
            normal=tn[:,:,0,None]*tangent+tn[:,:,1,None]*bitangent+tn[:,:,2,None]*base;normal/=np.maximum(np.linalg.norm(normal,axis=2)[:,:,None],1e-5)
            light=np.array([2,-7,10],np.float32);light/=np.linalg.norm(light)
            intensity=.44+.65*np.maximum(0,np.sum(normal*light,axis=2))
            pixels=np.uint8(np.rint(np.clip(diffuse**2.2*intensity[:,:,None],0,1)**(1/2.2)*255))
            sky=np.empty_like(pixels);sky[:]=[157,194,226]
            pixels=np.where(hit[:,:,None],pixels,sky)
            im=Image.fromarray(pixels);d=ImageDraw.Draw(im);d.rectangle((0,0,width,42),fill=(22,25,29));d.text((16,10),version+' '+label+' — source terrain preview, not MX Bikes footage',font=font(21),fill='white');im.save(out/(version+'_'+label+'.jpg'),quality=95)
            print('CPU terrain source preview',version,label,flush=True)
    print('Actual terrain-source before/after authoring previews complete.',flush=True)

if __name__=='__main__':main()
