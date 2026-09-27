#!/usr/bin/env python3
"""Section authoring views from encoded terrain. These are not in-game captures."""
from pathlib import Path
import json,os,numpy as np
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
def main():
 q=np.load(R/'V009_SOURCE/baseline_route.npz')['q'];L=q[-1,3]
 h=np.fromfile(R/'V009_OUTPUT/terrain.raw','<u2').reshape(2049,2049)/65535*18
 b=np.fromfile(R/'BUILD/v009_baseline/terrain.raw','<u2').reshape(2049,2049)/65535*18
 out=R/'DOCUMENTATION/v009_qa/sections';out.mkdir(parents=True,exist_ok=True)
 sectors=json.loads((R/'V009_SOURCE/section_station_map.json').read_text())['sections']
 for sec in sectors:
  a=sec['route_station_start_m'];span=(sec['route_station_end_m']-a)%L;s=np.linspace(a,a+span,600);sm=s%L
  x,z,th=[np.interp(sm,q[:,3],q[:,k]) for k in range(3)]
  def sample(H,lat=0):return map_coordinates(H,[(600-z-np.cos(th)*lat)/600*2048,(x-np.sin(th)*lat)/600*2048],order=1)
  fig,axs=plt.subplots(1,2,figsize=(12,4.8),layout='constrained',gridspec_kw={'width_ratios':[1,1.65]})
  lo=np.maximum([0,0],np.array([x.min(),z.min()])-18);hi=np.minimum([600,600],np.array([x.max(),z.max()])+18)
  c0,c1=np.floor(lo[0]/600*2048).astype(int),np.ceil(hi[0]/600*2048).astype(int)
  r0,r1=np.floor((600-hi[1])/600*2048).astype(int),np.ceil((600-lo[1])/600*2048).astype(int)
  im=axs[0].imshow((h-b)[r0:r1,c0:c1],extent=[lo[0],hi[0],lo[1],hi[1]],origin='upper',cmap='RdBu_r',vmin=-2.2,vmax=2.2)
  axs[0].plot(x,z,color='#1f2824',lw=1.1);axs[0].scatter([x[0]],[z[0]],marker='>',color='#126d52');axs[0].set(xlabel='Map X (m)',ylabel='Map Z (m)',title='Terrain change / route');fig.colorbar(im,ax=axs[0],shrink=.7,label='Height change (m)')
  axs[1].plot(s-a,sample(b),color='#999',label='v008b center');axs[1].plot(s-a,sample(h),color='#963e25',lw=1.7,label='v009 center')
  axs[1].plot(s-a,sample(h,3.5),color='#45835e',lw=.8,label='v009 left +3.5 m');axs[1].plot(s-a,sample(h,-3.5),color='#467baf',lw=.8,label='v009 right -3.5 m')
  axs[1].set(xlabel='Distance from mapped section start (m)',ylabel='Terrain height (m)',title='Encoded longitudinal lines');axs[1].grid(alpha=.2);axs[1].legend(fontsize=8)
  repeated=' / repeated physical sector' if int(sec['section_id'][1:])>11 else ''
  fig.suptitle(f"{sec['section_id']}{repeated} — authoring view; in-game ride test pending",fontsize=12)
  destination=out/(sec['section_id']+'.png')
  with destination.open('wb') as fp:
   fig.savefig(fp,format='png',dpi=135);fp.flush();os.fsync(fp.fileno())
  plt.close(fig)
 from PIL import Image
 for sec in sectors:
  with Image.open(out/(sec['section_id']+'.png')) as im:im.load()
 print('Wrote 14 section authoring views, including repeated-reference aliases.')
if __name__=='__main__':main()
