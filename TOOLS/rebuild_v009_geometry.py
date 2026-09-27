#!/usr/bin/env python3
"""Deterministic v009 terrain sectors over an exact, immutable v008b baseline.

Metric dimensions are tuning estimates. Native/game QA is separate.
"""
from pathlib import Path
import json,hashlib,math,io,inspect
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import gaussian_filter,gaussian_filter1d,map_coordinates
from scipy.spatial import cKDTree
from PIL import Image
from refine_jumps import supports,envelope,add_grade_segment
R=Path(__file__).resolve().parents[1];SRC=R/'V009_SOURCE';OUT=R/'V009_OUTPUT';N=2049;SIZE=600.;SCALE=18.;DX=SIZE/(N-1)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def ease(t):
 t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
def periodic_delta(s,c,L):return (s-c+L/2)%L-L/2
def window(s,a,b,L,fade=14):
 length=(b-a)%L;u=periodic_delta(s,(a+length/2)%L,L)
 return 1-ease((abs(u)-length/2)/fade)
def make_profile(p):
 p=p.copy();F=p['face_m'];roll=p['rollover_m'];height=p['crest_height_m'];land=p['landing_m'];bridge=p['crest_bridge_m']
 # Integral of progressive grades: 0->.7G over 55%, .7G->G over 45%.
 g=height/(F*(.55*.35+.45*.85)+roll*.5)
 xs,hs,ds=[-F-3,-F],[0.,0.],[0.,0.]
 add_grade_segment(xs,hs,ds,F*.55,0,.7*g)
 add_grade_segment(xs,hs,ds,F*.45,.7*g,g)
 add_grade_segment(xs,hs,ds,roll,g,0)
 exitgrade=-.06 if bridge else 0
 if bridge:add_grade_segment(xs,hs,ds,bridge,0,exitgrade)
 entry=min(4.,land*.20);runout=min(7.,land*.32);flat=land-entry-runout
 down=(hs[-1]+exitgrade*entry/2)/(flat+(entry+runout)/2)
 add_grade_segment(xs,hs,ds,entry,exitgrade,-down)
 add_grade_segment(xs,hs,ds,flat,-down,-down)
 add_grade_segment(xs,hs,ds,runout,-down,0);hs[-1]=0.
 add_grade_segment(xs,hs,ds,3,0,0)
 p.update(profile_s=xs,profile_h=hs,profile_derivative=ds,takeoff_angle_deg=math.degrees(math.atan(g)),maximum_designed_landing_grade=down,status='Video-guided authoring estimate; ride test pending')
 return p

def generate_target(spec,base,q,w,info):
 L=q[-1,3];profiles=[make_profile(p) for p in spec['profiles']]
 old=json.loads((SRC/'baseline_jump_profiles.json').read_text());olds=supports(old,q,w);news=supports(profiles,q,w)
 tree=cKDTree(q[:-1,:2]);axes=np.linspace(0,SIZE,N)
 regs=np.linspace(0,L,round(L/.4)+1);regth=np.unwrap(np.interp(regs,q[:,3],q[:,2]));kk=gaussian_filter1d(np.gradient(regth,regs),3/.4,mode='nearest')
 target=base.copy();stations=np.zeros_like(base);lateral=np.zeros_like(base);distance=np.zeros_like(base);widths=np.zeros_like(base);ewidth=np.zeros_like(base)
 lookup={x['id']:x for x in spec['berms']}
 for row in range(0,N,64):
  zz,xx=np.meshgrid(SIZE-axes[row:row+64],axes,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()];dist,ind=tree.query(pts,workers=2)
  th=q[ind,2];dv=pts-q[ind,:2];lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th);along=dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th);s=(q[ind,3]+along)%L;wi=w[ind]
  delta=envelope(pts,news)-envelope(pts,olds);newjump=envelope(pts,news)
  curvature=np.interp(s,regs,kk);out=-np.sign(curvature)*lat;strength=smooth((abs(curvature)-.009)/.045)
  oldbank=(.95+.20*np.sin(s/95)**2)*strength*smooth((out+.6)/(wi/2+.6))*(1-smooth((out-wi/2)/6))
  bank=np.zeros_like(s);chop=np.zeros_like(s);effective=np.full_like(s,8.6);bankload=np.zeros_like(s)
  for turn in info['turns']:
   dd=periodic_delta(s,turn['mid'],L);extent=(turn['arc_end']-turn['arc_start'])/2;cfg=lookup[turn['id']];fade=ease((dd+extent+16)/18)*(1-ease((dd-extent+3)/18));out=-np.sign(turn['angle'])*lat;half=cfg['effective_width_m']/2
   # Two/three shallow grooves and an asymmetric broad raised outside half.
   wall=cfg['outer_rise_m']*ease((out+1.5)/(half+1.5))*(1-ease((out-half)/5.5))
   groove=np.zeros_like(s)
   for off,depth,sig in [(-1.4,1.,.55),(.65,.8,.55),(2.55,.55,.65)]:groove+=depth*np.exp(-((out-off-.13*np.sin(dd/12))/sig)**2)
   wall-=cfg['rut_depth_m']*groove
   bank+=fade*wall;bankload=np.maximum(bankload,fade);effective+=(cfg['effective_width_m']-8.6)*fade
   entry=np.exp(-((dd+extent+8)/15)**4);exit=np.exp(-((dd-extent-5)/13)**4)
   chop+=spec['continuous_relief']['braking_chop_amplitude_m']*(entry*np.sin(2*np.pi*s/3.4)+.75*exit*np.sin(2*np.pi*s/4.7))
   # Remove the broad legacy raised corner platforms, not the surrounding ground.
   if turn['id']=='T02':oldbank+=1.20*np.exp(-(dd/24)**4)*(1-smooth((abs(lat)-wi/2)/7))
   if turn['id']=='T05':oldbank+=.45*np.exp(-((dd-9)/27)**4)*(1-smooth((abs(lat)-wi/2)/7))
   if turn['id']=='T06':oldbank+=.30*np.exp(-(dd/20)**4)*(1-smooth((abs(lat)-wi/2)/7))
  # Core lateral fade ends before neighboring lane bisectors. Jump support uses
  # each obstacle's own local corridor above, preventing nearest-lane cliff cuts.
  core=1-ease((abs(lat)-effective/2+.3)/2.0)
  relief=spec['continuous_relief'];wave=relief['long_wave_amplitude_m']*np.sin(2*np.pi*23*s/L)+relief['short_wave_amplitude_m']*np.sin(2*np.pi*57*s/L+.6)
  wave*=1-ease(newjump/.7);wave*=1-.4*bankload
  seam_guard=ease(np.minimum(s,L-s)/28) # smooth native start/finish join
  grooves=-.025*(1-bankload)*(np.exp(-((lat-1.25-.18*np.sin(s/19))/.52)**2)+np.exp(-((lat+1.4-.15*np.sin(s/17))/.60)**2))
  delta+=bank-oldbank+(wave+chop+grooves)*core*seam_guard
  # Retain peripheral map, paddock and non-course scenery terrain exactly.
  support=1-ease((dist-wi/2-7)/1.5);delta*=support
  shape=xx.shape;sl=slice(row,row+len(xx));target[sl]+=delta.reshape(shape)
  stations[sl]=s.reshape(shape);lateral[sl]=lat.reshape(shape);distance[sl]=dist.reshape(shape);widths[sl]=wi.reshape(shape);ewidth[sl]=effective.reshape(shape)
  if row%512==0:print('v009 target row',row,flush=True)
 # Smooth sub-grid projection/quantization artifacts, then relax only steep
 # changed terrain. Full-map base and protected outside nodes remain untouched.
 changed=(gaussian_filter((np.abs(target-base)>1e-6).astype(np.float32),1.5)>.002)&(distance<widths/2+8.5)
 sm=gaussian_filter(target-base,.65);target=base+np.where(changed,sm,0)
 before=target.copy();passes=0
 for _ in range(80):
  gy,gx=np.gradient(target,DX);bad=(np.hypot(gx,gy)>.78)&changed
  if not bad.any():break
  weight=np.clip(gaussian_filter(bad.astype(np.float32),1.2)*7,0,1)*changed
  target=target*(1-weight)+gaussian_filter(target,1.8)*weight;passes+=1
 print('Target grade relaxation passes',passes,flush=True)
 return dict(target=target.astype(np.float32),station=stations.astype(np.float32),lat=lateral.astype(np.float32),distance=distance.astype(np.float32),width=widths.astype(np.float32),effective_width=ewidth.astype(np.float32),profiles=profiles,relaxation=dict(passes=passes,max_adjustment_m=float(abs(target-before).max())))

def main():
 OUT.mkdir(exist_ok=True);spec=json.loads((SRC/'v009_geometry_spec.json').read_text());manifest=json.loads((SRC/'baseline_manifest.json').read_text());rawpath=R/'BUILD/v009_baseline/terrain.raw'
 assert digest(rawpath)==manifest['terrain_sha256'],'Exact v008b baseline required; run materialize_v009_baseline.py'
 base=np.fromfile(rawpath,dtype='<u2').reshape(N,N).astype(np.float32)/65535*SCALE;d=np.load(SRC/'baseline_route.npz');q=d['q'];w=d['width'];info=json.loads((SRC/'baseline_geometry.json').read_text());L=q[-1,3]
 cache=R/'BUILD/v009_cache';cache.mkdir(exist_ok=True);structural={k:v for k,v in spec.items() if k!='active_sections'}
 key=hashlib.sha256(json.dumps(structural,sort_keys=True).encode()+''.join(inspect.getsource(f) for f in [generate_target,make_profile,smooth,ease,periodic_delta]).encode()+(R/'TOOLS/refine_jumps.py').read_bytes()+rawpath.read_bytes()).hexdigest();npz=cache/(key+'.npz');meta=cache/(key+'.json')
 if npz.exists():
  with np.load(npz) as f:fields={k:f[k] for k in f.files}
  fields.update(json.loads(meta.read_text()))
 else:
  fields=generate_target(spec,base,q,w,info);arrays={k:v for k,v in fields.items() if isinstance(v,np.ndarray)};np.savez_compressed(npz,**arrays);meta.write_text(json.dumps({k:v for k,v in fields.items() if k not in arrays}))
 data=json.loads((SRC/'section_station_map.json').read_text());blend=np.zeros_like(base)
 for sec in data['sections']:
  if sec['section_id'] in spec['active_sections']:
   blend=np.maximum(blend,window(fields['station'],sec['route_station_start_m'],sec['route_station_end_m'],L))
 blend=gaussian_filter(blend,4.0)
 H=base+(fields['target']-base)*blend;encoded=np.round(H/SCALE*65535).astype('<u2');H=encoded.astype(np.float32)/65535*SCALE
 assert np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
 encoded.tofile(OUT/'terrain.raw');Image.fromarray(encoded).save(OUT/'terrain_16bit.png');np.save(OUT/'height_metres.npy',H)
 coords=[(SIZE-q[:,1])/SIZE*(N-1),q[:,0]/SIZE*(N-1)];elev=map_coordinates(H,coords,order=1)
 np.savetxt(OUT/'centerline_elevation.csv',np.c_[q[:,3],elev],delimiter=',',header='station_m,height_m',comments='')
 (OUT/'jump_profiles.json').write_text(json.dumps(fields['profiles'],indent=2)+'\n')
 delta=H-base;gy,gx=np.gradient(H,DX);grade=np.hypot(gx,gy);changed=abs(delta)>SCALE/65535*1.1;racing=fields['distance']<fields['effective_width']/2
 by,bx=np.gradient(base,DX);baseline_grade=np.hypot(bx,by);new_spikes=int(((grade>.84)&(grade>baseline_grade+.05)&changed).sum())
 qa=dict(new_excessive_grade_nodes=new_spikes,version='v009',active_sections=spec['active_sections'],native_compilation=False,in_game_riding=False,raw_sha256=digest(OUT/'terrain.raw'),height_range_m=[float(H.min()),float(H.max())],maximum_raise_m=float(delta.max()),maximum_lower_m=float(-delta.min()),maximum_changed_grade=float(grade[changed].max()),maximum_racing_grade=float(grade[racing].max()),changed_nodes=int(changed.sum()),relaxation=fields['relaxation'],finite=bool(np.isfinite(H).all()),raw_bytes=(OUT/'terrain.raw').stat().st_size,raw_png_identical=bool(np.array_equal(encoded,np.array(Image.open(OUT/'terrain_16bit.png')))),outer_terrain_max_delta_m=float(abs(delta[fields['distance']>fields['width']/2+9]).max()),route_unchanged=digest(SRC/'baseline_route.npz')==manifest['route_sha256'],loop_closure_m=float(np.linalg.norm(q[0,:2]-q[-1,:2])),effective_width_range_m=[float(fields['effective_width'][racing].min()),float(fields['effective_width'][racing].max())])
 (R/'DOCUMENTATION/v009_geometry_validation.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps(qa,indent=2),flush=True)
 # Retain compact cache fields for QA; this file is a generated product.
 temporary=OUT/'qa_fields.npz.tmp'
 with temporary.open('wb') as fp:np.savez_compressed(fp,station=fields['station'],lat=fields['lat'],distance=fields['distance'],width=fields['width'],effective_width=fields['effective_width'])
 import zipfile
 with zipfile.ZipFile(temporary) as z:
  if z.testzip() is not None:raise RuntimeError('Incomplete generated QA field archive')
 temporary.replace(OUT/'qa_fields.npz')
 if qa['maximum_racing_grade']>.84 or new_spikes or (len(spec['active_sections'])==11 and qa['maximum_changed_grade']>.84):raise RuntimeError('Excessive grade; inspect geometry before native build')
 if qa['outer_terrain_max_delta_m']>.001:raise RuntimeError('Terrain outside corridor changed')
if __name__=='__main__':main()
