#!/usr/bin/env python3
"""Orlando reference-based construction, v005. Geometry is estimated, not surveyed."""
from pathlib import Path
import json, math, csv, shutil, io, os
import numpy as np
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator, CubicHermiteSpline
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
NAME='orlandomx_2026_v005'
N=2049; SIZE=600.; SCALE=18.
def savejson(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def main():
    for d in ['00_REFERENCES','01_GIS_AERIAL','02_HEIGHTMAP','03_MASKS','04_TEXTURES','05_NORMALS','06_SHADERS','07_OBJECTS_SOURCE','08_OBJECTS_GAME','09_TRACKED','10_COMPILED','11_TEST_BUILDS','12_RELEASE','BUILD','DOCUMENTATION','TOOLS']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    from reference_route import sample_native,write_tcl
    info=json.loads((ROOT/'01_GIS_AERIAL/geometry.json').read_text());d=np.load(ROOT/'01_GIS_AERIAL/route.npz');q=d['q'];w=d['width'];turns=info['turns'];total=q[-1,3];cut=0.;origin=q[0,:2]
    end=np.array([np.interp(15,q[:,3],q[:,i]) for i in range(2)]);th=np.interp(15,q[:,3],q[:,2]);controls=np.array([[236,153],[262,153],[290,173],end]);kn=np.r_[0,np.cumsum(np.linalg.norm(np.diff(controls,axis=0),axis=1))];dv=np.array([[1,0],[1,.10],[.91,.41],[math.cos(th),math.sin(th)]]);sp=CubicHermiteSpline(kn,controls,dv);tt=np.linspace(0,kn[-1],240);p=sp(tt);pp=np.vstack([p[::4],p[-1]]);v=np.diff(pp,axis=0);lens=np.linalg.norm(v,axis=1);u=v/lens[:,None];angles=np.arctan2(u[:-1,0]*u[1:,1]-u[:-1,1]*u[1:,0],(u[:-1]*u[1:]).sum(1));trim=np.minimum(lens[:-1],lens[1:])*.24;entries=pp.copy();exits=pp.copy();entries[1:-1]-=u[:-1]*trim[:,None];exits[1:-1]+=u[1:]*trim[:,None];sasegs=[]
    for i in range(len(pp)-1):
        sasegs.append((0,float(np.linalg.norm(entries[i+1]-exits[i])),0,0))
        if i<len(angles) and abs(angles[i])>1e-8:
            rad=trim[i]/math.tan(abs(angles[i])/2);sasegs.append((1,float(abs(angles[i])*rad),float(-math.copysign(rad,angles[i])),float(abs(math.degrees(angles[i])))))
    sa=sample_native(exits[0],math.atan2(u[0,1],u[0,0]),sasegs,.2);write_tcl(ROOT/'09_TRACKED/start.tcl',exits[0],math.atan2(u[0,1],u[0,0]),sasegs)
    data={k:d[k] for k in d.files};data['start']=sa;np.savez_compressed(ROOT/'01_GIS_AERIAL/route.npz',**data);info.update(start_segments=sasegs,start_merge_native_s=15.,start_placement='Estimated apron on paddock side',grid_stalls=24,pit_stalls=24)
    with (ROOT/'01_GIS_AERIAL/centerline.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['source_s_m','native_s_m','x_m','z_m','heading_radians','width_m'])
        for row,wi in zip(q,w):wr.writerow([row[3],(row[3]-cut)%total,row[0],row[1],row[2],wi])
    # One or more obstacles per observed jump group. Their metric profiles are modelling estimates.
    specs=[('J01',3.15,9.5,9,14),('J02',2.05,8,5,11),('J03',1.7,7,6,10),('J04',3.05,10,11,14),('J05',1.6,12,4,13),('J06',3.25,8,6,12),('J07',.85,7,1,9),('J08a',.65,5,1.5,6),('J08b',2.55,9,7,12),('J09a',1.15,6,2,8),('J09b',2.2,8,6,11),('J10a',1.9,7,4,10),('J10b',2.65,9,7,12),('J11',3.45,10,10,16),('J12a',1.6,7,4,10),('J12b',2.1,8,5,11)];features={f['id']:f for f in info['features']};jumps=[]
    for jid,h,face,top,land in specs:
        xs=[-face-2,-face,0,1.2,1.2+top,3.2+top,top+land+3.2,top+land+6.2];ys=[0,0,h,h+.15,h+.15,h-.06,0,0];ds=[0,0,min(.52,1.2*h/face),0,0,-min(.25,h/land),0,0]
        jumps.append(dict(id=jid,lip_s=features[jid]['native_s_m'],height_m=h,profile_s=xs,profile_h=ys,profile_derivative=ds,face_m=face,top_m=top,landing_m=land,status='Estimated; riding validation pending'))
    savejson(ROOT/'02_HEIGHTMAP/jump_profiles.json',jumps)
    def ground(uv):
        a=np.c_[np.array(uv,float),np.ones(len(uv))]@np.array(info['pixel_to_nominal_ground']).T;a=a[:,:2]/a[:,2,None];return a@np.array(info['rotation']).T*info['plane_scale']+np.array(info['offset'])
    pondpix=[[[951,476],[998,452],[1060,456],[1173,491],[1260,526],[1274,552],[1220,563],[1123,547],[1010,512]],[[772,592],[811,585],[876,619],[948,658],[1000,690],[967,698],[896,664],[822,626]],[[735,302],[777,296],[800,310],[800,332],[771,344],[732,332]]];ponds=[ground(v).tolist() for v in pondpix];im=Image.new('L',(N,N));dr=ImageDraw.Draw(im)
    for poly in ponds:dr.polygon([(x/600*2048,(600-z)/600*2048) for x,z in poly],fill=255)
    pondmask=gaussian_filter(np.array(im,dtype=np.float32)/255,3);wetmask=np.zeros((N,N),np.float32)
    tree=cKDTree(q[:-1,:2]);stree=cKDTree(sa[:,:2]);axes=np.linspace(0,SIZE,N)
    H=np.empty((N,N),np.float32);track=np.empty_like(H);pit=np.empty_like(H);start=np.empty_like(H);shoulder=np.empty_like(H);sand=np.empty_like(H);rutmask=np.empty_like(H)
    nearest_s=np.empty_like(H);nearest_lat=np.empty_like(H)
    pitrect=[253.,346.,105.,132.];info['pit_rectangle_xz']=pitrect
    for row in range(0,N,48):
        zz,xx=np.meshgrid(SIZE-axes[row:row+48],axes,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()]
        dist,ind=tree.query(pts,workers=2);dist=dist.reshape(xx.shape);ind=ind.reshape(xx.shape)
        px=q[ind,0];pz=q[ind,1];theta=q[ind,2]
        lat=(xx-px)*-np.sin(theta)+(zz-pz)*np.cos(theta)
        along=(xx-px)*np.cos(theta)+(zz-pz)*np.sin(theta)
        s=(q[ind,3]+along)%total;wi=w[ind];nearest_s[row:row+len(xx)]=s;nearest_lat[row:row+len(xx)]=lat
        corridor=1-smooth((dist-wi/2+.1)/1.1);sh=1-smooth((dist-wi/2-1.2)/2.0)
        ds,si=stree.query(pts,workers=2);ds=ds.reshape(xx.shape);si=si.reshape(xx.shape)
        sw=10.5+25.5*(1-smooth((sa[si,3]-12)/43));startalpha=(1-smooth((ds-sw/2)/1.3))*(1-smooth((236-xx)/2))
        # Rectangular paddock and an access link to the rear of the start apron.
        x1,x2,z1,z2=pitrect;outside=np.maximum.reduce([x1-xx,xx-x2,z1-zz,zz-z2,np.zeros_like(xx)])
        pa=1-smooth(outside/3)
        a=np.array([242.,127.]);b=np.array([241.,152.]);v=b-a;u=np.clip(((pts-a)*v).sum(1)/(v*v).sum(),0,1);access=1-smooth((np.linalg.norm(pts-(a+u[:,None]*v),axis=1).reshape(xx.shape)-7)/2)
        pa=np.maximum(pa,access)
        base=3+.12*np.sin(xx/55)+.10*np.cos(zz/73)+.05*np.sin((xx+zz)/29)
        flatten=np.maximum(pa,startalpha);base=base*(1-flatten)+3*flatten
        water=pondmask[row:row+len(xx)]*smooth((dist-wi/2-1)/3);wetmask[row:row+len(xx)]=water;base-=water*1.25
        surf=base.copy();height_j=np.zeros_like(base)
        for j in jumps:
            delta=(s-j['lip_s']+total/2)%total-total/2;xs=j['profile_s'];mask=(delta>=xs[0])&(delta<=xs[-1])
            if np.any(mask):
                hh=CubicHermiteSpline(xs,j['profile_h'],j['profile_derivative'])(np.clip(delta,xs[0],xs[-1]))
                height_j+=np.maximum(hh,0)*(1-smooth((abs(lat)-wi/2+.4)/3.5))*mask
        surf+=height_j
        corner=np.zeros_like(base);rut=np.zeros_like(base)
        for i,e in enumerate(turns):
            dd=(s-e['mid']+total/2)%total-total/2;extent=(e['arc_end']-e['arc_start'])/2;fade=smooth((dd+extent+10)/12)*(1-smooth((dd-extent+2)/12));out=-np.sign(e['angle'])*lat
            surf+=(.95+.18*(i%3))*smooth((out+.4)/(wi/2+.4))*(1-smooth((out-wi/2)/3))*fade
            if e['id']=='T02':surf+=np.exp(-(dd/24)**4)*(1-smooth((abs(lat)-wi/2)/3))
            if e['id']=='T05':surf+=.75*np.exp(-((dd-12)/32)**4)*(1-smooth((abs(lat)-wi/2)/3))
            if e['id']=='T06':surf+=.45*np.exp(-(dd/23)**4)*(1-smooth((abs(lat)-wi/2)/3))
            rut=np.maximum(rut,(np.exp(-((out-1.6-.35*np.sin(dd/13))/.55)**2)+.6*np.exp(-((out+1.5)/.7)**2))*fade*corridor)
        crown=.08*np.maximum(0,1-(lat/(wi/2))**2)*corridor
        surf+=crown
        surf=surf*(1-flatten*(1-sh))+3*flatten*(1-sh)
        H[row:row+len(xx)]=surf
        track[row:row+len(xx)]=corridor;shoulder[row:row+len(xx)]=np.maximum.reduce([sh,startalpha,pa]);pit[row:row+len(xx)]=pa;start[row:row+len(xx)]=startalpha
        sand[row:row+len(xx)]=corridor*(.25+.2*np.sin(s/70)**2);rutmask[row:row+len(xx)]=rut*corridor
        if row%384==0:print('terrain row',row,flush=True)
    original=H.copy();passes=0
    for it in range(32):
        gy,gx=np.gradient(H,SIZE/(N-1));bad=(np.hypot(gx,gy)>.74)&(track>.8)
        if not bad.any():break
        weight=np.clip(gaussian_filter(bad.astype(np.float32),2)*6,0,1);H=H*(1-weight)+gaussian_filter(H,2)*weight;passes+=1
    gy,gx=np.gradient(H,SIZE/(N-1));maxgrade=float(np.hypot(gx,gy)[track>.95].max());assert maxgrade<.80
    assert np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
    raw=np.round(H/SCALE*65535).astype('<u2');raw.tofile(ROOT/'02_HEIGHTMAP/terrain.raw');buf=io.BytesIO();Image.fromarray(raw).save(buf,format='PNG');(ROOT/'02_HEIGHTMAP/terrain_16bit.part').write_bytes(buf.getvalue());os.replace(ROOT/'02_HEIGHTMAP/terrain_16bit.part',ROOT/'02_HEIGHTMAP/terrain_16bit.png')
    np.save(ROOT/'02_HEIGHTMAP/height_metres.npy',H)
    # Masks have exactly the same orientation and extent as the 2049-node heightmap.
    masks={'racing':track,'shoulder':shoulder,'pits':pit,'start':start,'grass':(1-shoulder)*(1-wetmask),'off':1-np.maximum.reduce([track,pit,start]),'sand':sand,'ruts':rutmask,'worked':rutmask*.45}
    for name,arr in masks.items():
        a=Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).resize((2048,2048),Image.Resampling.BILINEAR)
        a.save(ROOT/f'03_MASKS/{name}.png');rgba=Image.new('RGBA',a.size,'white');rgba.putalpha(a);rgba.save(ROOT/f'03_MASKS/{name}.tga')
    # Original procedural surface colour/noise, no copied commercial textures.
    rng=np.random.default_rng(20260912);n=rng.normal(0,1,H.shape).astype(np.float32);macro=gaussian_filter(n,24);macro/=max(float(macro.std()),1e-6)
    soil=np.array([140,106,75],np.float32);grasscol=np.array([95,112,65],np.float32);shouldcol=np.array([160,138,101],np.float32)
    rgb=grasscol[None,None,:]*(1-shoulder[:,:,None])+shouldcol[None,None,:]*shoulder[:,:,None]
    rgb=rgb*(1-track[:,:,None])+soil*track[:,:,None];rgb+=(macro[:,:,None]*7+n[:,:,None]*2);rgb-=rutmask[:,:,None]*13;rgb=rgb*(1-wetmask[:,:,None])+np.array([61,69,53])*wetmask[:,:,None]
    rgb=np.uint8(np.clip(rgb,0,255));Image.fromarray(rgb).resize((2048,2048),Image.Resampling.LANCZOS).save(ROOT/'04_TEXTURES/basemap.png')
    Image.fromarray(rgb).resize((2048,2048),Image.Resampling.LANCZOS).save(ROOT/'04_TEXTURES/basemap.tga')
    def tile(name,color,coarseness,spec):
        noise=rng.normal(0,1,(1024,1024));noise=gaussian_filter(noise,coarseness,mode='wrap');noise/=noise.std()
        fine=rng.normal(0,1,(1024,1024));value=noise*9+fine*3
        rgb=np.uint8(np.clip(np.array(color)[None,None,:]+value[:,:,None],0,255));Image.fromarray(rgb).save(ROOT/f'04_TEXTURES/{name}.tga')
        Image.fromarray(np.uint8(rgb.astype(float)*.71)).save(ROOT/f'04_TEXTURES/{name}_wet.tga')
        gy,gx=np.gradient(noise);v=np.dstack([-gx*.22,gy*.22,np.ones_like(noise)]);v/=np.linalg.norm(v,axis=2)[:,:,None]
        normal=np.dstack([np.uint8((v*.5+.5)*255),np.full((1024,1024),spec,np.uint8)]);Image.fromarray(normal).save(ROOT/f'05_NORMALS/{name}_n.tga')
        (ROOT/f'06_SHADERS/{name}.shd').write_text(f'bump\n{{\n map = {name}_n.tga\n repetitions = 0\n}}\nspecular\n{{\n shininess = 10\n}}\n')
    tile('soil',[139,105,75],1.1,9);tile('prepared',[128,92,62],1.5,8);tile('worked',[115,87,60],1.3,12);tile('sand',[174,153,116],.65,6);tile('grass',[93,111,65],1.8,0)
    # Render-ready geometry source. Ground export is for review only; native game terrain uses RAW.
    meta=dict(pond_polygons=ponds,water_level=2.15,origin=origin.tolist(),pit_rectangle=pitrect,jumps=jumps,turns=turns,model_length=total,ground=3,coordinates='Blender X=game X, Blender Y=-game Z, Blender Z=game Y. Metres; FBX uses -Z forward, Y up.')
    savejson(ROOT/'07_OBJECTS_SOURCE/scene_spec.json',meta);savejson(ROOT/'01_GIS_AERIAL/geometry.json',info)
    hsample=map_coordinates(H,[(SIZE-q[:,1])/SIZE*(N-1),q[:,0]/SIZE*(N-1)],order=1)
    with (ROOT/'02_HEIGHTMAP/centerline_elevation.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['source_s_m','height_m']);wr.writerows(zip(q[:,3],hsample))
    qa=dict(maximum_racing_surface_grade=maxgrade,local_grade_relaxation_passes=passes,local_grade_relaxation_max_height_change_m=float(abs(H-original).max()),initial_surface='Clean; no baked braking bumps',raw_bytes=int(raw.nbytes),raw_expected=2049*2049*2,raw_png_identical=bool(np.array_equal(raw,np.array(Image.open(ROOT/'02_HEIGHTMAP/terrain_16bit.png')))),height_range_m=[float(H.min()),float(H.max())],lap_length_m=total,loop_closure_m=float(np.linalg.norm(q[0,:2]-q[-1,:2])),width_range_m=[float(w.min()),float(w.max())],jump_obstacles=len(jumps),jump_groups=12,turns=14,native_compilation=False,in_game_testing=False)
    savejson(ROOT/'DOCUMENTATION/terrain_validation.json',qa);print(json.dumps(qa,indent=2),flush=True)
if __name__=='__main__':main()

