"""Authoring-only soil and scope views. These are not game-renderer captures."""
import re
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from v031_common import *

def composite(folder,box,n=1200):
    text=(folder/'materials/track.hmf').read_text()
    X=np.linspace(box[0],box[2],n);Z=np.linspace(box[3],box[1],n)
    xx,zz=np.meshgrid(X,Z);image=np.zeros((n,n,3),np.float32)
    mask_shape=None
    for index,_,block in layer_blocks(text):
        name=re.search(r'map\s*=\s*(\S+)',block)[1]
        rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
        if not (folder/'materials'/name).is_file():
            assert index==0 and name=='basemap.tga'
            # This native foundation is completely covered by unmasked layer1.
            continue
        texture=np.asarray(Image.open(folder/'materials'/name).convert('RGB'),np.float32)
        tx=(xx/SIZE*rep%1)*(texture.shape[1]-1);ty=((SIZE-zz)/SIZE*rep%1)*(texture.shape[0]-1)
        sampled=np.stack([map_coordinates(texture[...,c],[ty,tx],order=1,mode='wrap') for c in range(3)],axis=-1)
        mask=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        if mask:
            a=np.asarray(Image.open(folder/'materials'/mask[1]).getchannel('A'),np.float32)/255
            alpha=map_coordinates(a,[(SIZE-zz)/SIZE*(a.shape[0]-1),xx/SIZE*(a.shape[1]-1)],order=1,mode='nearest')
        else:alpha=np.ones((n,n),np.float32)
        image=image*(1-alpha[...,None])+sampled*alpha[...,None]
    return np.uint8(np.clip(np.rint(image),0,255))

def main():
    box=[208,130,467,442]
    fig,axes=plt.subplots(1,2,figsize=(13.5,8.2),dpi=150)
    for ax,folder,title in zip(axes,[BASE,O],['Tested v030','v031 scanned soils - same grass and geometry']):
        ax.imshow(composite(folder,box),extent=[box[0],box[2],box[1],box[3]],origin='upper');ax.set_title(title,fontsize=11)
        ax.set_xlabel('Game X metres');ax.set_ylabel('Game Z metres')
        ax.text(214,145,'Pits grass: unchanged',color='white',fontsize=9,bbox=dict(facecolor='black',alpha=.6,edgecolor='none'))
    fig.suptitle('Authored surface comparison - source textures and masks, not in-game screenshots',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.965));b=io.BytesIO();fig.savefig(b,format='png');plt.close(fig)
    atomic(O/'surface_comparison.png',b.getvalue())
    print('v031 authored source comparison written.',flush=True)

if __name__=='__main__':main()
