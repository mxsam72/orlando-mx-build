"""Overhead of all 18 obstacles with exact station ranges, plus game map."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from v016_common import *

def main():
    q,w=route();sa=np.load(O/'route.npz')['start'];cfg=read(O/'facility_layout.json');info=read(R/'V009_SOURCE/baseline_geometry.json');profiles=read(S/'v016_geometry_spec.json')['profiles']
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    folder=R/'DOCUMENTATION/v016_qa';folder.mkdir(exist_ok=True)
    fig,(ax,tableax)=plt.subplots(1,2,figsize=(17,12),gridspec_kw={'width_ratios':[1.1,1]},layout='constrained')
    ax.imshow(H,extent=[0,600,0,600],cmap='terrain',vmin=1.5,vmax=7);ax.plot(q[:,0],q[:,1],color='#293e35',lw=1.5,label='Normal lap')
    ax.plot(sa[:,0],sa[:,1],color='#edca32',lw=4,label='Start loop → before T06');ff=np.array(cfg['fence_polyline_xz']);ax.plot(*ff.T,color='#249cda',lw=4,label='Spectator fence')
    gg=np.array([[g['x'],g['z']] for g in cfg['grid']]);ax.scatter(*gg.T,c='#edca32',marker='|',s=100)
    colors=plt.get_cmap('tab20')(np.linspace(0,1,18));rows=[]
    for p,col in zip(profiles,colors):
        ss=np.linspace(p['station_start_m'],p['station_end_m'],200);qq=ss%q[-1,3];th=np.interp(qq,q[:,3],q[:,2]);offset=p.get('lateral_offset_m',0)
        xy=np.c_[np.interp(qq,q[:,3],q[:,0])-offset*np.sin(th),np.interp(qq,q[:,3],q[:,1])+offset*np.cos(th)]
        ax.plot(*xy.T,color=col,lw=4,ls='--' if p['kind']=='none' else '-')
        mid=xy[len(xy)//2];ax.annotate(p['id'],mid,xytext=(5,7),textcoords='offset points',fontsize=9,fontweight='bold',bbox=dict(fc='white',alpha=.85,ec='none',pad=1))
        ax.scatter(*xy[[0,-1]].T,c=[col,col],s=12)
        rows.append([p['id'],p['kind'].replace('_',' '),f"{p['station_start_m']:.1f} – {p['station_end_m']:.1f}",f"{p['station_end_m']-p['station_start_m']:.1f}"])
    for t in info['turns']:
        p=route_point(q,t['mid']);ax.annotate(t['id'],p[:2],xytext=(-16,-12),textcoords='offset points',fontsize=7,color='#1f2420')
    for s in np.linspace(12,sa[-1,3]-5,6):
        p=route_point(sa,s);ax.arrow(p[0],p[1],2*np.cos(p[2]),2*np.sin(p[2]),width=.2,head_width=2,color='#987706')
    ax.set(xlim=(205,445),ylim=(160,445),aspect='equal',xlabel='Native X (m)',ylabel='Native Z (m)',title='Feature spans and route direction');ax.legend(loc='upper right',fontsize=8)
    tableax.axis('off');tbl=tableax.table(cellText=rows,colLabels=['Feature','User target','Station start – end (m)','Length (m)'],colWidths=[.12,.31,.40,.17],loc='center',cellLoc='left',bbox=[0,.16,1,.74]);tbl.auto_set_font_size(False);tbl.set_fontsize(10)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_edgecolor('#c7cdd0');cell.set_linewidth(.5)
        if r==0:cell.set_facecolor('#284b5c');cell.set_text_props(color='white',weight='bold')
        elif c==0:cell.set_facecolor(colors[r-1])
        else:cell.set_facecolor('#f2f5f5' if r%2 else 'white')
    tableax.text(0,.10,'R01: 2 × the v011 raised-earthwork length.\nR16: v011 length + 5 m. R12 / R17: 5 m crest spacing.\nDashed spans have no authored jump.\nR18 occupies only the inside line at T14.\nR01 starts at -2 m, wrapping across native station zero.',fontsize=10,va='top',linespacing=1.6)
    fig.suptitle('Orlando MX v016 — authoritative R01–R18 rebuild\nActual source terrain; lengths are construction targets, not survey measurements',fontsize=16);save_plot(fig,folder/'v016_layout.png',dpi=160);plt.close(fig)
    # Keep the game map square without squeezing the documentation table.
    fig,ax=plt.subplots(figsize=(8,8));ax.imshow(H,extent=[0,600,0,600],cmap='terrain',vmin=1.5,vmax=7);ax.plot(q[:,0],q[:,1],c='#283b33',lw=2);ax.plot(sa[:,0],sa[:,1],c='#dbc234',lw=3);ax.set(xlim=(190,465),ylim=(160,435),aspect='equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);save_plot(fig,folder/'game_map.png',dpi=128);plt.close(fig)
    dest=R/'12_RELEASE'/NAME
    if dest.exists():Image.open(folder/'game_map.png').convert('RGB').resize((1024,1024)).save(dest/(NAME+'_map.tga'))
    print('18-feature station map saved.')
if __name__=='__main__':main()
