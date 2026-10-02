"""CPU texture/z-buffer renderer of exact source meshes; never an in-game claim."""
import argparse, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib.font_manager import findfont
FONT=findfont("DejaVu Sans")
from v022_common import *
from facility_mesh_v022 import PALETTE

DEST=R/'DOCUMENTATION/v022_qa'

def raster(meshes,eye,target,span,output,title,size=(1280,800),ground_y=None):
    W,H=size;eye=np.array(eye,float);target=np.array(target,float);f=target-eye;f/=np.linalg.norm(f);right=np.cross(f,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,f)
    cam=np.stack([right,up,f],axis=1);scale=W/span;buf=np.empty((H,W,3),np.uint8);buf[:]=[219,226,232];depth=np.full((H,W),np.inf,np.float32)
    mats=read(S/'vehicle_materials.json');tex={k:np.asarray(Image.open(S/v['file']).convert('RGB')) for k,v in mats.items()}
    light=np.array([-.4,.85,.30]);light/=np.linalg.norm(light)
    for mesh in meshes:
        v=np.asarray(mesh['vertices']);p=(v-target)@cam;p[:,0]=W/2+p[:,0]*scale;p[:,1]=H/2-p[:,1]*scale
        if p[:,0].max()<0 or p[:,0].min()>=W or p[:,1].max()<0 or p[:,1].min()>=H:continue
        mat=mesh['material'];bitmap=tex.get(mat) if "uv" in mesh else None;rgb=np.array(mesh.get('rgb',PALETTE.get(mat,[100,100,100])))
        for fi,face in enumerate(mesh['faces']):
            for k in range(1,len(face)-1):
                ids=[face[0],face[k],face[k+1]];t=p[ids];a,b,c=t
                x0=max(0,int(math.floor(t[:,0].min())));x1=min(W-1,int(math.ceil(t[:,0].max())));y0=max(0,int(math.floor(t[:,1].min())));y1=min(H-1,int(math.ceil(t[:,1].max())))
                if x1<x0 or y1<y0:continue
                den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(den)<1e-6:continue
                vv=v[ids];n=np.cross(vv[1]-vv[0],vv[2]-vv[0]);nn=np.linalg.norm(n)
                if nn<1e-9:continue
                n/=nn
                # Double-sided panels are explicitly authored as paired triangles.
                if n@f>.00001:continue
                yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
                w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w2=1-w0-w1
                z=w0*a[2]+w1*b[2]+w2*c[2];db=depth[y0:y1+1,x0:x1+1];mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(z<db)
                if not mask.any():continue
                shade=.62+.38*max(0,n@light)
                if bitmap is not None:
                    uv=np.array(mesh['uv'][fi])[[0,k,k+1]];u=w0[mask]*uv[0,0]+w1[mask]*uv[1,0]+w2[mask]*uv[2,0];vvv=w0[mask]*uv[0,1]+w1[mask]*uv[1,1]+w2[mask]*uv[2,1]
                    # v022 stores readable decals pre-flipped to compensate for
                    # the native game's horizontal UV handedness. Undo that
                    # preflip in this CPU preview so the QA image represents the
                    # expected in-game orientation rather than the raw bitmap.
                    if mats.get(mat,{}).get('native_u_preflipped'):u=1-u
                    h,w=bitmap.shape[:2];col=bitmap[np.clip(((1-vvv)*(h-1)).astype(int),0,h-1),np.clip((u*(w-1)).astype(int),0,w-1)]*shade
                else:col=rgb*shade
                buf[y0:y1+1,x0:x1+1][mask]=np.clip(col,0,255).astype('uint8');db[mask]=z[mask]
    im=Image.fromarray(buf);d=ImageDraw.Draw(im);d.rectangle((0,0,W,63),fill='#f5f7f8');d.text((22,12),title,fill='#162c39',font=ImageFont.truetype(FONT,21));d.text((22,39),'v022 native-handedness preview — readable decals compensated; game lighting differs',fill='#425563',font=ImageFont.truetype(FONT,13));im.save(output);print('Rendered',output.name,flush=True)

def ground_mesh(H,bounds,step=3):
    cfg=read(S/'pit_facilities.json');x0,x1,z0,z1=bounds;out=[]
    for z in np.arange(z0,z1,step):
        for x in np.arange(x0,x1,step):
            pts=np.array([[x,z],[x,z+step],[x+step,z+step],[x+step,z]]);heights=ground(H,pts);rgb=[107,127, 77]
            center=pts.mean(0)
            for road in cfg['roads']:
                rp=np.array(road['points']);aa=rp[:-1];dd=rp[1:]-aa;tt=np.clip(((center-aa)*dd).sum(1)/(dd*dd).sum(1),0,1);dist=np.linalg.norm(center-(aa+tt[:,None]*dd),axis=1).min()
                if dist<road['width']/2:rgb=[186,180,159]
            out.append(dict(vertices=np.c_[pts[:,0],heights-.015,pts[:,1]].tolist(),faces=[[0,1,2,3]],material='ground',rgb=rgb))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--individual-only',action='store_true');args=ap.parse_args();DEST.mkdir(exist_ok=True)
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;meshes=read(O/'vehicle_meshes.json');assets=read(S/'vehicles.json')['assets'];fac=read(O/'facility_meshes.json')
    for a in assets:
        if a['id'].startswith('bike'):continue
        owner=a['id'].split('_')[-1];own=[m for m in meshes if m['asset'] in [a['id'],'bike_'+owner]];v=np.concatenate([m['vertices'] for m in own]);center=(v.min(0)+v.max(0))/2;t=math.radians(a['heading']);rot=np.array([[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]]);eye=center+np.array([-9,5,12])@rot.T
        g=ground_mesh(H,(v[:,0].min()-5,v[:,0].max()+5,v[:,2].min()-5,v[:,2].max()+5),2)
        raster(g+own,eye,center,10.8,DEST/(owner+'_pair.png'),owner.title()+' / vehicle and bike',size=(1400,900))
        # Opposite profile checks rear and side graphics as well as the front.
        eye2=center+np.array([10,3,-11])@rot.T
        raster(g+own,eye2,center,10.8,DEST/(owner+'_rear.png'),owner.title()+' / rear and side',size=(1280,800))
    for a in assets:
        if not a['id'].startswith('bike'):continue
        own=[m for m in meshes if m['asset']==a['id']];v=np.concatenate([m['vertices'] for m in own]);center=(v.min(0)+v.max(0))/2
        t=math.radians(a['heading']);rot=np.array([[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]])
        for side,offset in [('front',[-4,1.6,5]),('side',[5,1,-2])]:
            raster(own,center+np.array(offset)@rot.T,center,3.3,DEST/(a['id']+'_'+side+'.png'),a['id'].replace('_',' ').title()+' / number plates, plastics and mechanical detail',size=(1280,850))
    sign=next(a for a in read(S/'pit_facilities.json')['assets'] if a['id']=='bithlo_sticker_stop')
    own=[m for m in fac if m['asset']==sign['id']];v=np.concatenate([m['vertices'] for m in own]);center=(v.min(0)+v.max(0))/2
    t=math.radians(sign['heading']);rot=np.array([[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]])
    raster(own,center+np.array([.7,.2,7])@rot.T,center,3.5,DEST/'bithlo_sign_detail.png','Bithlo sign / actual reference stickers on thin metal panels',size=(1100,1200))
    if args.individual_only:return
    g=ground_mesh(H,(223,390,82,188),2)
    views=[('truck_cluster',[356,24,120],[334,4,154],37,'Four owner vehicles / grass parking beside frontage'),('pit_overview',[404,85,55],[308,6,140],190,'Entire pit / existing facilities retained'),('bathroom_trucks',[242,23,89],[304,4,136],100,'Bathroom access and owner parking'),('office_stop_sign',[311,15,126],[323,4,150], 50,'Office, sticker sign and owner parking')]
    for name,eye,target,span,title in views:raster(g+fac+meshes,eye,target,span,DEST/(name+'.png'),title,size=(1600,950))
    topdown(H,meshes,fac)

def topdown(H,meshes,fac):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull
    from matplotlib.patches import Polygon
    cfg=read(S/'pit_facilities.json');fig,ax=plt.subplots(figsize=(15,9));ax.set_facecolor('#adb88a')
    for road in cfg['roads']:
        p=np.array(road['points']);ax.plot(*p.T,color='#d4cbb7',lw=road['width']*3,solid_capstyle='round')
    for a in cfg['assets']:
        vv=[np.array(m['vertices']) for m in fac if m['asset']==a['id']]
        if not vv:continue
        v=np.concatenate(vv)[:,[0,2]];h=ConvexHull(v);ax.add_patch(Polygon(v[h.vertices],facecolor='#5d7957' if a['type']=='oak' else '#858e93',alpha=.7));ax.annotate(a['id'].replace('_',' '),a['xz'],fontsize=7,ha='center')
    colors={'jordan':'#dce4e9','premier':'#2477c1','sam':'#4b4336','shane':'#222c38'}
    for a in read(S/'vehicles.json')['assets']:
        v=np.concatenate([m['vertices'] for m in meshes if m['asset']==a['id']])[:,[0,2]];h=ConvexHull(v);ax.add_patch(Polygon(v[h.vertices],facecolor=colors[a['id'].split('_')[-1]],edgecolor='white'))
        if not a['id'].startswith('bike'):ax.annotate(a['id'].split('_')[-1].title(),a['xz'],xytext=(-2,15),textcoords='offset points',rotation=45,fontsize=9,fontweight='bold')
    f=np.array(read(S/'facilities.json')['fence_polyline_xz']);ax.plot(*f.T,c='#69543a',lw=3,label='Spectator fence');ax.scatter([x for x in range(260,331,10) for z in [110,117,124]],[z for x in range(260,331,10) for z in [110,117,124]],marker='x',c='#a14e39',label='Preserved pit spawns')
    ax.set(xlim=(224,381),ylim=(89,182),aspect='equal',xlabel='Native X (m)',ylabel='Native Z (m)',title='v022 actual mesh footprints / gravel roads and grass parking');ax.legend(loc='upper left');fig.tight_layout();fig.savefig(DEST/'vehicle_placement_topdown.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
