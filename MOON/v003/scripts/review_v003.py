"""Reproducible layout and flight plots from the exact native RAW grid."""
from pathlib import Path
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
V=Path(__file__).resolve().parents[1];B=V/'build';P=V/'previews'
sys.path.insert(0,str(V/'scripts'))
import build_v003 as source

def main():
    spec=json.loads((B/'source_validation.json').read_text());data=np.load(B/'design.npz')
    h=data['height'];xy=data['route_xy'];by=data['bypasses'];P.mkdir(exist_ok=True)
    relief=LightSource(azdeg=307,altdeg=22).hillshade(h,vert_exag=1,dx=source.DX,dy=source.DX)
    plt.style.use('dark_background')
    fig,ax=plt.subplots(figsize=(11,11));ax.imshow(relief,cmap='gray',extent=(-800,800,-800,800))
    ax.plot(xy[:,0],xy[:,1],c='#50d8fa',lw=1.4,label='Main crater circuit')
    for i,q in enumerate(by):ax.plot(q[:,0],q[:,1],'--',c='#f5c96b',lw=1.2,label='Bypass' if i==0 else None)
    for j in spec['features']:
        x,y=j['center'];d=np.array(j['direction']);c=np.array([x,y]);lip=c-d*j['gap']/2;land=c+d*j['gap']/2
        ax.plot([lip[0],land[0]],[lip[1],land[1]],c='#fc9360',lw=3)
        ax.annotate(j['id']+' · '+str(j['gap'])+' m',c,xytext=(15,8),textcoords='offset points',fontsize=10,color='#ffffff',bbox=dict(fc='#15202a',alpha=.85,ec='none',pad=3))
    ax.plot([-110,110],[0,0],c='#ff809e',lw=3,label='Optional Shorty transfer · 220 m')
    ax.text(0,65,'Measured Shorty',ha='center',fontsize=11)
    pit=data['pit'];ax.scatter(*pit,c='#62f5b2',s=80,marker='s',label='Pits');q=data['access'];ax.plot(q[:,0],q[:,1],c='#62f5b2',lw=2)
    ax.plot([480,680],[-745,-745],color='white',lw=4);ax.text(580,-725,'200 m',ha='center')
    ax.set(xlim=(-800,800),ylim=(-800,800),xlabel='Local east (m)',ylabel='Local north (m)',title='TAURUS–LITTROW · CRATER SEND v003\nMapped Moon setting · fictional giant crater jumps · half gravity')
    ax.legend(loc='upper right',fontsize=9,framealpha=.9);fig.tight_layout();fig.savefig(P/'05_layout.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,12))
    for ax,j in zip(axes.flat,spec['features']):
        c=np.array(j['center']);d=np.array(j['direction']);u=np.linspace(-65,j['gap']+90,1100)
        pos=c+d*(u-j['gap']/2)[:,None];ground=source.sample(h,pos[:,0],pos[:,1]);lip=j['launch_height_absolute_m']-spec['terrain_height_offset_m']
        ax.fill_between(u,ground,np.min(ground)-5,color='#7b7c83');ax.plot(u,ground,c='white',lw=1)
        flight_u=np.linspace(0,j['gap']+30,400);ax.plot(flight_u,lip+source.ballistic(flight_u,j),c='#50d8fa',lw=2)
        ax.axvspan(0,j['gap'],color='#ed9464',alpha=.12)
        ax.set(title=f"{j['id']} {j['name']} · {j['gap']} m gap · {j['suggested_lip_speed_kmh']} km/h at lip",xlabel='Distance from takeoff lip (m)',ylabel='Terrain height above datum (m)');ax.grid(alpha=.15)
    fig.suptitle('HALF GRAVITY · 4.905 m/s²\nPoint-mass flight over actual quantized terrain; bike, suspension and rider remain untested',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(P/'06_flight_profiles.png',dpi=140);plt.close(fig)
    print('V003_LAYOUT_AND_FLIGHT_PLOTS_PASS',flush=True)

if __name__=='__main__':main()
