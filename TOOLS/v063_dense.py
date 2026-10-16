"""Contiguous forward/back passes over the v062 B trial; same v061 geometry."""
import gc,json,os
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from v062_trials import R,BASE,Circuit as PreviousCircuit,source as previous,noise,write_image,normal_map,smooth,sha,save

O=R/'V063_OUTPUT';M=O/'materials';S=R/'V063_SOURCE';PREV=R/'V062_OUTPUT/B'

def baseline(name):return previous(name,'B')
def source(name):return M/name if (M/name).is_file() else baseline(name)

class Circuit(PreviousCircuit):
 def __init__(self):
  super().__init__();rng=np.random.default_rng(630151);pos=[0.];neg=[];p=0.
  while p<22:p+=rng.uniform(.25,.31);pos.append(p)
  p=0.
  while p>-22:p-=rng.uniform(.25,.31);neg.append(p)
  self.centres=np.array(sorted(neg+pos));self.widths=rng.uniform(.165,.205,len(self.centres));self.depths=rng.uniform(.052,.066,len(self.centres))
  self.seeds=rng.uniform(0,6.28,len(self.centres));self.infill=(self.centres[:-1]+self.centres[1:])/2
 def passes(self,s,l):
  # A smooth maximum keeps neighbouring imprints from summing into a flat
  # field. Alternating rims suggest opposite travelling directions.
  idx=np.searchsorted(self.centres,l);g6=np.zeros_like(l);depth6=np.zeros_like(l);rim=np.zeros_like(l)
  for offset in [-2,-1,0,1]:
   ii=np.clip(idx+offset,0,len(self.centres)-1);wobble=.012*np.sin(s*.09+self.seeds[ii]);u=(l-self.centres[ii]-wobble)/self.widths[ii]
   g=np.exp(-u*u);g6+=g**6;depth6+=(g*self.depths[ii])**6
   side=np.where(ii%2==0,1.,-1.);r=np.exp(-((u-side*1.45)/1.02)**2);rim=np.maximum(rim,r)
  primary=g6**(1/6);depth=depth6**(1/6)
  mid=np.searchsorted(self.infill,l);secondary=np.zeros_like(l)
  for offset in [-1,0]:
   ii=np.clip(mid+offset,0,len(self.infill)-1);wobble=.010*np.sin(s*.09+(self.seeds[ii]+self.seeds[ii+1])/2)
   g=np.exp(-((l-self.infill[ii]-wobble)/.095)**2);secondary=np.maximum(secondary,g)
  return primary,depth,secondary,rim
 def fields(self,x,z,f):
  n0,n1=f['n0'],f['n1'];s,l=f['s'],f['l'];clod=np.maximum(0,.64*n0+.36*n1-.35)**1.45*3.4
  till=clod*.064+(n0-.5)*.010+(n1-.5)*.014
  core=1-smooth((abs(l)-f['half']-.4)/1.5);primary,depth,infill,rim=self.passes(s,l)
  activity=.90+.10*noise(x,z,3.7,11)
  relief=till*.60+(-depth-infill*.014+rim*.011)*core*activity
  # The darker photographic soil covers the entire worked width, including
  # between old bands. A subtle tonal groove survives distant mip filtering.
  coverage=np.clip(.78*primary+.22*infill,0,1)
  amount=np.clip(.35+.42*coverage+.10*(f['n3']-.5)+.08*(f['n2']-.5)+.06*f['corner'],.12,.93)
  return relief,amount,core,coverage

def retain():
 O.mkdir(parents=True,exist_ok=True);M.mkdir(exist_ok=True);S.mkdir(exist_ok=True);records=[]
 for name in ['terrain.raw','scenery.fbx','route.npz','jump_profiles.json','layout.json','main.tcl','start.tcl','compiled_track.hmf','trial_daylight.amb']:
  dest=O/name
  if not dest.exists():os.link(PREV/name,dest)
  assert sha(dest)==sha(PREV/name);records.append(dict(file=name,sha256=sha(dest)))
 return records

def author(c):
 old=np.array(Image.open(baseline('v044_route_detail_n.tga')));a=old.copy();n=len(a);dx=600/n;minimum=c.bounds.min(0)-25;maximum=c.bounds.max(0)+25
 x0=max(1,int(minimum[0]/dx));x1=min(n-1,int(maximum[0]/dx)+1);y0=max(1,int((600-maximum[1])/dx));y1=min(n-1,int((600-minimum[1])/dx)+1);count=0
 for row in range(y0,y1,96):
  end=min(row+96,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-1,end+1)+.5)*dx);f=c.common(x,z);w=f['scope'][1:-1]
  relief,_,_,_=c.fields(x,z,f);nn=normal_map(c,x,z,relief,dx)[1:-1]/127.5-1;before=old[row:end,x0:x1,:3];v=before/127.5-1
  v=v*(1-w[:,:,None])+nn*w[:,:,None];v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-8);new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)));new=np.where((w>0)[:,:,None],new,before)
  changed=np.any(new!=before,axis=2);assert not np.any(changed&(w==0));count+=int(changed.sum());a[row:end,x0:x1,:3]=new
  if (row-y0)//96%10==0:print('Dense grooming rows',row,'/',y1,flush=True)
 assert np.array_equal(a[:,:,3],old[:,:,3]);write_image(a,M/'v044_route_detail_n.tga');del old,a;gc.collect()
 name='mask_v046_packed.tga';a=np.array(Image.open(baseline(name)));old=a.copy();n=len(a);dx=600/n
 x0=max(0,int(minimum[0]/dx));x1=min(n,int(maximum[0]/dx)+1);y0=max(0,int((600-maximum[1])/dx));y1=min(n,int((600-minimum[1])/dx)+1)
 for row in range(y0,y1,64):
  end=min(row+64,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row,end)+.5)*dx);f=c.common(x,z);_,amount,core,_=c.fields(x,z,f);w=f['scope']*core
  before=old[row:end,x0:x1,3];value=np.uint8(np.rint(before*(1-w)+255*amount*w));value[(before>0)&(value==0)]=1;value[before==0]=0;a[row:end,x0:x1,3]=value
 assert np.array_equal(a[:,:,:3],old[:,:,:3]);assert np.array_equal(a[:,:,3]>0,old[:,:,3]>0);write_image(a,M/name)
 return count

def validate(c,retained,count):
 old=json.loads((R/'V062_SOURCE/trial_validation.json').read_text());inventory=next(r['active_terrain_inventory'] for r in old['designs'] if r['method']=='B');allowed={'v044_route_detail_n.tga','mask_v046_packed.tga'};images=[]
 for item in inventory:
  path=source(item['file']);im=Image.open(path);actual=sha(path);assert list(im.size)==item['size'] and im.mode==item['mode']
  if item['file'] not in allowed:assert actual==item['sha256'],item['file']
  images.append(dict(item,sha256=actual))
 # Check continuous lateral coverage including the literal centre, at varying
 # station phases. These are imprint-envelope checks, not tyre simulation.
 ss,ll=np.meshgrid(np.arange(0,c.length,1.),np.arange(-19.,19.001,.0125));primary,_,infill,_=c.passes(ss,ll);coverage=np.clip(.78*primary+.22*infill,0,1)
 assert coverage.min()>.45;centre=c.passes(np.arange(0,c.length,.1),np.zeros(len(np.arange(0,c.length,.1))))[0];assert centre.min()>.99
 gaps=np.diff(c.centres);width_sum=c.widths[:-1]+c.widths[1:];assert np.all(width_sum>gaps)
 # The roller lies outside the MX grooming region. Its normal texels are exact.
 oldnormal=Image.open(baseline('v044_route_detail_n.tga'));newnormal=Image.open(source('v044_route_detail_n.tga'));n=oldnormal.width;box=(int(525/600*n),int((600-252)/600*n),int(545/600*n)+1,int((600-218)/600*n)+1)
 assert np.array_equal(np.asarray(oldnormal.crop(box)),np.asarray(newnormal.crop(box)))
 assert sha(O/'terrain.raw')==sha(BASE/'terrain.raw') and sha(O/'scenery.fbx')==sha(BASE/'scenery.fbx')
 report=dict(checks_pass=True,version='v063 dense B trial',baseline_source_commit='5e5f34951f96bb09a940ce6326a02e31176b1315',
  source='v062 B flowing cultivation',retained_source_files=retained,normal_changed_pixels=count,normal_alpha_exact=True,normal_changes_outside_existing_soil_scope=0,
  continuous_passes=dict(primary_spacing_range_m=[float(gaps.min()),float(gaps.max())],primary_half_width_range_m=[float(c.widths.min()),float(c.widths.max())],
   additional_passes_at_every_primary_midpoint=True,explicit_primary_pass_at_track_centre=True,minimum_envelope_coverage=float(coverage.min()),minimum_centre_envelope=float(centre.min()),
   adjacent_primary_footprints_overlap=True,alternating_forward_back_rim_direction=True,route_direction_preserved=True,unworked_central_lane=False),
  active_terrain_inventory=images,texture_allocation_bytes=sum(i['rgba8_bytes'] for i in images),added_images=0,added_layers=0,
  all_photographic_RGB_exact_v062_B=True,wear_mask_exact_v062_B=True,lighting_exact_v062_B=True,all_geometry_and_wall_roller_exact=True,wall_roller_normal_texels_exact=True,
  final_compilation_started=False,in_game_verified=False,preview_note='Real material/terrain source render with approximate lighting; no native compilation.')
 assert report['texture_allocation_bytes']==next(r['rgba8_base_level_bytes'] for r in old['designs'] if r['method']=='B')
 save(S/'surface_validation.json',report);save(O/'surface_validation.json',report)
 print('V063_DENSE_FULL_WIDTH_PASS',count,'normal texels; minimum envelope',float(coverage.min()),'; roller and geometry exact',flush=True)

def main():
 retained=retain();c=Circuit();count=author(c);validate(c,retained,count)

if __name__=='__main__':main()
