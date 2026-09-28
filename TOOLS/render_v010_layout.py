"""Exact authored layout and height differences; not a generated reference image."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from v010_common import *

def main():
    q,w=route();sa=np.load(O/'route.npz')['start'];cfg=read(O/'facility_layout.json');info=read(R/'V009_SOURCE/baseline_geometry.json')
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;B=np.fromfile(R/'V009_OUTPUT/terrain.raw','<u2').reshape(N,N)/65535*SCALE
    folder=R/'DOCUMENTATION/v010_qa';folder.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,11),layout='constrained')
    ax.imshow(H,extent=[0,600,0,600],cmap='terrain',vmin=1.5,vmax=7);ax.plot(q[:,0],q[:,1],color='#1c2723',lw=1.5,label='Normal lap')
    ax.plot(sa[:,0],sa[:,1],color='#edca32',lw=4,label='New start to T05');p=np.array(cfg['fence_polyline_xz']);ax.plot(p[:,0],p[:,1],color='#249cda',lw=4,label='Spectator fence')
    g=np.array([[st['x'],st['z']] for st in cfg['grid']]);ax.scatter(*g.T,c='#edca32',marker='|',s=100)
    for t in info['turns']:
        p=route_point(q,t['mid']);ax.annotate(t['id'],p[:2],xytext=(4,6),textcoords='offset points',fontsize=8)
    for p in read(S/'v010_geometry_spec.json')['profiles']:
        xz=route_point(q,p['lip_s'])[:2];ax.plot(*xz,'o',ms=3,c='#be4125');ax.annotate(p['id'],xz,xytext=(-14,-12),textcoords='offset points',fontsize=7,c='#963319')
    for s in np.linspace(8,sa[-1,3]-4,6):
        p=route_point(sa,s);ax.arrow(p[0],p[1],2*np.cos(p[2]),2*np.sin(p[2]),width=.25,head_width=2.1,color='#947500')
    ax.set(xlim=(205,449),ylim=(158,443),aspect='equal',xlabel='Native X (m)',ylabel='Native Z (m)',title='Orlando MX v010 — authored candidate\nGate → T05; fence outside T14–T01')
    ax.legend(loc='upper right',fontsize=8);fig.savefig(folder/'v010_layout.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,10),layout='constrained');im=ax.imshow(H-B,extent=[0,600,0,600],cmap='RdBu_r',vmin=-1,vmax=1);ax.plot(q[:,0],q[:,1],lw=.5,c='black');ax.plot(sa[:,0],sa[:,1],lw=1,c='#c09c00');ax.set(xlim=(205,449),ylim=(158,443),aspect='equal',title='v010 minus v009 actual terrain (m)');fig.colorbar(im,ax=ax);fig.savefig(folder/'v010_height_changes.png',dpi=150);plt.close(fig)
    dest=R/'12_RELEASE'/NAME
    if dest.exists():
        Image.open(folder/'v010_layout.png').convert('RGB').resize((1024,1024)).save(dest/(NAME+'_map.tga'))
    print('v010 authored layout and actual terrain difference plots saved.')
if __name__=='__main__':main()
