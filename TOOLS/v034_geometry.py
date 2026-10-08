"""Local holeshot clearance revision from the tested v033 layout."""
from pathlib import Path
import io,json,math,numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial import cKDTree
from v024_common import route_point,start_path,ease
from reference_route import native_segments,sample_native,write_tcl
from v033_common import atomic,save,image_file
R=Path(__file__).resolve().parents[1];BASE=R/'V033_OUTPUT';O=R/'V034_OUTPUT';S=R/'V034_SOURCE'
def point(q,s):return route_point(q,s)
def geometry():
 d=dict(np.load(BASE/'route.npz'));old=d['q'];w=d['width'];turns=json.loads((BASE/'turns.json').read_text());t=next(t for t in turns if t['id']=='T05');cfg=json.loads((S/'holeshot_spec.json').read_text());shift=np.array(cfg['corner_translation_xz_m']);a,b=t['arc_start'],t['arc_end'];p0,p1=cfg['main_connector_old_station_bounds_m']
 def connector(begin,end):
  length=np.linalg.norm(end[:2]-begin[:2]);v=np.array([[np.cos(begin[2]),np.sin(begin[2])],[np.cos(end[2]),np.sin(end[2])]])
  sp=CubicHermiteSpline([0,length],np.array([begin[:2],end[:2]]),v*cfg['connector_tangent_scale']);return sp(np.linspace(0,length,int(length/.10)+1))
 pA=point(old,a);pB=point(old,b);pA[:2]+=shift;pB[:2]+=shift
 entry=connector(point(old,p0),pA);exit=connector(pB,point(old,p1));arc=old[(old[:,3]>=a)&(old[:,3]<=b),:2]+shift
 xy=np.vstack([old[old[:,3]<p0,:2],entry,arc,exit,old[old[:,3]>p1,:2]]);labels=np.r_[old[old[:,3]<p0,3],np.linspace(p0,a,len(entry)),old[(old[:,3]>=a)&(old[:,3]<=b),3],np.linspace(b,p1,len(exit)),old[old[:,3]>p1,3]]
 keep=np.r_[True,np.linalg.norm(np.diff(xy,axis=0),axis=1)>1e-7];xy=xy[keep];labels=labels[keep];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))];heading=np.unwrap(np.arctan2(np.gradient(xy[:,1],s),np.gradient(xy[:,0],s)));q=np.c_[xy,heading,s,np.zeros(len(s))];width=np.interp(labels,old[:,3],w);mapping=np.interp(old[:,3],labels,s)
 origin,theta,segs=native_segments(q,station_spacing=.8);native=sample_native(origin,theta,segs,.16)
 O.mkdir(exist_ok=True);write_tcl(O/'main.tcl',origin,theta,segs)
 merge=float(np.interp(cfg['merge_old_main_station_m'],old[:,3],mapping));startcfg=dict(start_origin_xz=[416,172],start_controls_xz=cfg['start_controls_xz'],merge_station_m=merge)
 sa,startsegs,starttheta=start_path(startcfg,q);write_tcl(O/'start.tcl',sa[0,:2],starttheta,startsegs)
 d.update(q=q,width=width,curvature=np.gradient(q[:,2],q[:,3]),native=native,start=sa,old_to_new_v033_station=mapping,v033_station=labels)
 if 'v005_s' in d:d['v005_s']=np.interp(labels,old[:,3],d['v005_s'])
 if 'old_to_new_station' in d:d['old_to_new_station']=np.interp(d['old_to_new_station'],old[:,3],mapping)
 buff=io.BytesIO();np.savez_compressed(buff,**d);atomic(O/'route.npz',buff.getvalue())
 nt=[]
 for turn in turns:nt.append(dict(turn,**{k:float(np.interp(turn[k],old[:,3],mapping)) for k in ['mid','arc_start','arc_end']}))
 save(O/'turns.json',nt)
 profiles=json.loads((BASE/'jump_profiles.json').read_text())
 for p in profiles:
  for k in ['station_start_m','station_end_m','lip_s']:
   if k in p:p[k]=float(np.interp(p[k],old[:,3],mapping))
 save(O/'jump_profiles.json',profiles)
 save(O/'holeshot_layout.json',dict(**cfg,new_main_lap_length_m=float(q[-1,3]),old_main_lap_length_m=float(old[-1,3]),new_start_length_m=float(sa[-1,3]),merge_main_station_m=merge,merge_xz_m=sa[-1,:2].tolist(),start_origin_xz_m=sa[0,:2].tolist()))
 return old,w,q,width,sa,mapping,labels

def survey():
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 old,w,q,width,sa,mapping,labels=geometry();oldsa=np.load(BASE/'route.npz')['start'];cfg=json.loads((S/'holeshot_spec.json').read_text());fig,axes=plt.subplots(1,2,figsize=(15,9),sharex=True,sharey=True)
 for ax,main,mw,start,title,knots in zip(axes,[old,q],[w,width],[oldsa,sa],['v033 before','v034 local holeshot revision'],[json.loads((R/'V024_SOURCE/facilities.json').read_text())['start_width_knots'],cfg['start_width_knots']]):
  for route,widths,col in [(main,mw,'#aa7049'),(start,np.interp(start[:,3],*np.array(knots).T),'#1e98ce')]:
   n=np.c_[-np.sin(route[:,2]),np.cos(route[:,2])];left=route[:,:2]+n*widths[:,None]/2;right=route[:,:2]-n*widths[:,None]/2;poly=np.vstack([left,right[::-1]])
   ax.fill(poly[:,0],poly[:,1],color=col,alpha=.50);ax.plot(route[:,0],route[:,1],color=col,lw=1)
  ax.scatter([416],[184],marker='s',s=40,color='black');ax.text(416,180,'24 gates',ha='center');ax.set_title(title);ax.set_aspect('equal',adjustable='box');ax.set_xlim(290,450);ax.set_ylim(160,320);ax.invert_yaxis();ax.grid(alpha=.2);ax.set_xlabel('Game X (m)');ax.set_ylabel('Game Z (m)')
 fig.tight_layout();b=io.BytesIO();fig.savefig(b,format='png',dpi=135);atomic(R.parent/'v034-review/layout_candidates.png',b.getvalue());plt.close(fig)
 mainmask=(q[:,3]<np.interp(428.7,old[:,3],mapping))|(q[:,3]>np.interp(497.0,old[:,3],mapping));pq=q[mainmask];pw=width[mainmask]
 pairs=cKDTree(q[::5,:2]).query_pairs(25,output_type='ndarray');qs=q[::5];ww=width[::5];bad=[]
 for i,j in pairs:
  sep=abs(qs[j,3]-qs[i,3]);sep=min(sep,q[-1,3]-sep)
  if sep<60:continue
  if not (428<labels[::5][i]<498 or 428<labels[::5][j]<498):continue
  gap=np.linalg.norm(qs[j,:2]-qs[i,:2])-(ww[i]+ww[j])/2
  if gap<1:bad.append([labels[::5][i],labels[::5][j],gap])
 print('main changed-sector overlaps',bad[:12]);print('main length',q[-1,3],'start length',sa[-1,3]);print('main native closure',np.linalg.norm(np.load(O/'route.npz')['native'][-1,:2]-np.load(O/'route.npz')['native'][0,:2]));print('start',sa[::100]);
 for station in np.arange(85,sa[-1,3],10):
  p=point(sa,station);startw=np.interp(station,*np.array(cfg['start_width_knots']).T);ds,ids=cKDTree(q[:,:2]).query([p[:2]]);i=ids[0];print('start clearance',round(station),np.round(p[:2],1),'main oldstation',round(labels[i],1),'edgegap',round(float(ds[0]-(startw+width[i])/2),2))
if __name__=='__main__':survey()
