"""Inspect authored masks/meshes; previews are explicitly not game screenshots."""
import re
from PIL import Image
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from v030_materials import layer_blocks
from v030_common import *

def surface(bounds,pixels=1200):
    x0,z0,x1,z1=bounds; nx=pixels;ny=max(2,int(pixels*(z1-z0)/(x1-x0)))
    xx,zz=np.meshgrid(np.linspace(x0,x1,nx),np.linspace(z1,z0,ny));color=np.zeros((*xx.shape,3),float)
    for _,_,block in layer_blocks((M/'track.hmf').read_text()):
        name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1];p=M/name
        if not p.exists():continue
        tile=np.asarray(Image.open(p).convert('RGB'),float);rep=int(re.search(r'repetitions\s*=\s*(\d+)',block)[1]);tw=SIZE/rep
        coords=[((SIZE-zz)/tw%1)*(len(tile)-1),(xx/tw%1)*(tile.shape[1]-1)]
        rgb=np.stack([map_coordinates(tile[...,k],coords,order=1,mode='wrap') for k in range(3)],axis=2)
        match=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        alpha=np.ones(xx.shape)
        if match:
            p=M/match[1]
            if not p.exists():p=O/'masks'/match[1].removeprefix('mask_')
            a=np.asarray(Image.open(p).getchannel('A'),float)/255
            alpha=map_coordinates(a,[(SIZE-zz)/SIZE*(len(a)-1),xx/SIZE*(a.shape[1]-1)],order=1,mode='nearest')
        color=color*(1-alpha[...,None])+rgb*alpha[...,None]
    h=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;hs=ground(h,np.c_[xx.ravel(),zz.ravel()]).reshape(xx.shape)
    dz,dx=np.gradient(hs,(z1-z0)/(ny-1),(x1-x0)/(nx-1));light=np.clip(.97-.10*dx+.12*dz,.68,1.18)
    return np.uint8(np.clip(color*light[...,None],0,255))

def main():
    global O,M
    q=np.load(O/'route.npz')['q'];a=dict(np.load(O/'practice_access.npz'));cfg=read(R/'V028_SOURCE/pit_access.json');meshes=read(O/'pit_facility_meshes.json')
    from facility_mesh_v016 import PALETTE
    bounds=[208,130,467,442];fig,ax=plt.subplots(figsize=(10,12));ax.imshow(surface(bounds),extent=[bounds[0],bounds[2],bounds[1],bounds[3]])
    for m in meshes:
        v=np.asarray(m['vertices'])[:,[0,2]];faces=[v[f] for f in m['faces']]
        col=np.array(PALETTE.get(m['material'],(72,76,75)))/255
        ax.add_collection(PolyCollection(faces,facecolor=col,edgecolor='none',alpha=.7 if m['material'].startswith('leaf') else 1))
    ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_aspect('equal');ax.set_title('v030 source surface/layout preview · not an in-game screenshot');ax.set_xlabel('Game X metres');ax.set_ylabel('Game Z metres');fig.tight_layout();save_png(fig,O/'surface_layout.png',dpi=130);plt.close(fig)
    turns=read(O/'turns.json');t09=next(t for t in turns if t['id']=='T09');idx=np.argmin(abs(q[:,3]-t09['mid']));c=q[idx,:2]
    panels=[('Behind-gate staging and practice access',[379,136,463,231]),('T09 matched rut paths and deposits',[c[0]-28,c[1]-28,c[0]+28,c[1]+28])]
    fig,axes=plt.subplots(1,2,figsize=(15,8))
    for ax,(title,b) in zip(axes,panels):
        ax.imshow(surface(b,1100),extent=[b[0],b[2],b[1],b[3]])
        for m in meshes:
            v=np.asarray(m['vertices'])[:,[0,2]]
            if not np.any((v[:,0]>=b[0])&(v[:,0]<=b[2])&(v[:,1]>=b[1])&(v[:,1]<=b[3])):continue
            col=np.array(PALETTE.get(m['material'],(72,76,75)))/255
            ax.add_collection(PolyCollection([v[f] for f in m['faces']],facecolor=col,edgecolor='none',alpha=.72 if m['material'].startswith('leaf') else 1))
        ax.set_xlim(b[0],b[2]);ax.set_ylim(b[1],b[3]);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('X metres');ax.set_ylabel('Z metres')
    fig.suptitle('v030 authored source previews · game lighting/handling remain to be checked');fig.tight_layout();save_png(fig,O/'pit_and_corner_detail.png',dpi=130);plt.close(fig)
    # The user correction concerns spatial scope. Show the entire course and
    # both pit paddocks together, using exact authored material composition.
    current_o,current_m=O,M; overview=[200,80,475,445]
    after=surface(overview,800)
    O=BASE; M=BASE/'materials'; before=surface(overview,800)
    O,M=current_o,current_m
    fig,axes=plt.subplots(1,2,figsize=(12,9))
    for ax,rgb,title in zip(axes,[before,after],['v028 grass baseline','v030: pits retained, start cleared, remaining course grass −50%']):
        ax.imshow(rgb,extent=[overview[0],overview[2],overview[1],overview[3]])
        poly=np.asarray(read(S/'surface_spec.json')['circled_polygon_xz_m'])
        ax.plot(*np.vstack([poly,poly[0]]).T,color='#ffe600',linewidth=1.6)
        ax.set_xlim(overview[0],overview[2]);ax.set_ylim(overview[1],overview[3]);ax.set_aspect('equal')
        ax.set_title(title,fontsize=10);ax.set_xlabel('Game X metres');ax.set_ylabel('Game Z metres')
        ax.text(208,98,'Pits grass: unchanged',color='white',fontsize=10,bbox=dict(facecolor='#151b18',alpha=.8,edgecolor='none'))
    fig.suptitle('Authored surface comparison · yellow outline follows the supplied circle · not in-game screenshots',fontsize=11)
    fig.tight_layout();save_png(fig,O/'grass_scope_comparison.png',dpi=140);plt.close(fig)
    print('v030 source texture/mask and pits/course scope previews written',flush=True)
if __name__=='__main__':main()
