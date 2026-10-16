"""Three real material trials on v061 geometry, preserving the wall roller.

Replace the v060 crosswise normal stripes. Keep photographic grain in the
colour slots, with larger-scale contrast in the existing packed-soil mask.
"""
import gc,json,os,re
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates,gaussian_filter
from scipy.spatial import cKDTree
from v061_inputs import R,O as BASE,source as baseline,sha,save
from v054_previews import Terrain
from v048_surface import normal_map,smooth
from v049_previews import layers

O=R/'V062_OUTPUT';S=R/'V062_SOURCE';CACHE=R/'BUILD/v062_cache'
METHODS={
 'A':dict(title='A - Deep tilled loam',description='Heavy, irregular clods through corners; short broken cultivation on faces. No crosswise tractor comb.',wear=.66),
 'B':dict(title='B - Flowing cultivation',description='Irregularly spaced curved grooves follow the riding line through corners and lengthwise up jump faces.',wear=.66),
 'C':dict(title='C - Ridden loam',description='Broken wheel ruts through mixed loose loam, with churned shoulders and stronger shape cues at distance.',wear=.62),
}

def source(name,method='A'):
 p=O/method/'materials'/name
 return p if p.is_file() else baseline(name)

def noise(x,z,scale,seed):
 xx=x/scale;zz=z/scale;ix=np.floor(xx);iz=np.floor(zz);fx=xx-ix;fz=zz-iz
 fx=fx*fx*fx*(10+fx*(-15+6*fx));fz=fz*fz*fz*(10+fz*(-15+6*fz))
 def h(a,b):return np.mod(np.sin(a*127.1+b*311.7+seed*74.7)*43758.5453123,1)
 return ((1-fx)*h(ix,iz)+fx*h(ix+1,iz))*(1-fz)+((1-fx)*h(ix,iz+1)+fx*h(ix+1,iz+1))*fz

class Circuit:
 def __init__(self):
  self.route=dict(np.load(BASE/'route.npz'));self.q=self.route['q'];self.p=self.q[:,:2];self.length=float(self.q[-1,3]);self.v=np.c_[np.cos(self.q[:,2]),np.sin(self.q[:,2])]
  self.curve=CubicSpline(self.q[:,3],self.p,bc_type='periodic');self.tree=cKDTree(self.p[:-1]);self.terrain=Terrain(BASE/'terrain.raw')
  self.start=self.route['start'];self.start_tree=cKDTree(self.start[:,:2]);self.start_v=np.c_[np.cos(self.start[:,2]),np.sin(self.start[:,2])]
  self.start_knots=np.asarray(json.loads((BASE/'layout.json').read_text())['start_width_knots'])
  self.dirt=np.asarray(Image.open(baseline('mask_v046_section.tga')).getchannel('A'),np.float32)/255
  self.profiles=json.loads((BASE/'jump_profiles.json').read_text());self.bounds=np.r_[self.p,self.start[:,:2]]
  self.tines=[];rng=np.random.default_rng(620151);p=-11.
  while p<11:
   self.tines.append((p,float(rng.uniform(.095,.145)),float(rng.uniform(.045,.075)),float(rng.uniform(0,6.28))));p+=rng.uniform(.39,.61)
 def slope(self,x,z):return self.terrain.slope(x,z)
 def coords(self,x,z):
  shape=x.shape;pos=np.c_[x.ravel(),z.ravel()];_,idx=self.tree.query(pos,workers=2);s=self.q[idx,3].copy()
  # Continuous curve projection prevents nearest-sample seams in turn grooves.
  for _ in range(3):
   p=self.curve(s);v=self.curve(s,1);a=self.curve(s,2);delta=pos-p;den=(v*v).sum(1)-(delta*a).sum(1)
   step=np.where(den>.12,np.sum(delta*v,axis=1)/np.maximum(den,.12),0);s=np.mod(s+np.clip(step,-.6,.6),self.length)
  p=self.curve(s);v=self.curve(s,1);v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-9);delta=pos-p
  l=delta[:,0]*-v[:,1]+delta[:,1]*v[:,0]
  return s.reshape(shape),l.reshape(shape)
 def common(self,x,z):
  s,l=self.coords(x,z);pos=np.c_[x.ravel(),z.ravel()];dm,_=self.tree.query(pos,workers=2);ds,ii=self.start_tree.query(pos,workers=2)
  start=(ds+1<dm)&(ds<24);sv=self.start_v[ii];delta=pos-self.start[ii,:2]
  ss=self.start[ii,3]+np.sum(delta*sv,axis=1);sl=delta[:,0]*-sv[:,1]+delta[:,1]*sv[:,0]
  half=np.interp(s,self.q[:,3],self.route['width'])/2
  half=np.where(start.reshape(x.shape),np.interp(ss,self.start_knots[:,0],self.start_knots[:,1]).reshape(x.shape)/2,half)
  s=np.where(start.reshape(x.shape),ss.reshape(x.shape)+self.length+20,s);l=np.where(start.reshape(x.shape),sl.reshape(x.shape),l)
  d=self.dirt;n=len(d);scope=map_coordinates(d,[(600-z)/600*n-.5,x/600*n-.5],order=1,mode='nearest')
  scope*=np.minimum(dm,ds).reshape(x.shape)<24
  if np.any(start):
   main_s=np.mod(s,self.length)
  else:main_s=s
  a=self.curve(main_s,2);vv=self.curve(main_s,1);curv=np.abs(vv[:,:,0]*a[:,:,1]-vv[:,:,1]*a[:,:,0])/np.maximum(np.linalg.norm(vv,axis=2)**3,1e-8)
  corner=smooth((curv-.012)/.035);corner=np.where(start.reshape(x.shape),0,corner)
  hx,hz=self.slope(x,z);tx=np.interp(main_s,self.q[:,3],self.v[:,0]);tz=np.interp(main_s,self.q[:,3],self.v[:,1]);face=smooth((abs(hx*tx+hz*tz)-.07)/.18)
  core=1-smooth((abs(l)-half+.5)/1.8);shoulder=1-core
  return dict(s=s,l=l,half=half,scope=scope,corner=corner,face=face,core=core,shoulder=shoulder,
   n0=noise(x,z,.27,13),n1=noise(x,z,.56,41),n2=noise(x,z,1.25,62),n3=noise(x,z,3.7,19),n4=noise(x,z,9.2,87))
 def fields(self,x,z,f,method):
  s,l=f['s'],f['l'];core=f['core'];n0,n1,n2,n3,n4=[f['n'+str(i)] for i in range(5)]
  clod=np.maximum(0,.64*n0+.36*n1-.35)**1.45*3.4
  crumb=(n0-.5)*.010+(n1-.5)*.014
  till=clod*.064+crumb;groove=np.zeros_like(s);ridge=np.zeros_like(s)
  if method=='A':
   relief=till*(.86+.74*f['corner']+.30*f['shoulder'])
   # Faces retain broken lengthwise scratching; corners remain churned clods.
   activity=(1-f['corner'])*f['face']*core
   for center,width,depth,seed in self.tines:
    u=(l-center-.025*np.sin(s*.11+seed))/width;g=np.exp(-u*u)*(0.18+.82*smooth((noise(x+seed,z,2.5,31)-.36)/.4))
    relief-=g*.027*activity;groove+=g*activity
  elif method=='B':
   relief=till*.60
   for center,width,depth,seed in self.tines:
    u=(l-center-.025*np.sin(s*.12+seed))/width;g=np.exp(-u*u);r=np.exp(-((u-1.65)/1.05)**2)
    activity=(.76+.24*noise(x+seed,z,3.7,11))*core
    relief+=(-g+.38*r)*depth*activity;groove+=g*activity;ridge+=r*activity
  else:
   relief=till*(.83+.65*f['shoulder']+.20*f['corner'])
   for i,center in enumerate([-4.5,-2.75,-.85,1.2,3.2,4.9]):
    seed=i*1.77;centre=center+.10*np.sin(s*.10+seed)+.035*np.sin(s*.31+seed)
    width=.15+.055*np.sin(i*1.9)**2;u=(l-centre)/width
    activity=smooth((noise(s+seed*19,l*.24,4.8,73)-.29)/.4)*core
    g=np.exp(-u*u)*activity;r=np.exp(-((u-1.6)/.95)**2)*activity
    relief+=(-g+.36*r)*(.061+.018*f['corner']);groove+=g;ridge+=r
  # Albedo varies at clod/patch scale to survive the loss of fine detail in mips.
  dark=np.clip((.44-n1)*1.4,0,.38)
  variation=(n3-.5)*.28+(n2-.5)*.18+(n4-.5)*.13+(clod-.40)*.105-dark*.30
  variation-=groove*(.10 if method=='B' else .13);variation+=ridge*.028
  variation+=f['shoulder']*.065
  if method=='A':variation+=(n1-.5)*.11
  factor=np.clip(1+variation,.63,1.38)
  rgb=np.array([107.45,96.81,77.44])*factor[:,:,None]
  return relief,rgb

def write_image(a,p):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.stem+'.writing.tga');Image.fromarray(a).save(tmp);tmp.replace(p);os.utime(p,None)

def geometry():
 paths=[]
 for method in METHODS:
  out=O/method;out.mkdir(parents=True,exist_ok=True);(out/'materials').mkdir(exist_ok=True)
  for name in ['terrain.raw','scenery.fbx','route.npz','jump_profiles.json','layout.json','main.tcl','start.tcl']:
   p=out/name
   if not p.exists():os.link(BASE/name,p)
   assert sha(p)==sha(BASE/name)
  text=(BASE/'compiled_track.hmf').read_text()
  # Keep the detailed photographic colour at the accepted 3m repeat.
  assert len(list(layers(text)))==14;(out/'compiled_track.hmf').write_text(text,newline='\n')
  (out/'materials/v044_route_detail.shd').write_text(baseline('v044_route_detail.shd').read_text(),newline='\n')
  old=(R/'BUILD/v062_inputs/baseline_v060.amb').read_text();new=old.replace('red = 0.44\n green = 0.49\n blue = 0.56','red = 0.30\n green = 0.34\n blue = 0.40').replace('density = 0.00030','density = 0.00018')
  assert new!=old and new.split('clear')[0]==old.split('clear')[0]
  (out/'trial_daylight.amb').write_text(new,newline='\n')
  paths.append(dict(method=method,terrain_sha256=sha(out/'terrain.raw'),scenery_sha256=sha(out/'scenery.fbx')))
 return paths

def author(c):
 # Three 8K normal arrays, one source. This adds no images to any candidate.
 old=np.array(Image.open(baseline('v044_route_detail_n.tga')));normal={m:old.copy() for m in METHODS};n=len(old);dx=600/n
 minimum=c.bounds.min(0)-25;maximum=c.bounds.max(0)+25
 x0=max(1,int(minimum[0]/dx));x1=min(n-1,int(maximum[0]/dx)+1);y0=max(1,int((600-maximum[1])/dx));y1=min(n-1,int((600-minimum[1])/dx)+1)
 changed={m:0 for m in METHODS};outside={m:0 for m in METHODS}
 for row in range(y0,y1,96):
  end=min(row+96,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-1,end+1)+.5)*dx);f=c.common(x,z);w=f['scope'][1:-1]
  for m in METHODS:
   relief,_=c.fields(x,z,f,m);nn=normal_map(c,x,z,relief,dx)[1:-1]/127.5-1;base=old[row:end,x0:x1,:3]/127.5-1
   v=base*(1-w[:,:,None])+nn*w[:,:,None];v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-8);new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)))
   active=w>0;new=np.where(active[:,:,None],new,old[row:end,x0:x1,:3]);diff=np.any(new!=old[row:end,x0:x1,:3],axis=2)
   assert not np.any(diff&~active);normal[m][row:end,x0:x1,:3]=new;changed[m]+=int(diff.sum())
  if (row-y0)//96%8==0:print('Normal trial rows',row,'/',y1,flush=True)
 for m in METHODS:
  assert np.array_equal(normal[m][:,:,3],old[:,:,3]);write_image(normal[m],O/m/'materials/v044_route_detail_n.tga')
 del old,normal;gc.collect()
 return changed

def contrast(c):
 """Keep fine photographs crisp; use the existing packed mask for macro tone."""
 photo=np.asarray(Image.open(baseline('v045_loose.tga')),np.float32);soft=gaussian_filter(photo,(10,10,0),mode='wrap');crisp=np.uint8(np.rint(np.clip(soft+(photo-soft)*1.22,8,235)))
 packed=np.asarray(Image.open(baseline('v045_packed.tga')),np.float32);packed=np.uint8(np.rint(np.clip(packed*.57,8,235)))
 for m in METHODS:
  write_image(crisp,O/m/'materials/v045_loose.tga');write_image(crisp,O/m/'materials/v044_route_detail.tga');write_image(packed,O/m/'materials/v045_packed.tga')
 minimum=c.bounds.min(0)-25;maximum=c.bounds.max(0)+25;n=4096;dx=600/n
 oldwear=np.array(Image.open(baseline('mask_v046_wear.tga')));oldpacked=np.array(Image.open(baseline('mask_v046_packed.tga')))
 wear={m:oldwear.copy() for m in METHODS};pm={m:oldpacked.copy() for m in METHODS}
 x0=max(0,int(minimum[0]/dx));x1=min(n,int(maximum[0]/dx)+1);y0=max(0,int((600-maximum[1])/dx));y1=min(n,int((600-minimum[1])/dx)+1)
 for row in range(y0,y1,64):
  end=min(row+64,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row,end)+.5)*dx);f=c.common(x,z);w=f['scope'];active=w>0
  for m in METHODS:
   _,rgb=c.fields(x,z,f,m);factor=np.mean(rgb/np.array([107.45,96.81,77.44]),axis=2)
   # Darker fine-photo soil sits in cavities/patches, with lighter clod tops.
   amount=np.clip(.45+(1-factor)*2.7+.12*f['corner']-.15*f['shoulder'],.05,.94)
   for name,arrays,old,target in [('wear',wear,oldwear,255*(METHODS[m]['wear']+.035*f['face'])),('packed',pm,oldpacked,255*amount)]:
    before=old[row:end,x0:x1,3];new=np.uint8(np.rint(before*(1-w)+target*w));new[(before>0)&(new==0)]=1;new[before==0]=0
    arrays[m][row:end,x0:x1,3]=np.where(active,new,before)
 for m in METHODS:
  write_image(wear[m],O/m/'materials/mask_v046_wear.tga');write_image(pm[m],O/m/'materials/mask_v046_packed.tga')

def validate(c,changed,retained):
 inventory=json.loads((R/'V060_OUTPUT/surface_validation.json').read_text())['active_terrain_inventory'];allowed={'v045_loose.tga','v045_packed.tga','v044_route_detail.tga','v044_route_detail_n.tga','mask_v046_wear.tga','mask_v046_packed.tga'};rows=[]
 for m in METHODS:
  images=[]
  for item in inventory:
   path=source(item['file'],m);im=Image.open(path);assert list(im.size)==item['size'] and im.mode==item['mode'];actual=sha(path)
   if item['file'] not in allowed:assert actual==sha(baseline(item['file']))
   images.append(dict(item,sha256=actual))
  for name in ['mask_v046_wear.tga','mask_v046_packed.tga']:
   before=np.asarray(Image.open(baseline(name)));after=np.asarray(Image.open(source(name,m)))
   assert np.array_equal(before[:,:,:3],after[:,:,:3]);assert np.array_equal(before[:,:,3]>0,after[:,:,3]>0)
  assert sha(O/m/'terrain.raw')==sha(BASE/'terrain.raw') and sha(O/m/'scenery.fbx')==sha(BASE/'scenery.fbx')
  rows.append(dict(method=m,**METHODS[m],normal_changed_pixels=changed[m],normal_changes_outside_existing_soil_scope=0,normal_specular_alpha_exact=True,active_terrain_inventory=images,
   rgba8_base_level_bytes=sum(i['rgba8_bytes'] for i in images),added_images=0,added_layers=0,layer_count=14,wall_roller_heights_and_all_geometry_exact=True))
 assert len({p['rgba8_base_level_bytes'] for p in rows})==1
 report=dict(checks_pass=True,version='v062 source trials',baseline_source_commit='1002097379ee7e74b57971bd26f29c40eee98144',
  accepted_wall_roller_terrain_sha256=sha(BASE/'terrain.raw'),accepted_scenery_sha256=sha(BASE/'scenery.fbx'),
  texture_allocation_equal_to_v061=True,riding_geometry_unchanged=True,final_compilation_started=False,native_game_visual_verification=False,
  designs=rows,retained_geometry=retained,lighting=dict(sun_position_exact_v060=[2,10,-7],original_clear_ambient=[.44,.49,.56],proposed_clear_ambient=[.30,.34,.40],original_clear_fog_density=.00030,proposed_clear_fog_density=.00018,cloudy_and_rainy_unchanged=True),
  explanation='Replaces the dense cross-track stripes. Photographic colour remains at the accepted repeats, with 22% extra high-frequency contrast and unchanged scanned fine normals. Larger-scale dark/light variation is encoded in the existing packed-soil blend mask using a darker fine photographic packed tile. No coarse colour overlay or extra texture slots.',
  preview_limit='Approximate material/daylight source renders; native filtering, lighting and ride quality require a compiled in-game test after selection.')
 save(S/'trial_validation.json',report);save(O/'trial_validation.json',report);save(S/'designs.json',METHODS)
 print('V062_THREE_MATERIAL_TRIALS_PASS; roller preserved; existing image allocation',rows[0]['rgba8_base_level_bytes'],flush=True)

def main():
 for p in [O,S,CACHE]:p.mkdir(parents=True,exist_ok=True)
 retained=geometry();c=Circuit()
 if '--contrast-only' in __import__('sys').argv:
  prior=json.loads((S/'trial_validation.json').read_text());changed={r['method']:r['normal_changed_pixels'] for r in prior['designs']}
 else:changed=author(c)
 contrast(c);validate(c,changed,retained)

if __name__=='__main__':main()
