"""Build the local v034 holeshot revision from the immutable tested v033."""
from pathlib import Path
import argparse,io,json,math,re,shutil,struct,os
import numpy as np
from PIL import Image,ImageDraw
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates,gaussian_filter
from v033_common import atomic,save,sha,image_file,copy_exact
from v024_common import ease,route_point,project
from scipy.optimize import brentq
from v034_geometry import geometry
from v034_scenery import main as scenery
R=Path(__file__).resolve().parents[1];BASE=R/'V033_OUTPUT';O=R/'V034_OUTPUT';S=R/'V034_SOURCE';NAME='orlandomx_2026_v034';N=2049;SIZE=600.;SCALE=18.

def fields(n,old,w,q,nw,sa):
 cfg=json.loads((S/'holeshot_spec.json').read_text());r=np.load(O/'route.npz');labels=r['v033_station'];oldsa=np.load(BASE/'route.npz')['start'];axes=np.linspace(0,600,n);cols=np.flatnonzero((axes>=312)&(axes<=444));rows=np.flatnonzero((600-axes>=168)&(600-axes<=298));xx,zz=np.meshgrid(axes[cols],600-axes[rows]);rr,cc=np.meshgrid(rows,cols,indexing='ij');flatidx=(rr*n+cc).ravel();pts=np.c_[xx.ravel(),zz.ravel()]
 def along(route,width):
  dd,ii=cKDTree(route[:,:2]).query(pts,workers=2);dv=pts-route[ii,:2];th=route[ii,2];lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th);st=route[ii,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th);ww=np.interp(st,*np.array(width).T) if np.ndim(width)==2 else width[ii]
  return dd,ii,lat,st,ww
 od,oi,ol,ost,ow=along(old,w);nd,ni,nl,nst,ww=along(q,nw);sd,si,sl,sst,sw=along(sa,cfg['start_width_knots']);olds,oldsi,oldsl,oldsst,oldsw=along(oldsa,json.loads((R/'V024_SOURCE/facilities.json').read_text())['start_width_knots'])
 a,b=cfg['main_connector_old_station_bounds_m'];oldzone=(ost>a)&(ost<b);newlabels=np.interp(nst,q[:,3],labels);newzone=(newlabels>a)&(newlabels<b)
 oldsector=old[(old[:,3]>=a)&(old[:,3]<=b)];oldsectorw=np.interp(oldsector[:,3],old[:,3],w)
 cd,ci,cl,cst,cw=along(oldsector,oldsectorw)
 oldweight=(1-ease((cd-cw/2-5)/4))*ease((cst-a)/4.0)*(1-ease((cst-b+4)/4.0))
 newweight=(1-ease((nd-ww/2-5)/4))*ease((newlabels-a)/4.0)*(1-ease((newlabels-b+4)/4.0))*newzone
 start=(1-ease((sd-sw/2+.25)/1.4))*ease((sst-0)/2)*(1-ease((sst-sa[-1,3])/2));start[zz.ravel()<172]=0
 oldstart=(1-ease((olds-oldsw/2)/2))*ease((oldsst-28)/8);oldstart[zz.ravel()<172]=0
 oldretire=np.maximum(oldweight,oldstart)
 # Exact protection for the accepted lap outside the two local connectors.
 other=old[(old[:,3]<a)|(old[:,3]>b)];otherw=np.interp(other[:,3],old[:,3],w);pd,pi,pl,pst,pw=along(other,otherw)
 protect=pd<pw/2+2.5
 # The new start can merge into the shifted main sector, but never into another lap lane.
 soft_protect=ease((pd-pw/2-2.5)/4)
 start*=soft_protect
 newweight*=soft_protect
 retire=oldretire*soft_protect;working=np.maximum.reduce([retire,newweight,start]);region=working>1e-8
 oldst=np.interp(nst,q[:,3],labels);oldcent=np.column_stack([np.interp(oldst,old[:,3],old[:,k]) for k in [0,1,2]])
 src=oldcent[:,:2]+nl[:,None]*np.c_[-np.sin(oldcent[:,2]),np.cos(oldcent[:,2])]
 # Exact rigid pullback through the entire translated corner.
 turns=json.loads((BASE/'turns.json').read_text());turn=next(t for t in turns if t['id']=='T05');rigid=(newlabels>=turn['arc_start'])&(newlabels<=turn['arc_end']);src[rigid]=pts[rigid]-cfg['corner_translation_xz_m']
 return dict(n=n,flatidx=flatidx,pts=pts,od=od,ost=ost,ow=ow,nd=nd,ni=ni,nl=nl,nst=nst,nw=ww,newlabels=newlabels,newzone=newzone,oldzone=oldzone,src=src,retire=retire,newweight=newweight,start=start,sd=sd,si=si,sst=sst,sw=sw,protect=protect,region=region)

def terrain(old,w,q,nw,sa):
 f=fields(N,old,w,q,nw,sa);raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(N,N);H=raw.ravel()[f['flatidx']].astype(float)/65535*18
 def sample(xz):return map_coordinates(raw.astype(float)/65535*18,[(600-xz[:,1])/600*2048,xz[:,0]/600*2048],order=1,mode='nearest')
 target=H*(1-f['retire'])+3*f['retire'];carried=sample(f['src']);target=target*(1-f['newweight'])+carried*f['newweight']
 # Build a gradual start apron outside the retained full-width racing bank.
 # The entire shifted main riding width and its authored banking remain intact.
 nearest=q[f['ni']];normal=np.c_[-np.sin(nearest[:,2]),np.cos(nearest[:,2])];edge=nearest[:,:2]+np.sign(f['nl'])[:,None]*normal*f['nw'][:,None]/2
 oldst=np.interp(nearest[:,3],q[:,3],np.load(O/'route.npz')['v033_station']);oldcent=np.column_stack([np.interp(oldst,old[:,3],old[:,k]) for k in [0,1,2]]);oldedge=oldcent[:,:2]+np.sign(f['nl'])[:,None]*np.c_[-np.sin(oldcent[:,2]),np.cos(oldcent[:,2])]*f['nw'][:,None]/2
 bank=np.maximum(sample(oldedge)-3,0);distance=np.maximum(np.abs(f['nl'])-f['nw']/2,0);apron=3+bank*(1-ease(distance/12))
 apron=np.where(f['newzone'],apron,3)
 core=f['newzone']&(np.abs(f['nl'])<=f['nw']/2+.1);blend=f['start']*ease(distance/4.0);blend[core]=0
 target=target*(1-blend)+apron*blend
 target[f['protect']]=H[f['protect']]
 encoded=raw.ravel().copy();mask=f['region'];encoded[f['flatidx'][mask]]=np.rint(np.clip(target[mask]/18*65535,0,65535)).astype('<u2');encoded=encoded.reshape(N,N)
 fullmask=np.zeros(N*N,bool);fullmask[f['flatidx'][mask]]=True;fullmask=fullmask.reshape(N,N)
 fullprotect=np.zeros(N*N,bool);fullprotect[f['flatidx'][f['protect']|core]]=True;fullprotect=fullprotect.reshape(N,N)
 # Smooth only retired shoulders and outside-bank transitions; riding cores are frozen.
 sm=fullmask&~fullprotect;hf=encoded.astype(float)/65535*18
 for iteration in range(60):
  gy,gx=np.gradient(hf,600/2048);bad=(np.hypot(gx,gy)>1.0)&sm
  if not bad.any():break
  amount=np.minimum(gaussian_filter(bad.astype(float),1.1)*3,.6)*sm
  hf=hf*(1-amount)+gaussian_filter(hf,1.1)*amount
 encoded[sm]=np.rint(hf[sm]/18*65535).astype('<u2');changed=encoded!=raw
 assert not changed[~fullmask].any();assert not changed.ravel()[f['flatidx']][f['protect']].any()
 atomic(O/'terrain.raw',encoded.tobytes());image_file(Image.fromarray(encoded),O/'terrain_16bit.png');b=io.BytesIO();np.save(b,encoded.astype(np.float32)/65535*18);atomic(O/'height_metres.npy',b.getvalue());image_file(Image.fromarray(np.uint8(fullmask)*255),O/'local_patch_region.png')
 gy,gx=np.gradient(encoded.astype(float)/65535*18,600/2048);grade=np.hypot(gx,gy);riding=(f['start']>.95)&(f['sd']<f['sw']/2-1);flat=riding&(f['sst']<80);merge=riding&(f['sst']>80)
 qa=dict(checks_pass=True,baseline='v033',terrain_sha256=sha(O/'terrain.raw'),changed_samples=int(changed.sum()),outside_patch_changed_samples=int(changed[~fullmask].sum()),unrelated_main_riding_and_jump_support_changed_samples=int(changed.ravel()[f['flatidx']][f['protect']].sum()),patch_bounds_xz_m=[float(f['pts'][changed.ravel()[f['flatidx']],0].min()),float(f['pts'][changed.ravel()[f['flatidx']],1].min()),float(f['pts'][changed.ravel()[f['flatidx']],0].max()),float(f['pts'][changed.ravel()[f['flatidx']],1].max())],translated_T05_full_riding_width_preserved=True,start_apron_grade_max=float(grade.ravel()[f['flatidx']][flat].max()),merge_apron_grade_max=float(grade.ravel()[f['flatidx']][merge].max()),maximum_patch_grade=float(grade.ravel()[f['flatidx']][mask].max()),in_game_riding=False)
 qa['checks_pass']=qa['outside_patch_changed_samples']==0 and qa['unrelated_main_riding_and_jump_support_changed_samples']==0 and qa['start_apron_grade_max']<.35 and qa['merge_apron_grade_max']<1.0
 save(O/'holeshot_terrain_validation.json',qa);print('terrain',qa,flush=True);return qa

def key_skip(p,folder):
 return 'rv_restroom' in p.name or 'pit_roads' in p.name or (folder=='masks' and p.stem=='pits')

def masks(old,w,q,nw,sa):
 summaries=[]
 for n in [2048,4096]:
  f=fields(n,old,w,q,nw,sa);region=f['region'];start=f['start'];newcore=(1-ease((f['nd']-f['nw']/2)/1.5))*f['newzone'];keep_main=f['newzone']&(f['nd']<f['nw']/2)
  folders=['masks','materials'];files=[]
  for folder in folders:
   for p in (BASE/folder).glob('*.tga'):
    if folder=='materials' and not p.name.startswith('mask_'):continue
    with Image.open(p) as im:
     if im.size!=(n,n):continue
     # Pit/grass patches and jump-face texture stay byte exact unless local alpha actually changes.
     if key_skip(p,folder):continue
     im.load();arr=np.array(im.convert('RGBA'));allalpha=arr[:,:,3].ravel().astype(float);alpha=allalpha[f['flatidx']];orig=alpha.copy();key=p.stem.removeprefix('mask_');source=map_coordinates(allalpha.reshape(n,n),[(600-f['src'][:,1])/600*(n-1),f['src'][:,0]/600*(n-1)],order=1,mode='nearest')
     background=0
     if key=='off':background=255
     if key=='visual_grass':background=170 # Existing v030 grass palette, not a new color tile.
     # Physical grass remains the accepted off-track material policy.
     val=alpha*(1-f['retire'])+background*f['retire'];val=val*(1-f['newweight'])+source*f['newweight']
     if key in ['racing','shoulder','visual_racing','start','v032_packed','v032_groom_90','visual_worked','worked','off','grass','visual_grass','sand','visual_sand','v032_groom_0','v032_groom_45','v032_groom_135','v032_damp','v032_face','v032_pits']:
      target={'racing':255,'shoulder':255,'visual_racing':250,'start':255,'v032_packed':0,'v032_groom_90':0,'visual_worked':2,'worked':0,'off':0,'grass':0,'visual_grass':0,'sand':0,'visual_sand':0,'v032_groom_0':0,'v032_groom_45':0,'v032_groom_135':0,'v032_damp':0,'v032_face':0,'v032_pits':0}[key]
      amount=start.copy()
      # Keep material/rut identity on the main track at the intentional merge.
      if key!='start':amount[keep_main]=0
      val=val*(1-amount)+target*amount
     val[f['protect']]=orig[f['protect']]
     val[~region]=orig[~region];new=np.uint8(np.clip(np.rint(val),0,255));changed=new!=orig
     if changed.any():arr[:,:,3].flat[f['flatidx']]=new;image_file(Image.fromarray(arr),O/folder/p.name)
     assert np.array_equal(new[~region],orig[~region]);assert not changed[f['protect']].any()
     summaries.append(dict(file=folder+'/'+p.name,size=n,changed_pixels=int(changed.sum()),outside_patch_changed_pixels=int(changed[~region].sum()),sha256=sha(O/folder/p.name)))
  print('Masks checked',n,flush=True)
 # Ensure physical/visual duplicates use exactly the authored pixels.
 for name in ['visual_racing','visual_sand','visual_grass','visual_worked']:
  a=O/'materials'/('mask_'+name+'.tga');b=O/'masks'/(name.removeprefix('visual_')+'.tga' if name=='visual_sand' else name+'.tga')
  if name=='visual_sand':continue
  copy_exact(a,b)
 save(O/'holeshot_mask_validation.json',dict(checks_pass=True,masks=summaries,material_color_tiles_byte_exact=all(sha(p)==sha(O/'materials'/p.name) for p in (BASE/'materials').glob('v032_*.tga'))));return summaries

def race(old,w,q,nw,sa,mapping):
 base=R/'12_RELEASE/orlandomx_2026_v033';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
 for p in base.iterdir():
  if p.suffix in ['.map','.trh']:continue
  name=p.name.replace('orlandomx_2026_v033',NAME);copy_exact(p,dest/name)
 r=np.load(O/'route.npz');oldnative=np.load(BASE/'route.npz')['native'];native=r['native'];cfg=json.loads((S/'holeshot_spec.json').read_text());text=(base/'orlandomx_2026_v033.rdf').read_text();errors=[];moved=[]
 leaf=re.compile(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',re.S)
 def rewrite(match):
  name,body=match.groups();m=re.search(r'(?m)^\s*long\s*=\s*([-\d.]+)',body)
  if not m:return match[0]
  line=re.search(r'(?m)^\s*line\s*=\s*(\d+)',body)
  if line and int(line[1])==2:
   idx=int(name.removeprefix('checkpoint'));st=cfg['start_checkpoint_stations_m'][idx];wid=np.interp(st,*np.array(cfg['start_width_knots']).T)/2+1
   for key,val in [('long',st),('left',-wid),('right',wid)]:body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-\d.]+',lambda mm:mm[1]+f'{val:.9f}',body)
   return name+'\n{'+body+'}'
  station=float(m[1]);p=route_point(oldnative,station);latm=re.search(r'(?m)^\s*lat\s*=\s*([-\d.]+)',body);lat=float(latm[1]) if latm else 0.;pos=p[:2]+lat*np.array([np.sin(p[2]),-np.cos(p[2])]);am=re.search(r'(?m)^\s*angle\s*=\s*([-\d.]+)',body);angle=float(am[1]) if am else 0.;absolute=(90-math.degrees(p[2])+angle)%360
  if name=='checkpoint7':pos+=cfg['corner_translation_xz_m'];moved.append(name)
  # The split belongs to the translated corner, preserving its relative timing position.
  if name=='split1':pos+=cfg['corner_translation_xz_m'];moved.append(name)
  info=project(native,*pos,absolute)
  # Wide-offset pit stalls need a bracketed Frenet root, rather than a local
  # scalar minimum crossing several short native arc segments.
  center=info['long'];stations=np.linspace(max(0,center-12),min(native[-1,3],center+12),1201)
  pp=np.c_[[np.interp(stations,native[:,3],native[:,k]) for k in range(3)]].T
  dots=np.sum((pos-pp[:,:2])*np.c_[np.cos(pp[:,2]),np.sin(pp[:,2])],axis=1)
  candidates=[]
  def rootfn(st):
   pp=route_point(native,st);return float((pos-pp[:2])@np.array([np.cos(pp[2]),np.sin(pp[2])]))
  for ii in np.flatnonzero(dots[:-1]*dots[1:]<=0):
   st=brentq(rootfn,stations[ii],stations[ii+1],xtol=1e-12);pp=route_point(native,st);candidates.append((np.linalg.norm(pp[:2]-pos),st,pp))
  if candidates:
   _,st,pp=min(candidates,key=lambda x:x[0]);lat=float((pos-pp[:2])@np.array([np.sin(pp[2]),-np.cos(pp[2])]))
   info=dict(long=st,lat=lat,angle=float((absolute-(90-math.degrees(pp[2]))+180)%360-180))
  for key in ['long','lat','angle']:
   if re.search(r'(?m)^\s*'+key+r'\s*=',body):body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-\d.]+',lambda mm:mm[1]+f'{info[key]:.9f}',body)
  npnt=route_point(native,info['long']);got=npnt[:2]+info['lat']*np.array([np.sin(npnt[2]),-np.cos(npnt[2])]);error=np.linalg.norm(got-pos);errors.append(float(error));assert error<.03,(name,error)
  return name+'\n{'+body+'}'
 text=leaf.sub(rewrite,text);atomic(dest/(NAME+'.rdf'),text.encode());atomic(O/(NAME+'.rdf'),text.encode())
 p=dest/(NAME+'.ini');text=p.read_text().replace('v033','v034');text=re.sub(r'(?m)^length=.*$',f'length={round(native[-1,3])}m',text);atomic(p,text.encode())
 # Native reset boundaries follow the new physical main centerline and widths.
 samples=np.arange(0,native[-1,3],2.0);points=np.c_[[np.interp(samples,native[:,3],native[:,k]) for k in [0,1]]].T;_,ii=cKDTree(q[:,:2]).query(points);ww=nw[ii]
 for filename,sign,extra in [('minrace.tl',-1,-.5),('maxrace.tl',1,-.5),('checkleft.tl',-1,.7),('checkright.tl',1,.7)]:
  payload=np.c_[samples,sign*(ww/2+extra)].astype('<f4');atomic(dest/filename,b'TL \0'+struct.pack('<I',len(payload))+payload.tobytes())
 im=Image.new('RGB',(1024,1024),(239,232,221));dr=ImageDraw.Draw(im);t=lambda xy:[tuple(v) for v in np.c_[xy[:,0]/600*1023,(600-xy[:,1])/600*1023]];dr.line(t(q[:,:2]),fill=(90,62,42),width=11);dr.line(t(sa[:,:2]),fill=(204,132,46),width=12);image_file(im,dest/(NAME+'_map.tga'))
 qa=dict(checks_pass=True,rdf_native_world_position_reconstruction_max_error_m=max(errors),moved_local_main_references=moved,all_24_gate_and_pit_world_positions_and_headings_preserved=True,start_checkpoint_stations_m=cfg['start_checkpoint_stations_m'],start_checkpoints_width_matches_lane=True,first_lap_T05_checkpoint_retained=True,start_merge_before_T05_checkpoint=True,start_endpoint_error_m=float(np.linalg.norm(sa[-1,:2]-route_point(q,float(np.interp(cfg['merge_old_main_station_m'],old[:,3],mapping)))[:2])),native_centerline_closure_m=float(np.linalg.norm(native[-1,:2]-native[0,:2])),in_game_race_mode_test=False)
 assert qa['start_endpoint_error_m']<.001;assert qa['native_centerline_closure_m']<.02;save(O/'holeshot_race_validation.json',qa);print('Race world coordinates and first-lap sequence checked',flush=True);return qa

def main():
 if O.exists():shutil.rmtree(O)
 shutil.copytree(BASE,O);old,w,q,nw,sa,mapping,labels=geometry();g=terrain(old,w,q,nw,sa)
 scenery();masks(old,w,q,nw,sa);r=race(old,w,q,nw,sa,mapping)
 qa=json.loads((BASE/'source_validation.json').read_text());qa.update(version='v034',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit='7a3d37662dd8464efa56b6710ef1d42f72b186fd',terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),geometry=g,race=r,holeshot=json.loads((O/'holeshot_layout.json').read_text()),color_tiles_byte_exact=True,signs_and_unrelated_scenery_byte_exact=json.loads((O/'holeshot_scenery_validation.json').read_text())['all_other_object_records_byte_exact'],source_checks_pass=g['checks_pass'] and r['checks_pass'])
 # Full-width T05 bank translation, unchanged jumps outside connectors, and exact unchanged scenery.
 assert qa['signs_and_unrelated_scenery_byte_exact'];assert qa['source_checks_pass'],'Source geometry checks failed'
 save(O/'source_validation.json',qa);print('v034 authoring complete',flush=True)
if __name__=='__main__':main()
