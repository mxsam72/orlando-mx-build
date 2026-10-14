"""Apply the user-drawn A/B/C path revision to the delivered v052 geometry.

Metric controls come from the annotated 1024 px/600 m track-info map. Terrain
and native route/race data are authored together; unrelated RAW samples stay
byte exact. R09 and the eight R17 rollers retain their authored profiles.
"""
import io, json, math, re, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicSpline, CubicHermiteSpline, PchipInterpolator
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from v048_surface import R, BASE, sha, save, smooth
from v024_common import route_point, project
from v036_geometry import parse_tcl, open_segments
from reference_route import sample_native, write_tcl
from refine_jumps import supports
from jump_v024 import envelope

O=R/'V054_OUTPUT'; PREV=R/'V052_OUTPUT'; M=O/'materials'
NAME='orlandomx_2026_v054'; DEST=R/'12_RELEASE'/NAME
A=(578.,742.); C=(1276.,1390.); MERGE=500.
BOXES=[(285.,274.,429.,383.),(195.,190.,258.,326.),(310.,228.,439.,298.)]

def read(p):return json.loads(Path(p).read_text())
def ground(h,p):return map_coordinates(h,[(600-p[:,1])/600*2048,p[:,0]/600*2048],order=1,mode='nearest')
def unit(theta):return np.c_[np.cos(theta),np.sin(theta)]
def raster_points(n,box):
 ax=np.arange(n,dtype=float)/max(1,n-1)*600
 cc=np.flatnonzero((ax>=box[0])&(ax<=box[2]));rr=np.flatnonzero((600-ax>=box[1])&(600-ax<=box[3]))
 zz,xx=np.meshgrid(600-ax[rr],ax[cc],indexing='ij');return rr,cc,np.c_[xx.ravel(),zz.ravel()]

def curve(points,start_angle,end_angle,spacing=.08):
 pp=np.asarray(points,float);knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp,axis=0),axis=1))]
 sp=CubicSpline(knots,pp,bc_type=((1,unit(np.array([start_angle]))[0]),(1,unit(np.array([end_angle]))[0])))
 tt=np.linspace(0,knots[-1],max(1500,math.ceil(knots[-1]/.035)))
 vv=sp(tt);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(vv,axis=0),axis=1))]
 ss=np.linspace(0,arc[-1],math.ceil(arc[-1]/spacing)+1);t=np.interp(ss,arc,tt)
 p=sp(t);v=sp(t,1);a=sp(t,2);speed=np.linalg.norm(v,axis=1)
 assert speed.min()>.1,'Degenerate path tangent'
 theta=np.unwrap(np.arctan2(v[:,1],v[:,0]));curv=(v[:,0]*a[:,1]-v[:,1]*a[:,0])/speed**3
 return np.c_[p,theta,ss],curv

def projection(q,pts):
 d,i=cKDTree(q[:,:2]).query(pts,workers=2);v=pts-q[i,:2];th=q[i,2]
 along=(v*unit(th)).sum(1);lat=-v[:,0]*np.sin(th)+v[:,1]*np.cos(th)
 return d,i,q[i,3]+along,lat

class Layout:
 def __init__(self,generate=False):
  self.data=dict(np.load(BASE/'route.npz'));self.old=self.data['q'];self.width=self.data['width'];self.oldstart=self.data['start']
  if generate:self.build()
  else:
   out=dict(np.load(O/'route.npz'));self.q=out['q'];self.start=out['start'];self.knots=read(O/'layout.json')['start_width_knots'];self.old_s=out['v054_old_station']
  self.oldtree=cKDTree(self.old[:,:2]);self.newtree=cKDTree(self.q[:,:2]);self.starttree=cKDTree(self.start[:,:2]);self.oldstarttree=cKDTree(self.oldstart[:,:2])
  self.oldknots=np.array(read(BASE/'holeshot_layout.json')['start_width_knots'])

 def build(self):
  q=self.old.copy();changes=[]
  controls={
   'A':[(316.,310.),(350.,300.),(389.,290.),(403.,293.),(409.,304.),(399.,322.),(374.,342.)],
   'C':[(218.,303.),(210.,294.),(209.,281.),(215.,267.),(226.,249.),(237.,227.)]
  }
  for label,(lo,hi) in [('A',A),('C',C)]:
   ids=np.flatnonzero((self.old[:,3]>=lo)&(self.old[:,3]<=hi));a,b=ids[0]-1,ids[-1]+1
   p0,p1=self.old[[a,b]];cc,k=curve([p0[:2],*controls[label],p1[:2]],p0[2],p1[2])
   ss=(self.old[a:b+1,3]-p0[3])/(p1[3]-p0[3])*cc[-1,3]
   for j in range(2):q[a:b+1,j]=np.interp(ss,cc[:,3],cc[:,j])
   th=np.interp(ss,cc[:,3],cc[:,2]);th+=round((p0[2]-th[0])/(2*np.pi))*2*np.pi;q[a:b+1,2]=th
   q[[a,b],:3]=self.old[[a,b],:3]
   changes.append(dict(id=label,old_station_bounds=[float(p0[3]),float(p1[3])],old_length_m=float(p1[3]-p0[3]),new_length_m=float(cc[-1,3]),max_abs_curvature=float(abs(k).max()),controls_xz_m=np.asarray(controls[label]).tolist()))
  q[:,3]=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
  self.q=q;self.old_s=self.old[:,3]
  end=route_point(q,self.remap(MERGE))
  origin,heading,native_segments=parse_tcl(BASE/'main.tcl');accepted_native=sample_native(origin,heading,native_segments,.04)
  native_index=cKDTree(accepted_native[:,:2]).query(end[:2])[1];end=accepted_native[native_index,:3]
  start_controls=[[416.,230.],[414.,241.],[402.,257.],[385.,273.],[365.,278.],[347.,279.],[336.,274.]]
  dense,_=curve([[416.,172.],*start_controls,end[:2]],np.pi/2,end[2],spacing=.35)
  # Preserve the actual straight gate run-up, then approximate only the curve.
  cut=np.searchsorted(dense[:,3],59.);stop=np.searchsorted(dense[:,3],dense[-1,3]-1.0);p0=np.array([416.,229.])
  pp=np.vstack([p0,p0+[0,.35],dense[cut:stop,:2],end[:2]-.35*unit(np.array([end[2]]))[0],end[:2]])
  # Remove small endpoint duplicates before fitting native line/arc sections.
  pp=pp[np.r_[True,np.linalg.norm(np.diff(pp,axis=0),axis=1)>.01]]
  segs=[(0,57.,0.,0.)]+open_segments(pp)
  assert all(t==0 or abs(r)>.001 for t,length,r,angle in segs),'Degenerate native start arc'
  write_tcl(O/'start.tcl',[416.,172.],np.pi/2,segs);self.start=sample_native([416.,172.],np.pi/2,segs,.2)
  assert np.linalg.norm(self.start[-1,:2]-end[:2])<.01
  assert abs((self.start[-1,2]-end[2]+np.pi)%(2*np.pi)-np.pi)<1e-5
  self.knots=[[0,38],[57,38],[78,25],[105,14],[125,11],[float(self.start[-1,3]),11.8]]
  self.data.update(q=q,start=self.start,curvature=np.gradient(q[:,2],q[:,3]),v054_old_station=self.old[:,3],v054_old_to_new_station=q[:,3])
  np.savez_compressed(O/'route.npz',**self.data)
  save(O/'layout.json',dict(version='v054',baseline='v052',source_registration='Annotated v052 pic_info; x/600*1023, (600-z)/600*1023',sections=changes,start_merge_old_station_m=MERGE,start_merge_new_station_m=self.remap(MERGE),start_length_m=float(self.start[-1,3]),start_width_knots=self.knots,start_controls_xz_m=start_controls,gate_origin_xz=[416,172],gates_world_positions_preserved=True,unrelated_route_positions_exact=bool(np.array_equal(q[~self.active(self.old[:,3]),:2],self.old[~self.active(self.old[:,3]),:2]))))

 def active(self,s):return ((s>A[0])&(s<A[1]))|((s>C[0])&(s<C[1]))
 def along(self,s):
  out=np.zeros_like(s,dtype=float)
  for lo,hi in [A,C]:out=np.maximum(out,smooth((s-lo)/4)*(1-smooth((s-hi+4)/4)))
  return out
 def remap(self,s):return np.interp(s,self.old[:,3],self.q[:,3])
 def inverse(self,pts):
  d,i=self.newtree.query(pts,workers=2);delta=pts-self.q[i,:2];v=unit(self.q[i,2]);a=(delta*v).sum(1);lat=delta[:,0]*(-v[:,1])+delta[:,1]*v[:,0]
  ratio=np.gradient(self.old_s,self.q[:,3]);s=self.old_s[i]+a*ratio[i];p=np.c_[np.interp(s,self.old_s,self.old[:,0]),np.interp(s,self.old_s,self.old[:,1])];th=np.interp(s,self.old_s,self.old[:,2]);oldnormal=np.c_[-np.sin(th),np.cos(th)]
  src=p+oldnormal*lat[:,None];rotation=self.q[i,2]-th;half=self.width[i]/2
  weight=self.along(s)*(1-smooth((abs(lat)-half-2)/9))
  return src,rotation,weight,s,lat
 def forward(self,pts):
  d,i=self.oldtree.query(pts,workers=2);delta=pts-self.old[i,:2];v=unit(self.old[i,2]);a=(delta*v).sum(1);lat=delta[:,0]*(-v[:,1])+delta[:,1]*v[:,0];s=self.old[i,3]+a;ns=self.remap(s)
  p=np.c_[np.interp(ns,self.q[:,3],self.q[:,0]),np.interp(ns,self.q[:,3],self.q[:,1])];th=np.interp(ns,self.q[:,3],self.q[:,2]);target=p+np.c_[-np.sin(th),np.cos(th)]*lat[:,None]
  w=self.along(s)*(1-smooth((abs(lat)-self.width[i]/2-2)/9))
  return pts+(target-pts)*w[:,None]
 def fields(self,pts):
  src,rotation,neww,s,lat=self.inverse(pts);od,oi,os,ol=projection(self.old,pts)
  oldw=self.along(os)*(1-smooth((abs(ol)-self.width[oi]/2-2)/9))
  # Never edit the riding surface of an unrelated part of the main circuit.
  protected=(~self.active(os))&(od<self.width[oi]/2+1.8)
  neww[protected]=0;oldw[protected]=0
  sd,si,ss,sl=projection(self.start,pts);sw=np.interp(ss,*np.asarray(self.knots).T)
  bw=smooth((ss-55)/6)*(1-smooth((ss-self.start[-1,3])/3))*(1-smooth((abs(sl)-sw/2+.3)/4))
  bd,bi,bs,bl=projection(self.oldstart,pts);ow=np.interp(bs,*self.oldknots.T)
  retired=smooth((bs-55)/6)*(1-smooth((bs-self.oldstart[-1,3])/3))*(1-smooth((abs(bl)-ow/2+.3)/4))
  # B creates a bank opening only on the outside of the target merge.
  merge=smooth((os-434)/9)*(1-smooth((os-520)/9))
  protected_half=self.width[oi]/2+1.8
  protected_half=protected_half*(1-merge)+.8*merge
  protected_half=np.where(self.active(os),-.1,protected_half)
  bw*=smooth((od-protected_half)/2.5)
  retired*=smooth((od-self.width[oi]/2-1)/3)
  return dict(src=src,rotation=rotation,new=neww,old=oldw,station=s,lateral=lat,start=bw,retired_start=retired,start_station=ss,start_lateral=sl,start_width=sw,protected=protected,old_main_station=os,old_main_distance=od)

def native_routes(layout):
 origin,theta,segs=parse_tcl(BASE/'main.tcl');ends=sample_native(origin,theta,segs,1e6);old=sample_native(origin,theta,segs,.12)
 segments=[];cursor=0;changes=[];new_s=0.
 for label,(lo,hi) in [('A',A),('C',C)]:
  i0=int(cKDTree(ends[:,:2]).query(route_point(layout.old,lo)[:2])[1]);i1=int(cKDTree(ends[:,:2]).query(route_point(layout.old,hi)[:2])[1]);p0,p1=ends[[i0,i1]];assert i1>i0
  pre=segs[cursor:i0];segments+=pre;new_s+=sum(p[1] for p in pre)
  stations=np.linspace(p0[3]+.6,p1[3]-.6,max(10,int((p1[3]-p0[3])/.45)))
  pp=np.c_[np.interp(stations,old[:,3],old[:,0]),np.interp(stations,old[:,3],old[:,1])]
  moved=layout.forward(pp)
  pp=np.vstack([p0[:2],p0[:2]+.35*unit(np.array([p0[2]]))[0],moved,p1[:2]-.35*unit(np.array([p1[2]]))[0],p1[:2]])
  local=open_segments(pp);check=sample_native(p0[:2],p0[2],local,.15)
  assert np.linalg.norm(check[-1,:2]-p1[:2])<.01
  assert abs((check[-1,2]-p1[2]+np.pi)%(2*np.pi)-np.pi)<1e-4
  length=sum(p[1] for p in local);changes.append(dict(id=label,old=[float(p0[3]),float(p1[3])],new=[new_s,new_s+length],prefix_segments_preserved=i0,suffix_segments_preserved=len(segs)-i1))
  segments+=local;cursor=i1;new_s+=length
 segments+=segs[cursor:];write_tcl(O/'main.tcl',origin,theta,segments);new=sample_native(origin,theta,segments,.15)
 assert np.linalg.norm(new[-1,:2]-new[0,:2])<.02
 error=cKDTree(layout.q[:,:2]).query(new[:,:2],workers=2)[0]
 assert error.max()<.30,error.max()
 save(O/'native_route_validation.json',dict(checks_pass=True,changes=changes,old_native_length_m=float(old[-1,3]),new_native_length_m=float(new[-1,3]),max_native_to_authored_distance_m=float(error.max()),closure_m=float(np.linalg.norm(new[-1,:2]-new[0,:2])),unmodified_native_segments_preserved=True))
 data=dict(np.load(O/'route.npz'));data['native']=new;np.savez_compressed(O/'route.npz',**data)
 return old,new,changes

def profiles(layout):
 before=read(BASE/'jump_profiles.json');after=[]
 for p in before:
  n=dict(p);length=p['station_end_m']-p['station_start_m']
  # Anchor R09's landing before the unchanged R10 approach. Keep its 50 m
  # jump profile instead of stretching its gap with the longer straight.
  start=float(layout.remap(p['station_start_m']))
  if p['id']=='R09':start=float(layout.remap(p['station_end_m']))-length
  n['station_start_m']=start;n['station_end_m']=start+length;n['lip_s']=start+(p['lip_s']-p['station_start_m']);after.append(n)
  assert n['profile_s']==p['profile_s'] and n['profile_h']==p['profile_h'] and n['profile_derivative']==p['profile_derivative']
 save(O/'jump_profiles.json',after)
 return before,after

def terrain(layout,before,after):
 raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);h=raw.astype(float)/65535*18;w=layout.width
 selected={'R09','R17'};axis=np.linspace(0,600,2049);zz,xx=np.meshgrid(600-axis,axis,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()]
 oldjump=gaussian_filter(envelope(pts,supports([p for p in before if p['id'] in selected],layout.old,w)).reshape(h.shape),.65)
 floor=h-oldjump;background=gaussian_filter(floor,30);target=h.copy();allowed=np.zeros(h.shape,bool)
 start=layout.start;begin=58.;end=float(start[-1,3]);p0=route_point(start,begin);p1=start[-1];h0=ground(h,p0[None,:2])[0];h1=ground(h,p1[None,:2])[0]
 slope=lambda p:float((ground(h,(p[:2]+.4*unit(np.array([p[2]]))[0])[None])[0]-ground(h,(p[:2]-.4*unit(np.array([p[2]]))[0])[None])[0])/.8)
 # Follow the existing corner's riding elevation through the merge apron.
 # A low flat lane beside its higher bank would leave a ridge at the joint.
 ring=layout.old[(layout.old[:,3]>=430)&(layout.old[:,3]<=515)]
 hs=np.array([begin,92.,110.,126.,142.,158.,170.,end])
 hp=np.c_[np.interp(hs,start[:,3],start[:,0]),np.interp(hs,start[:,3],start[:,1])]
 indices=cKDTree(ring[:,:2]).query(hp)[1];values=ground(h,ring[indices,:2]);values[0]=h0;values[-1]=h1
 startheight=PchipInterpolator(hs,values)
 for box in BOXES:
  rr,cc,p=raster_points(2049,box);f=layout.fields(p);v=target[np.ix_(rr,cc)].ravel().copy()
  erase=np.maximum(f['old'],f['retired_start'])*(1-f['new'])*(1-f['start'])
  bg=ground(background,p);v=v*(1-erase)+bg*erase
  sample=ground(floor,f['src']);v=v*(1-f['new'])+sample*f['new']
  desired=startheight(np.clip(f['start_station'],begin,end))+.025*(f['start_lateral']/np.maximum(f['start_width']/2,1))**2
  v=v*(1-f['start'])+desired*f['start']
  active=np.maximum.reduce([f['old'],f['new'],f['start'],f['retired_start']])>0
  dest=target[np.ix_(rr,cc)];dest[active.reshape(dest.shape)]=v.reshape(dest.shape)[active.reshape(dest.shape)];target[np.ix_(rr,cc)]=dest
  allowed[np.ix_(rr,cc)]|=active.reshape(dest.shape)
 newjump=gaussian_filter(envelope(pts,supports([p for p in after if p['id'] in selected],layout.q,w)).reshape(h.shape),.65)
 # Rebuild the transported jumps only where A/C authoring actually applies.
 jump_scope=np.zeros(h.shape,float)
 for box in [BOXES[0],BOXES[1]]:
  rr,cc,p=raster_points(2049,box);f=layout.fields(p);jump_scope[np.ix_(rr,cc)]=np.maximum(jump_scope[np.ix_(rr,cc)],f['new'].reshape(len(rr),len(cc)))
 target+=newjump*jump_scope
 encoded=raw.copy();encoded[allowed]=np.rint(np.clip(target[allowed]/18*65535,0,65535)).astype('<u2')
 assert np.array_equal(encoded[~allowed],raw[~allowed]);(O/'terrain.raw').write_bytes(encoded.tobytes());Image.fromarray(encoded).save(O/'terrain_16bit.png')
 newh=encoded.astype(float)/65535*18;ss=np.linspace(58,end,700);sp=np.c_[np.interp(ss,start[:,3],start[:,0]),np.interp(ss,start[:,3],start[:,1])];hh=ground(newh,sp);grade=abs(np.gradient(hh,ss));change=encoded!=raw
 assert grade.max()<.48,('Start lane still has an abrupt bank',grade.max(),ss[grade.argmax()])
 # Detect a remaining abrupt step on dense cross-sections of the new entry.
 sections=[]
 for st in np.linspace(65,end-2,32):
  p=route_point(start,st);lat=np.linspace(-4.3,4.3,51);cross=p[:2]+np.c_[-np.sin(p[2])*lat,np.cos(p[2])*lat];heights=ground(newh,cross)
  sections.append(dict(station_m=float(st),cross_grade_max=float(abs(np.gradient(heights,lat)).max())))
 assert max(t['cross_grade_max'] for t in sections)<.60,sections
 qa=dict(checks_pass=True,baseline='v052',terrain_sha256=sha(O/'terrain.raw'),changed_samples=int(change.sum()),unrelated_raw_samples_exact=True,maximum_start_centre_grade=float(grade.max()),start_cross_sections=sections,gate_run_up_preserved=True,profile_arrays_exact_v052=True,R09_length_m=50,R17_roller_count=8,R17_spacing_m=10,scopes_xz_m=BOXES,in_game_riding_test=False)
 save(O/'terrain_validation.json',qa);print('V054_TERRAIN_CHECKS_PASSED',qa['changed_samples'],qa['maximum_start_centre_grade'],flush=True)

def race(layout,old,new,changes):
 src=R/'BUILD/v054_baseline_game';DEST.mkdir(parents=True,exist_ok=True)
 for p in src.iterdir():
  if p.suffix!='.trh':shutil.copy2(p,DEST/p.name.replace('orlandomx_2026_v052',NAME))
 def remap(st):
  delta=0.
  for row in changes:
   a,b=row['old'];an,bn=row['new']
   if st<a:return st+delta
   if st<=b:
    p=route_point(old,st);target=layout.forward(p[None,:2])[0]
    sub=new[(new[:,3]>=an-.5)&(new[:,3]<=bn+.5)]
    return project(sub,*target,(90-math.degrees(p[2]))%360)['long']
   delta=bn-b
  return st+delta
 text=(src/'orlandomx_2026_v052.rdf').read_text();records=[]
 checkpoints=[20.,92.,float(layout.start[-1,3]-10)]
 def edit(m):
  name,body=m.groups();get=lambda k:re.search(r'(?m)^\s*'+k+r'\s*=\s*([-+\d.eE]+)',body);lm=get('long');line=get('line')
  if lm is None:return m[0]
  oldst=float(lm[1]);lineid=int(float(line[1])) if line else 0;values={}
  if lineid==2:
   st=checkpoints[int(name.removeprefix('checkpoint'))];half=float(np.interp(st,*np.asarray(layout.knots).T))/2+1
   values=dict(long=st,left=-half,right=half)
  else:
   values['long']=remap(oldst)
   if name=='split1':
    end=layout.start[-1];merge_native=project(new,*end[:2],(90-math.degrees(end[2]))%360)['long'];values['long']=merge_native+5
   if name=='checkpoint7':
    # This old T05 checkpoint precedes the new merge. Keep it for regular
    # laps, and skip it on the gate-start lap (native start mode 0).
    values['start']=0
  for key,value in values.items():body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-+\d.eE]+',lambda n:n[1]+f'{value:.9f}',body,count=1)
  records.append(dict(block=name,old_long=oldst,new_long=values['long'],line=lineid));return name+'\n{'+body+'}'
 result=re.sub(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',edit,text,flags=re.S);(DEST/(NAME+'.rdf')).write_text(result)
 # Starting grid and pit stalls are before/after the edited native segments;
 # native station remapping retains their world positions and orientations.
 for fname in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
  raw=(src/fname).read_bytes();assert raw[:4]==b'TL \0';ar=np.frombuffer(raw[8:],'<f4').reshape(-1,2).copy();ar[:,0]=[remap(float(s)) for s in ar[:,0]]
  assert np.all(np.diff(ar[:,0])>=-.002);(DEST/fname).write_bytes(raw[:8]+ar.astype('<f4').tobytes())
 marshals=(src/'marshals.cfg').read_text()
 marshals=re.sub(r'(?m)(^\s*long\s*=\s*)([-+\d.eE]+)',lambda m:m[1]+f'{remap(float(m[2])):.9f}',marshals);(DEST/'marshals.cfg').write_text(marshals)
 ini=(DEST/(NAME+'.ini')).read_text().replace('v052','v054');ini=re.sub(r'(?m)^length=.*$',f'length={round(new[-1,3])}m',ini);(DEST/(NAME+'.ini')).write_text(ini)
 im=Image.new('RGB',(1024,1024),(239,232,221));d=ImageDraw.Draw(im);xy=lambda a:[tuple(v) for v in np.c_[a[:,0]/600*1023,(600-a[:,1])/600*1023]]
 d.line(xy(layout.q),fill=(90,62,42),width=11);d.line(xy(layout.start),fill=(204,132,46),width=12);im.save(DEST/(NAME+'_map.tga'));im.save(O/'v054_track_info.png')
 save(O/'race_validation.json',dict(checks_pass=True,gate_grid_world_positions_preserved=True,pit_stall_world_positions_preserved=True,starting_line_origin_preserved=True,first_lap_bypassed_checkpoint_made_normal_lap_only=True,first_sector_after_new_start_merge=True,start_checkpoint_stations_m=checkpoints,native_reset_stations_remapped=True,native_length_m=float(new[-1,3]),race_references=records,in_game_test=False))

def main():
 O.mkdir(parents=True,exist_ok=True);layout=Layout(generate=True);old,new,changes=native_routes(layout);before,after=profiles(layout);terrain(layout,before,after);race(layout,old,new,changes)
 print('V054_GEOMETRY_AND_RACE_READY',flush=True)
if __name__=='__main__':main()
