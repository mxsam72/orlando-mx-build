#!/usr/bin/env python3
"""Numerical and plotted review of the actual encoded heightmap, not ideal recipes."""
from pathlib import Path
import json, numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];N=2049;DX=600/2048

def main():
 out=R/'DOCUMENTATION/v009_qa';out.mkdir(exist_ok=True);S=R/'V009_SOURCE';qa=json.loads((R/'DOCUMENTATION/v009_geometry_validation.json').read_text(encoding='utf-8'));d=np.load(S/'baseline_route.npz');q=d['q'];L=q[-1,3]
 B=np.fromfile(R/'BUILD/v009_baseline/terrain.raw','<u2').reshape(N,N)/65535*18;H=np.fromfile(R/'V009_OUTPUT/terrain.raw','<u2').reshape(N,N)/65535*18
 def sample(h,s,lat=0):
  s=np.asarray(s)%L;x,z,th=[np.interp(s,q[:,3],q[:,k]) for k in range(3)];x-=np.sin(th)*lat;z+=np.cos(th)*lat
  return map_coordinates(h,[(600-z)/600*2048,x/600*2048],order=1,mode='nearest')
 ss=np.linspace(0,L,round(L/.25)+1);before=sample(B,ss);after=sample(H,ss)
 fig,ax=plt.subplots(figsize=(15,4.5),layout='constrained');ax.plot(ss,before,color='#999999',lw=1,label='v008b');ax.plot(ss,after,color='#8f3f24',lw=1.4,label='v009 candidate');ax.set(xlabel='Native station (m)',ylabel='Encoded terrain height (m)',title='Actual centerline elevation — authoring view');ax.grid(alpha=.2);ax.legend();fig.savefig(out/'centerline_before_after.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(14,8),layout='constrained');region=(slice(560,1470),slice(670,1360));extent=[670*DX,1360*DX,600-1470*DX,600-560*DX]
 for ax,A,title in zip(axs,[B,H,H-B],['v008b terrain','v009 terrain','v009 minus v008b']):
  im=ax.imshow(A[region],extent=extent,origin='upper',cmap='coolwarm' if title=='v009 minus v008b' else 'terrain');ax.plot(q[:,0],q[:,1],lw=.45,c='black',alpha=.5);ax.set_xlim(200,395);ax.set_ylim(170,435);ax.set_title(title);fig.colorbar(im,ax=ax,shrink=.5)
 fig.savefig(out/'terrain_before_after.png',dpi=150);plt.close(fig)
 cfg=json.loads((S/'v009_geometry_spec.json').read_text(encoding='utf-8'));fig,axs=plt.subplots(2,2,figsize=(13,8),layout='constrained')
 for ax,jid in zip(axs.ravel(),['R14','R10','R07','R01']):
  p=next(x for x in cfg['profiles'] if x['id']==jid);s=np.linspace(p['lip_s']-p['face_m']-18,p['lip_s']+p['landing_m']+p['rollover_m']+18,500)
  ax.plot(s,sample(B,s),c='#999',label='v008b');ax.plot(s,sample(H,s),c='#8f3f24',label='v009');ax.set_title(p['section']+' '+p['kind']);ax.set(xlabel='Station (m)',ylabel='Ground height (m)');ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.savefig(out/'major_jump_profiles.png',dpi=150);plt.close(fig)
 info=json.loads((S/'baseline_geometry.json').read_text(encoding='utf-8'));fig,axs=plt.subplots(2,2,figsize=(13,8),layout='constrained');berm_metrics=[]
 for ax,tid in zip(axs.ravel(),['T03','T09','T10','T14']):
  t=next(x for x in info['turns'] if x['id']==tid);lat=np.linspace(-8,8,160);s=np.full(len(lat),t['mid']);b=sample(B,s,lat);a=sample(H,s,lat);ax.plot(lat,b,c='#999',label='v008b');ax.plot(lat,a,c='#8f3f24',label='v009');ax.set_title(tid+' actual apex cross-section');ax.set(xlabel='Left offset from route (m)',ylabel='Ground height (m)');ax.grid(alpha=.2);ax.legend(fontsize=8)
  sign=-np.sign(t['angle']);inside=float(sample(H,np.array([t['mid']]),-1.4*sign)[0]);outer=float(sample(H,np.array([t['mid']]),4*sign)[0]);berm_metrics.append(dict(turn=tid,outside_minus_inside_m=outer-inside))
 fig.savefig(out/'berm_cross_sections.png',dpi=150);plt.close(fig)
 # Inspect actual finite-difference changes at construction boundaries.
 mapping=json.loads((S/'section_station_map.json').read_text(encoding='utf-8'));boundaries=sorted(set(x['route_station_start_m'] for x in mapping['sections']));boundary_checks=[]
 for st in boundaries:
  s=np.linspace(st-2,st+2,33);v=sample(H,s);boundary_checks.append(dict(station_m=st,max_longitudinal_grade=float(abs(np.gradient(v,s)).max()),max_125mm_height_step=float(abs(np.diff(v)).max())))
 qa['section_boundary_checks']=boundary_checks;qa['berm_cross_sections']=berm_metrics;qa['centerline_max_longitudinal_grade']=float(abs(np.gradient(after,ss)).max());qa['native_loop_height_difference_m']=float(abs(after[0]-after[-1]));qa['visual_review']='Authoring plots, not game screenshots'
 qa['geometry_checks_pass']=bool(qa.get('new_excessive_grade_nodes',0)==0 and qa['finite'] and qa['raw_png_identical'] and qa['route_unchanged'] and qa['maximum_racing_grade']<.84 and (len(cfg['active_sections'])<11 or qa['maximum_changed_grade']<.84) and qa['outer_terrain_max_delta_m']<.001 and qa['native_loop_height_difference_m']<.001 and all(x['max_longitudinal_grade']<.84 for x in boundary_checks))
 (R/'DOCUMENTATION/v009_geometry_validation.json').write_text(json.dumps(qa,indent=2)+'\n', encoding='utf-8')
 print(json.dumps({k:qa[k] for k in ['geometry_checks_pass','maximum_raise_m','maximum_lower_m','maximum_racing_grade','centerline_max_longitudinal_grade','native_loop_height_difference_m']},indent=2))
 if not qa['geometry_checks_pass']:raise RuntimeError('Geometry QA failed')
if __name__=='__main__':main()
