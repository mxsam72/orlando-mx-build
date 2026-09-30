#!/usr/bin/env python3
"""Deterministic v015 terrain sectors over an exact, immutable v008b baseline.

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
R=Path(__file__).resolve().parents[1];SRC=R/'V015_SOURCE';BASE_SRC=R/'V009_SOURCE';OUT=R/'V015_OUTPUT';N=2049;SIZE=600.;SCALE=18.;DX=SIZE/(N-1)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def ease(t):
 t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
def periodic_delta(s,c,L):return (s-c+L/2)%L-L/2
def window(s,a,b,L,fade=14):
 length=(b-a)%L;u=periodic_delta(s,(a+length/2)%L,L)
 return 1-ease((abs(u)-length/2)/fade)
from jump_v015 import make_profile, envelope
from refine_jumps import envelope as legacy_envelope

def generate_target(spec,base,q,w,info):
 L=q[-1,3];profiles=[make_profile(p) for p in spec['profiles']]
 old=json.loads((BASE_SRC/'baseline_jump_profiles.json').read_text(encoding='utf-8'));olds=supports(old,q,w);news=supports(profiles,q,w)
 tree=cKDTree(q[:-1,:2]);axes=np.linspace(0,SIZE,N)
 regs=np.linspace(0,L,round(L/.4)+1);regth=np.unwrap(np.interp(regs,q[:,3],q[:,2]));kk=gaussian_filter1d(np.gradient(regth,regs),3/.4,mode='nearest')
 target=base.copy();stations=np.zeros_like(base);lateral=np.zeros_like(base);distance=np.zeros_like(base);widths=np.zeros_like(base);ewidth=np.zeros_like(base)
 lookup={x['id']:x for x in spec['berms']}
 assert not any(x['enabled'] for x in spec.get('provisional_features',[])), 'Provisional rises need explicit authored profiles before enabling'
 for row in range(0,N,64):
  zz,xx=np.meshgrid(SIZE-axes[row:row+64],axes,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()];dist,ind=tree.query(pts,workers=2)
  th=q[ind,2];dv=pts-q[ind,:2];lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th);along=dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th);s=(q[ind,3]+along)%L;wi=w[ind]
  delta=envelope(pts,news)-legacy_envelope(pts,olds);newjump=envelope(pts,news)
  curvature=np.interp(s,regs,kk);out=-np.sign(curvature)*lat;strength=smooth((abs(curvature)-.009)/.045)
  oldbank=(.95+.20*np.sin(s/95)**2)*strength*smooth((out+.6)/(wi/2+.6))*(1-smooth((out-wi/2)/6))
  bank=np.zeros_like(s);chop=np.zeros_like(s);legacy_rut=np.zeros_like(s);effective=np.full_like(s,8.6);bankload=np.zeros_like(s)
  for turn in info['turns']:
   dd=periodic_delta(s,turn['mid'],L);extent=(turn['arc_end']-turn['arc_start'])/2;cfg=lookup[turn['id']];fade=ease((dd+extent+16)/18)*(1-ease((dd-extent+3)/18));out=-np.sign(turn['angle'])*lat;half=cfg['effective_width_m']/2
   # Remove the original v006 corner-groove recipe before authoring paths.
   oldfade=smooth((dd+extent+10)/12)*(1-smooth((dd-extent+2)/12))
   corridor=1-smooth((dist-wi/2+.15)/1.3)
   legacy_rut=np.maximum(legacy_rut,(np.exp(-((out-1.6-.35*np.sin(dd/13))/.55)**2)+.6*np.exp(-((out+1.5)/.7)**2))*oldfade*corridor)
   # Independent entry/apex/exit load and line trajectories; pocket is carved
   # relative to the surrounding ground rather than elevating the whole floor.
   phase=np.clip((dd+extent)/(2*extent),0,1)
   peak=np.exp(-((dd-cfg['apex_shift_m'])/max(extent*.75,9))**2)
   load=(cfg['entry_load']*(1-phase)+cfg['exit_load']*phase)*(.62+.38*peak)
   wall=cfg['outer_rise_m']*load*ease((out+.9)/(half+.9))*(1-ease((out-half)/5.5))
   pocket=cfg['pocket_depth_m']*peak*np.exp(-((out+.25)/2.2)**2)
   groove=np.zeros_like(s)
   for path in cfg['rut_paths']:
    pos=np.where(phase<.5,path['entry_out_m']+(path['apex_out_m']-path['entry_out_m'])*ease(2*phase),path['apex_out_m']+(path['exit_out_m']-path['apex_out_m'])*ease(2*phase-1))
    groove+=path['depth_scale']*(.25+.75*peak)*np.exp(-((out-pos)/path['width_m'])**2)
   wall-=pocket+cfg['rut_depth_m']*groove
   bank+=fade*wall;bankload=np.maximum(bankload,fade);effective+=(cfg['effective_width_m']-8.6)*fade
   entry=np.exp(-((dd+extent+8)/13)**4);exit=np.exp(-((dd-extent-5)/10)**4)
   # Broken, localized braking/drive bumps; no whole-lap repeating wave.
   bump=np.sin(2*np.pi*(dd+extent)/cfg['braking_spacing_m'])
   chop+=spec['continuous_relief']['braking_chop_amplitude_m']*(entry*bump+.6*exit*np.sin(2*np.pi*dd/4.9))
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
  grooves=np.zeros_like(s)
  delta+=bank-oldbank+.045*np.minimum(legacy_rut,1)*corridor+(wave+chop+grooves)*core*seam_guard
  # Retain peripheral map, paddock and non-course scenery terrain exactly.
  # R07 is now +5 m taller while explicitly 5% less steep on the face.  Its
  # large ant-hill needs a wider LOCAL shoulder so the extra height does not
  # terminate in an artificial side cliff.  All other sections keep the
  # established 7 m peripheral protection.
  r07=next(p for p in spec['profiles'] if p['id']=='R07')
  r07mid=(r07['station_start_m']+r07['station_end_m'])/2
  r07half=(r07['station_end_m']-r07['station_start_m'])/2+8
  r07zone=(abs(periodic_delta(s,r07mid,L))<r07half)
  support_extra=np.where(r07zone,r07.get('wide_support_extra_m',7.0),7.0)
  support=1-ease((dist-wi/2-support_extra)/1.5);delta*=support
  shape=xx.shape;sl=slice(row,row+len(xx));target[sl]+=delta.reshape(shape)
  stations[sl]=s.reshape(shape);lateral[sl]=lat.reshape(shape);distance[sl]=dist.reshape(shape);widths[sl]=wi.reshape(shape);ewidth[sl]=effective.reshape(shape)
  if row%512==0:print('v015 target row',row,flush=True)
 # The immutable base contains a legacy flattening edge at s21 inside the
 # extended R01 deck. Grade actual tabletop decks to an endpoint plane instead
 # of inheriting that buried ledge. Keep lip/landing joins and lateral shoulders.
 for p in profiles:
  if p['kind'] not in ['tabletop','table_single']:continue
  a=p['lip_s']+p['landmarks_m']['deck_start'];b=p['lip_s']+p['landmarks_m']['deck_end']
  ss=np.linspace(a,b,max(50,int((b-a)/.15)));qq=ss%L
  coords=[(SIZE-np.interp(qq,q[:,3],q[:,1]))/DX,np.interp(qq,q[:,3],q[:,0])/DX]
  hh=map_coordinates(target,coords,order=1);plane=np.interp(ss,[a,b],[hh[0],hh[-1]])
  correction=np.interp(stations,ss,plane-hh,left=0,right=0)
  fade=ease((stations-a)/1.2)*(1-ease((stations-b+1.2)/1.2))
  side=1-smooth((abs(lateral)-p['racing_width_m']/2)/p['side_taper_m'])
  target+=correction*fade*side*(distance<widths/2+8.5)
 # Smooth sub-grid projection/quantization artifacts, then relax only steep
 # changed terrain. Full-map base and protected outside nodes remain untouched.
 r07=next(p for p in spec['profiles'] if p['id']=='R07');r07mid=(r07['station_start_m']+r07['station_end_m'])/2;r07half=(r07['station_end_m']-r07['station_start_m'])/2+8
 r07wide=(abs(periodic_delta(stations,r07mid,L))<r07half)&(distance<widths/2+r07.get('wide_support_extra_m',7.0)+1.5)
 changed=(gaussian_filter((np.abs(target-base)>1e-6).astype(np.float32),1.5)>.002)&((distance<widths/2+8.5)|r07wide)
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
 OUT.mkdir(exist_ok=True);spec=json.loads((SRC/'v015_geometry_spec.json').read_text(encoding='utf-8'));manifest=json.loads((BASE_SRC/'baseline_manifest.json').read_text(encoding='utf-8'));rawpath=R/'BUILD/v009_baseline/terrain.raw'
 assert digest(rawpath)==manifest['terrain_sha256'],'Exact v008b baseline required; run materialize_v015_baseline.py'
 base=np.fromfile(rawpath,dtype='<u2').reshape(N,N).astype(np.float32)/65535*SCALE;d=np.load(BASE_SRC/'baseline_route.npz');q=d['q'];w=d['width'];info=json.loads((BASE_SRC/'baseline_geometry.json').read_text(encoding='utf-8'));L=q[-1,3]
 cache=R/'BUILD/v015_cache';cache.mkdir(exist_ok=True);structural={k:v for k,v in spec.items() if k!='active_sections'}
 key=hashlib.sha256(json.dumps(structural,sort_keys=True).encode()+''.join(inspect.getsource(f) for f in [generate_target,make_profile,envelope,smooth,ease,periodic_delta]).encode()+(R/'TOOLS/refine_jumps.py').read_bytes()+rawpath.read_bytes()).hexdigest();npz=cache/(key+'.npz');meta=cache/(key+'.json')
 if npz.exists():
  with np.load(npz) as f:fields={k:f[k] for k in f.files}
  fields.update(json.loads(meta.read_text(encoding='utf-8')))
 else:
  fields=generate_target(spec,base,q,w,info);arrays={k:v for k,v in fields.items() if isinstance(v,np.ndarray)};np.savez_compressed(npz,**arrays);meta.write_text(json.dumps({k:v for k,v in fields.items() if k not in arrays}), encoding='utf-8')
 data=json.loads((BASE_SRC/'section_station_map.json').read_text(encoding='utf-8'));blend=np.zeros_like(base)
 for sec in data['sections']:
  if sec['section_id'] in spec['active_sections']:
   blend=np.maximum(blend,window(fields['station'],sec['route_station_start_m'],sec['route_station_end_m'],L))
 blend=gaussian_filter(blend,4.0)
 H=base+(fields['target']-base)*blend;encoded=np.round(H/SCALE*65535).astype('<u2');H=encoded.astype(np.float32)/65535*SCALE
 assert np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
 encoded.tofile(OUT/'main_terrain.raw');Image.fromarray(encoded).save(OUT/'main_terrain_16bit.png');np.save(OUT/'height_metres.npy',H)
 coords=[(SIZE-q[:,1])/SIZE*(N-1),q[:,0]/SIZE*(N-1)];elev=map_coordinates(H,coords,order=1)
 np.savetxt(OUT/'centerline_elevation.csv',np.c_[q[:,3],elev],delimiter=',',header='station_m,height_m',comments='')
 (OUT/'jump_profiles.json').write_text(json.dumps(fields['profiles'],indent=2)+'\n', encoding='utf-8')
 delta=H-base;gy,gx=np.gradient(H,DX);grade=np.hypot(gx,gy);changed=abs(delta)>SCALE/65535*1.1;racing=fields['distance']<fields['effective_width']/2
 by,bx=np.gradient(base,DX);baseline_grade=np.hypot(bx,by)
 spike_mask=(grade>.84)&(grade>baseline_grade+.05)&changed
 new_spikes=int(spike_mask.sum())
 # The +5 m R07 ant-hill is intentionally much taller than prior terrain.  Its
 # off-track side embankments can exceed the normal riding-surface grade even
 # when the actual lane is safe.  Keep a separate ridable-corridor spike gate
 # rather than rejecting the build for non-riding jump sides.
 ridable=fields['distance']<fields['effective_width']/2+1.5
 new_spikes_ridable=int((spike_mask&ridable).sum())
 r07=next(p for p in spec['profiles'] if p['id']=='R07');r07mid=(r07['station_start_m']+r07['station_end_m'])/2;r07half=(r07['station_end_m']-r07['station_start_m'])/2+8
 outer_mask=(fields['distance']>fields['width']/2+9)&~((abs(periodic_delta(fields['station'],r07mid,L))<r07half)&(fields['distance']<fields['width']/2+r07.get('wide_support_extra_m',7.0)+2))
 qa=dict(new_excessive_grade_nodes=new_spikes,new_excessive_grade_nodes_ridable=new_spikes_ridable,version='v015',active_sections=spec['active_sections'],native_compilation=False,in_game_riding=False,raw_sha256=digest(OUT/'main_terrain.raw'),height_range_m=[float(H.min()),float(H.max())],maximum_raise_m=float(delta.max()),maximum_lower_m=float(-delta.min()),maximum_changed_grade=float(grade[changed].max()),maximum_racing_grade=float(grade[racing].max()),changed_nodes=int(changed.sum()),relaxation=fields['relaxation'],finite=bool(np.isfinite(H).all()),raw_bytes=(OUT/'main_terrain.raw').stat().st_size,raw_png_identical=bool(np.array_equal(encoded,np.array(Image.open(OUT/'main_terrain_16bit.png')))),outer_terrain_max_delta_m=float(abs(delta[outer_mask]).max()) if outer_mask.any() else 0.0,route_unchanged=digest(BASE_SRC/'baseline_route.npz')==manifest['route_sha256'],loop_closure_m=float(np.linalg.norm(q[0,:2]-q[-1,:2])),effective_width_range_m=[float(fields['effective_width'][racing].min()),float(fields['effective_width'][racing].max())])
 (R/'DOCUMENTATION/v015_geometry_validation.json').write_text(json.dumps(qa,indent=2)+'\n', encoding='utf-8');print(json.dumps(qa,indent=2),flush=True)
 # Retain compact cache fields for QA; this file is a generated product.
 temporary=OUT/'qa_fields.npz.tmp'
 with temporary.open('wb') as fp:np.savez_compressed(fp,station=fields['station'],lat=fields['lat'],distance=fields['distance'],width=fields['width'],effective_width=fields['effective_width'])
 import zipfile
 with zipfile.ZipFile(temporary) as z:
  if z.testzip() is not None:raise RuntimeError('Incomplete generated QA field archive')
 temporary.replace(OUT/'qa_fields.npz')
 if qa['maximum_racing_grade']>.84 or new_spikes_ridable or qa['maximum_changed_grade']>2.6:raise RuntimeError('Excessive grade on riding corridor or implausible off-track side slope; inspect geometry before native build')
 if qa['outer_terrain_max_delta_m']>.001:raise RuntimeError('Terrain outside corridor changed')
if __name__=='__main__':main()
