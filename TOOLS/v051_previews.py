"""Source QA previews of full-track soil and actual photographic grass meshes.

CPU renders are clearly labelled as source views, not game screenshots.
"""
import json,math
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
from v051_surface import R,BASE,DIRT,O,M,Circuit,sha,save
import v049_previews as terrain
from v027_scenery import parse,geometry_records,vertices,child
from rebind_scenery import array
from v051_scenery import F,TEXTURE,TINT
from v051_coverage import TRIALS,baseline_mask

OUT=R/'BUILD/v051_review'
def source(name,version):
    if version=='v051_control' and name in {t['mask'] for t in TRIALS}:return baseline_mask(name)
    for folder in ([M] if version in ['v051','v051_control'] else [R/'V049_OUTPUT/materials'] if version=='v049' else [])+[DIRT/'materials',BASE/'materials',BASE]:
        if (folder/name).is_file():return folder/name
    if name.startswith('mask_') and (BASE/'masks'/name[5:]).is_file():return BASE/'masks'/name[5:]
    raise FileNotFoundError(name)
def grass_views(sample):
    nodes,_=parse((O/'scenery.fbx').read_bytes());rec=geometry_records(nodes)
    qa=json.loads((O/'v051_scenery_validation.json').read_text());anchor=np.array(next(p['anchor_xz_m'] for p in qa['replaced_scrub'] if p['original']=='scrub_205'))
    pieces=[]
    for name,(g,mid) in rec.items():
        if not name.startswith('SKIDS_v051_grass'):continue
        v=vertices(g);idx=array(child(g,b'PolygonVertexIndex')).reshape(-1,3).copy();idx[idx<0]=-idx[idx<0]-1
        uvnode=child(g,b'LayerElementUV');uv=array(child(uvnode,b'UV')).reshape(-1,2)
        uv=uv[array(child(uvnode,b'UVIndex'))].reshape(-1,3,2)
        selected=np.max(np.linalg.norm(v[idx][:,:,[0,2]]-anchor,axis=2),axis=1)<2.8
        if np.any(selected):pieces.append((v[idx[selected]],uv[selected]))
    tris=np.concatenate([p[0] for p in pieces]);uvs=np.concatenate([p[1] for p in pieces]);tex=np.asarray(Image.open(F/TEXTURE).convert('RGBA'))
    target=np.array([anchor[0],float(sample.ground(anchor[:1],anchor[1:])[0])+.23,anchor[1]])
    for k,angle in enumerate([.2,2.4,4.6]):
        eye=target+np.array([math.cos(angle)*3.0,.83,math.sin(angle)*3.0]);forward=target-eye;forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
        points=tris-eye;z=points@forward;px=points@right;py=points@up;w,h=1200,720;f=w/(2*math.tan(math.radians(51)/2))
        screen=np.stack([w/2+px/z*f,h/2-py/z*f],2);canvas=np.empty((h,w,3),np.uint8);canvas[:]=[139,117,81];depth=np.full((h,w),np.inf)
        for t,uv,zz in zip(screen,uvs,z):
            if np.any(zz<=0):continue
            x0=max(0,int(np.floor(t[:,0].min())));x1=min(w-1,int(np.ceil(t[:,0].max())));y0=max(0,int(np.floor(t[:,1].min())));y1=min(h-1,int(np.ceil(t[:,1].max())))
            if x1<x0 or y1<y0:continue
            den=(t[1,1]-t[2,1])*(t[0,0]-t[2,0])+(t[2,0]-t[1,0])*(t[0,1]-t[2,1])
            if abs(den)<1e-6:continue
            xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            a=((t[1,1]-t[2,1])*(xx-t[2,0])+(t[2,0]-t[1,0])*(yy-t[2,1]))/den
            b=((t[2,1]-t[0,1])*(xx-t[2,0])+(t[0,0]-t[2,0])*(yy-t[2,1]))/den;c=1-a-b
            inv=a/zz[0]+b/zz[1]+c/zz[2];d=1/np.maximum(inv,1e-6)
            u=(a*uv[0,0]/zz[0]+b*uv[1,0]/zz[1]+c*uv[2,0]/zz[2])/inv
            v=(a*uv[0,1]/zz[0]+b*uv[1,1]/zz[1]+c*uv[2,1]/zz[2])/inv
            coords=[np.clip((1-v)*(tex.shape[0]-1),0,tex.shape[0]-1),np.clip(u*(tex.shape[1]-1),0,tex.shape[1]-1)]
            alpha=map_coordinates(tex[:,:,3],coords,order=1,mode='nearest')
            mask=(a>=0)&(b>=0)&(c>=0)&(alpha>=128)&(d<depth[y0:y1+1,x0:x1+1])
            col=np.clip(np.stack([map_coordinates(tex[:,:,j],coords,order=1,mode='nearest') for j in range(3)],2)*np.array(TINT),0,255)
            canvas[y0:y1+1,x0:x1+1][mask]=col[mask];depth[y0:y1+1,x0:x1+1][mask]=d[mask]
        im=Image.fromarray(canvas);draw=ImageDraw.Draw(im);draw.rectangle((0,0,w,50),fill=(22,25,29));draw.text((16,13),f'v051 actual grass meshes, view {k+1} — source preview, not game footage',font=terrain.font(21),fill='white')
        im.save(OUT/f'grass_source_view_{k+1}.jpg',quality=94)
    return dict(actual_exported_fbx_triangles=len(tris),texture=TEXTURE,source_only=True)
def main():
    OUT.mkdir(parents=True,exist_ok=True);sample=Circuit();terrain.OUT=OUT;terrain.O=O;terrain.M=M;terrain.source=source
    xz=sample.p;terrain.BOX=(float(xz[:,0].min()-16),float(xz[:,1].min()-16),float(xz[:,0].max()+16),float(xz[:,1].max()+16))
    def loc(s,l,above):
        x=np.interp(s,sample.q[:,3],sample.q[:,0]);z=np.interp(s,sample.q[:,3],sample.q[:,1]);v=np.array([np.interp(s,sample.q[:,3],sample.v[:,0]),np.interp(s,sample.q[:,3],sample.v[:,1])]);x-=l*v[1];z+=l*v[0]
        return [x,z,float(sample.ground(np.array([x]),np.array([z]))[0])+above]
    renders=[];comparisons=[]
    for label,s0,s1 in [('finish_face',2.,27.),('triple_face',125.,150.),('table_single',227.,250.),('big_tabletop',740.,767.),('rollers',1294.,1330.)]:
        eye=loc(s0,0.,1.7);target=loc(s1,0.,1.0)
        points=np.asarray([eye[:2],target[:2],loc(s1+22,0.,0.)[:2]])
        lo=points.min(0)-12;hi=points.max(0)+12;terrain.BOX=(float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1]))
        colors,normals=terrain.composite('v051',n=1800)
        p=terrain.render('v051',label,colors,normals,sample,eye,target,width=1200,height=750);renders.append(dict(file=p.name,sha256=sha(p),box=terrain.BOX))
    for trial in TRIALS:
        s0=trial['lo']-3;s1=trial['lo']+18
        eye=loc(s0,0.,1.8);target=loc(s1,0.,.8)
        points=np.asarray([eye[:2],target[:2],loc(trial['hi'],0.,0.)[:2]])
        lo=points.min(0)-14;hi=points.max(0)+14;terrain.BOX=(float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1]))
        frames=[];fields=[]
        for version in ['v051_control','v051']:
            c,n=terrain.composite(version,n=1600);fields.append(c)
            p=terrain.render(version,'trial_'+trial['id'],c,n,sample,eye,target,width=1100,height=690);frames.append(Image.open(p).copy())
        sheet=Image.new('RGB',(2200,730),(22,25,29));sheet.paste(frames[0],(0,40));sheet.paste(frames[1],(1100,40));d=ImageDraw.Draw(sheet)
        d.text((14,10),f"{trial['id']} {trial['feature']}: v051 with old layer retained",font=terrain.font(20),fill='white')
        d.text((1114,10),f"Same v051 with ONLY layer {trial['layer']} removed here",font=terrain.font(20),fill='white')
        name='comparison_trial_'+trial['id']+'.jpg';sheet.save(OUT/name,quality=94)
        delta=np.abs(fields[0].astype(np.int16)-fields[1].astype(np.int16))
        comparisons.append(dict(trial=trial['id'],file=name,one_mask_difference=trial['mask'],mean_abs_rgb_delta=float(delta.mean()),max_abs_rgb_delta=int(delta.max()),same_new_grooming_and_ground_grass=True))
    terrain.BOX=(float(xz[:,0].min()-16),float(xz[:,1].min()-16),float(xz[:,0].max()+16),float(xz[:,1].max()+16))
    colors,normals=terrain.composite('v051',n=2400)
    im=Image.fromarray(colors);im.save(OUT/'whole_circuit_colour_source.jpg',quality=94)
    # Actual route coordinates identify the three independent ride-test areas.
    mapimage=im.resize((1400,1400));draw=ImageDraw.Draw(mapimage)
    def project(p):return ((p[0]-terrain.BOX[0])/(terrain.BOX[2]-terrain.BOX[0])*1400,(terrain.BOX[3]-p[1])/(terrain.BOX[3]-terrain.BOX[1])*1400)
    draw.line([project(p) for p in sample.p],fill=(240,240,230),width=3)
    for t,c in zip(TRIALS,[(90,190,245),(250,165,65),(210,115,230)]):
        sel=(sample.q[:,3]>=t['lo'])&(sample.q[:,3]<=t['hi']);pp=[project(p) for p in sample.p[sel]];draw.line(pp,fill=c,width=12)
        x,y=pp[len(pp)//2];draw.rectangle((x-4,y-8,x+220,y+35),fill=(20,25,29));draw.text((x+3,y-3),t['id']+' '+t['feature'],font=terrain.font(19),fill=c)
    draw.rectangle((0,0,1400,48),fill=(20,25,29));draw.text((16,12),'v051: one historical overlay removal in each marked section — source map',font=terrain.font(22),fill='white')
    mapimage.save(OUT/'v051_trial_map.jpg',quality=94)
    grass=grass_views(sample)
    save(OUT/'manifest.json',dict(source_only=True,game_captures=False,terrain_sha256=sha(BASE/'terrain.raw'),renders=renders,grass=grass,layer_trial_comparisons=comparisons,box_world_xz_m=terrain.BOX))
    print('v051 actual-source terrain/grass previews ready.',flush=True)
if __name__=='__main__':main()
