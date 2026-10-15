"""Actual v061 heightfield/HMF and saved FBX previews; no native compilation."""
import gc,io,json,math,os,sys,time,zipfile
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from numba import njit
from v061_inputs import R,O,PREV,S,source,baseline,sha,save
from v027_scenery import parse,values,child,geometry_records,vertices
from rebind_scenery import array
from scene_texture_bindings_v044 import actual_diffuse_bindings
from v054_previews import Terrain
from v049_previews import font
import v058_render as ray
import v058_full_review as material

OUT=R/'BUILD/v061_review';CACHE=R/'BUILD/v061_cache/review'
W,H=1600,1000
VIEWS=[
 dict(id='01',title='Wall roller / placement before the big double',eye_xzy_m=[486.,203.,44.],target_xzy_m=[535.,280.,4.],fov=65.,max_distance_m=280.),
 dict(id='02',title='Low approach / broad rounded takeoff',eye_xzy_m=[532.,215.,5.0],target_xzy_m=[535.,248.,4.3],fov=62.),
 dict(id='03',title='Side view / crest, wall and asphalt landing',eye_xzy_m=[509.,241.,12.],target_xzy_m=[535.,242.,3.8],fov=66.),
 dict(id='04',title='From the road / wall clearance and takeoff width',eye_xzy_m=[550.,266.,13.],target_xzy_m=[535.,242.,3.6],fov=66.),
 dict(id='05',title='Alignment / new roller and existing speedway double',eye_xzy_m=[475.,155.,135.],target_xzy_m=[535.,310.,3.0],fov=67.,max_distance_m=380.),
]

def trace(c,view):
 """Use the existing perspective/mip method with sufficient overview range."""
 maximum=view.get('max_distance_m',160.);filename=ray.CACHE/(view['id']+'_hits.npz')
 eye=np.asarray(view['eye_xzy_m'],np.float32);target=np.asarray(view['target_xzy_m'],np.float32)
 if filename.exists():
  with np.load(filename) as cache:data=dict(cache)
  if int(data.get('width',0))==W and int(data.get('height',0))==H and float(data.get('max_distance',0))==maximum and float(data.get('fov',0))==view['fov'] and np.allclose(data['eye'],eye) and np.allclose(data['target'],target):
   return {k:v for k,v in data.items() if k not in ['width','height','fov','max_distance']}
 sy,sx=np.mgrid[:H,:W].astype(np.float32);forward=target-eye;forward/=np.linalg.norm(forward)
 right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward);tangent=math.tan(math.radians(view['fov']/2))
 rx=(sx+.5-W/2)/(W/2)*tangent;ry=-(sy+.5-H/2)/(W/2)*tangent
 rays=forward+rx[:,:,None]*right+ry[:,:,None]*up;rays/=np.linalg.norm(rays,axis=2,keepdims=True);rays=rays.astype(np.float32)
 hit=np.zeros((H,W),bool);lo=np.zeros((H,W),np.float32);hi=lo.copy()
 for distance in np.r_[.15,np.arange(.65,maximum+.1,1.5)]:
  p=eye+rays*distance;below=p[:,:,2]<=c.terrain.ground(p[:,:,0],p[:,:,1]);new=below&~hit
  lo[new]=max(0,distance-1.5);hi[new]=distance;hit|=new
 for _ in range(15):
  distance=(lo+hi)/2;p=eye+rays*distance[:,:,None];below=p[:,:,2]<=c.terrain.ground(p[:,:,0],p[:,:,1])
  hi=np.where(hit&below,distance,hi);lo=np.where(hit&~below,distance,lo)
 p=eye+rays*hi[:,:,None];far=eye+rays*maximum;x=np.where(hit,p[:,:,0],far[:,:,0]);z=np.where(hit,p[:,:,1],far[:,:,1])
 data=dict(x=x.ravel(),z=z.ravel(),ground=p[:,:,2].ravel(),hit=hit.ravel(),eye=eye,target=target,**ray.footprint(x,z))
 temp=filename.with_suffix('.writing.npz');np.savez_compressed(temp,width=W,height=H,fov=view['fov'],max_distance=maximum,**data);temp.replace(filename)
 print('Traced',view['id'],int(hit.sum()),'terrain pixels',flush=True);return data

@njit(cache=True)
def raster(p,n,uv,faces,levels,offsets,widths,heights,depth,image,light):
 h,w=depth.shape
 for f in faces:
  ia,ib,ic=f;a=p[ia];b=p[ib];c=p[ic]
  if min(a[2],b[2],c[2])<=.1:continue
  x0=max(0,int(np.floor(min(a[0],b[0],c[0]))));x1=min(w-1,int(np.ceil(max(a[0],b[0],c[0]))))
  y0=max(0,int(np.floor(min(a[1],b[1],c[1]))));y1=min(h-1,int(np.ceil(max(a[1],b[1],c[1]))))
  if x0>x1 or y0>y1:continue
  den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-9:continue
  ratio=1.
  for i,j in [(ia,ib),(ib,ic),(ic,ia)]:
   delta=(uv[i]-uv[j])*np.array([widths[0],heights[0]])
   px=p[i,:2]-p[j,:2];ratio=max(ratio,np.sqrt(np.sum(delta*delta)/max(np.sum(px*px),1e-6)))
  level=min(len(widths)-1,max(0,int(np.floor(np.log2(ratio)))))
  tw=widths[level];th=heights[level];offset=offsets[level]
  for yy in range(y0,y1+1):
   for xx in range(x0,x1+1):
    wa=((b[1]-c[1])*(xx+.5-c[0])+(c[0]-b[0])*(yy+.5-c[1]))/den
    wb=((c[1]-a[1])*(xx+.5-c[0])+(a[0]-c[0])*(yy+.5-c[1]))/den;wc=1-wa-wb
    if min(wa,wb,wc)<-1e-7:continue
    aa=wa/a[2];bb=wb/b[2];cc=wc/c[2];d=1/(aa+bb+cc)
    if d>=depth[yy,xx]:continue
    aa*=d;bb*=d;cc*=d
    u=aa*uv[ia,0]+bb*uv[ib,0]+cc*uv[ic,0];v=aa*uv[ia,1]+bb*uv[ib,1]+cc*uv[ic,1]
    tx=(u%1)*tw-.5;ty=(v%1)*th-.5;ix=int(np.floor(tx));iy=int(np.floor(ty));fx=tx-ix;fy=ty-iy
    colour=np.empty(4,np.float64)
    for k in range(4):
     colour[k]=(levels[offset+(iy%th)*tw+ix%tw,k]*(1-fx)+levels[offset+(iy%th)*tw+(ix+1)%tw,k]*fx)*(1-fy)+(levels[offset+((iy+1)%th)*tw+ix%tw,k]*(1-fx)+levels[offset+((iy+1)%th)*tw+(ix+1)%tw,k]*fx)*fy
    if colour[3]<130:continue
    normal=aa*n[ia]+bb*n[ib]+cc*n[ic];normal/=max(np.sqrt(np.sum(normal*normal)),1e-9)
    diffuse=.38+.70*max(0.,np.sum(normal*light))
    for k in range(3):image[yy,xx,k]=min(255.,((colour[k]/255)**2.2*diffuse)**(1/2.2)*255)
    depth[yy,xx]=d

def texture_levels(im):
 im=im.convert('RGBA');arrays=[];offsets=[];widths=[];heights=[];offset=0
 while True:
  a=np.ascontiguousarray(np.asarray(im)[::-1]);offsets.append(offset);widths.append(im.width);heights.append(im.height);arrays.append(a.reshape(-1,4));offset+=im.width*im.height
  if max(im.size)<=2:break
  im=im.resize((max(1,im.width//2),max(1,im.height//2)),Image.Resampling.BOX)
 return np.concatenate(arrays),np.array(offsets),np.array(widths),np.array(heights)

def scene():
 """Decode only source meshes that overlap the speedway review area."""
 print('Reading saved speedway scene',flush=True)
 nodes,_=parse((O/'scenery.fbx').read_bytes());records=geometry_records(nodes)
 objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
 links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
 bindings={b['texture_id']:b['texture'] for b in actual_diffuse_bindings(nodes)['bindings']}
 mt={v[2]:v[1] for v in links if v[1] in bindings and (v[0]!=b'OP' or v[3]==b'DiffuseColor')}
 mm={v[2]:v[1] for v in links if objects.get(v[1],{}).get('name')==b'Material'}
 textures={None:texture_levels(Image.new('RGBA',(2,2),(102,102,98,255)))};meshes=[]
 for name,(g,mid) in records.items():
  world=vertices(g);lo=world.min(0);hi=world.max(0)
  if hi[0]<440 or lo[0]>610 or hi[2]<185 or lo[2]>435:continue
  raw=array(child(g,b'PolygonVertexIndex'));ind=np.where(raw<0,-raw-1,raw);corners=[];start=0
  for end in np.flatnonzero(raw<0):
   polygon=list(range(start,end+1));corners.extend([[polygon[0],polygon[k],polygon[k+1]] for k in range(1,len(polygon)-1)]);start=end+1
  corners=np.asarray(corners,dtype=np.int64);vid=ind[corners];p=world[vid][:,:,[0,2,1]].reshape(-1,3)
  keep=np.all(p.reshape(-1,3,3)[:,:,0]>=425,axis=1)&np.all(p.reshape(-1,3,3)[:,:,0]<=625,axis=1)
  nn=next((n for n in g['children'] if n['name']==b'LayerElementNormal'),None)
  if nn:
   normals=array(child(nn,b'Normals')).reshape(-1,3);ni=next((n for n in nn['children'] if n['name']==b'NormalsIndex'),None)
   if ni:normals=normals[array(ni)]
   normals=(normals[corners] if len(normals)==len(raw) else normals[vid]).reshape(-1,3)*[1,1,-1];normals=normals[:,[0,2,1]]
  else:
   pp=p.reshape(-1,3,3);normal=np.cross(pp[:,1]-pp[:,0],pp[:,2]-pp[:,0]);normal[normal[:,2]<0]*=-1;normals=np.repeat(normal,3,axis=0)
  normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-9)
  un=next((n for n in g['children'] if n['name']==b'LayerElementUV'),None);uv=np.zeros((len(p),2))
  if un:
   u=array(child(un,b'UV')).reshape(-1,2);ui=next((n for n in un['children'] if n['name']==b'UVIndex'),None)
   if ui:u=u[array(ui)]
   uv=(u[corners] if len(u)==len(raw) else u[vid]).reshape(-1,2)
  tid=mt.get(mm.get(mid));texname=bindings.get(tid,'')
  if texname:
   from vehicle_textures_v022 import NATIVE_U_MIRROR_FIX
   if Path(texname).stem.removeprefix('v024_vehicle_') in NATIVE_U_MIRROR_FIX:uv[:,0]=1-uv[:,0]
  if tid not in textures:
   video=next(objects[v[1]] for v in links if v[2]==tid and objects.get(v[1],{}).get('name')==b'Video')
   rawimage=child(video,b'Content')['props'];assert rawimage[:1]==b'R';im=Image.open(io.BytesIO(rawimage[5:]));textures[tid]=texture_levels(im)
  # Restrict by triangle rather than its centre so partially visible walls survive.
  if not np.any(keep):continue
  p=p.reshape(-1,3,3)[keep].reshape(-1,3);normals=normals.reshape(-1,3,3)[keep].reshape(-1,3);uv=uv.reshape(-1,3,2)[keep].reshape(-1,2)
  meshes.append((name,np.ascontiguousarray(p),np.ascontiguousarray(normals),np.ascontiguousarray(uv),np.arange(len(p)).reshape(-1,3),tid))
 del nodes,objects,records;gc.collect();print('Saved scene meshes ready',len(meshes),flush=True);return meshes,textures

def setup_materials(before=False):
 material.O=PREV if before else O;material.source=baseline if before else source
 def shader(name):
  try:return (baseline if before else source)(str(Path(name).with_suffix('.shd')))
  except FileNotFoundError:return None
 material.old_shader=shader
 return material.ProductionMaterials()

def render_one(view,meshes,textures,before=False):
 t=time.monotonic();mode='v060' if before else 'v061';key=view['id']+'_'+mode
 ray.CACHE=CACHE/mode;ray.CACHE.mkdir(parents=True,exist_ok=True);ray.WIDTH=W;ray.HEIGHT=H;material.W=W;material.H=H
 c=SimpleNamespace(terrain=Terrain((PREV if before else O)/'terrain.raw'));m=setup_materials(before)
 data=trace(c,dict(view,id=key));ctx,ids=material.context(c,data);rgb,n,stats=m.composite(ctx);im=material.shade(ctx,rgb,n,ids)
 image=np.asarray(im).astype(np.float64);eye=data['eye'];target=data['target'];forward=target-eye;forward/=np.linalg.norm(forward)
 right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward);basis=np.stack([right,up,forward],1)
 points=np.stack([data['x'],data['z'],data['ground']],1);depth=np.where(data['hit'],(points-eye)@forward,np.inf).reshape(H,W).astype(np.float64)
 light=np.array([2.,-7.,10.]);light/=np.linalg.norm(light);scale=W/(2*math.tan(math.radians(view['fov']/2)))
 for name,p,normal,uv,faces,tid in meshes:
  cam=(p-eye)@basis
  if np.max(cam[:,2])<.1:continue
  projected=cam.copy();projected[:,0]=W/2+cam[:,0]/np.maximum(cam[:,2],.01)*scale;projected[:,1]=H/2-cam[:,1]/np.maximum(cam[:,2],.01)*scale
  if projected[:,0].max()<0 or projected[:,0].min()>W or projected[:,1].max()<0 or projected[:,1].min()>H:continue
  raster(projected,normal,uv,faces,*textures[tid],depth,image,light)
 im=Image.fromarray(np.uint8(np.rint(np.clip(image,0,255))));draw=ImageDraw.Draw(im)
 draw.rectangle((0,0,W,76),fill=(22,25,29));draw.text((20,10),view['id']+'  '+view['title'],font=font(26),fill='white')
 draw.text((20,46),('v060 before' if before else 'v061 roller attempt')+' | Actual source preview; approximate lighting | Not an in-game capture',font=font(18),fill=(204,217,225))
 path=OUT/(f'Orlando_{mode}_Roller_'+view['id']+'.jpg');im.save(path,quality=96,subsampling=0)
 report=dict(file=path.name,sha256=sha(path),view=view,baseline=before,seconds=round(time.monotonic()-t,2),terrain_pixels=len(ids),source_mesh_count=len(meshes),layers=stats)
 save(OUT/('view_'+key+'.json'),report);print('RENDER_READY',path.name,report['seconds'],'seconds',flush=True)
 del m,ctx,data,rgb,n,depth,image,points;gc.collect();return report

def package(rows):
 sheets=[]
 for label,ids in [('Overview',['01','05']),('Details',['02','03','04'])]:
  tw,th=1000,625;selected=[r for r in rows if r['view']['id'] in ids and not r['baseline']]
  sheet=Image.new('RGB',(tw*len(selected),th),(22,25,29))
  for i,r in enumerate(selected):sheet.paste(Image.open(OUT/r['file']).resize((tw,th),Image.Resampling.LANCZOS),(tw*i,0))
  p=OUT/('Orlando_v061_Roller_'+label+'.jpg');sheet.save(p,quality=95,subsampling=0);sheets.append(p.name)
 # Matched comparison makes the added footprint clear without painting a marker onto the dirt.
 selected=[r for r in rows if r['view']['id']=='03'];sheet=Image.new('RGB',(W*2,H))
 for i,r in enumerate(sorted(selected,key=lambda r:not r['baseline'])):sheet.paste(Image.open(OUT/r['file']),(i*W,0))
 compare=OUT/'Orlando_v061_Roller_Before_After.jpg';sheet.save(compare,quality=95,subsampling=0);sheets.append(compare.name)
 report=dict(version='v061 preview attempt 1',source_only=True,in_game_capture=False,final_compilation_started=False,
  terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),hmf_sha256=sha(O/'compiled_track.hmf'),
  geometry_validation_sha256=sha(S/'geometry_validation.json'),resolution=[W,H],renders=rows,sheets=sheets)
 save(OUT/'Review_Manifest.json',report);save(S/'preview_review.json',report)
 (OUT/'Read_Me.txt').write_text('Orlando MX v061 roller review\n\nActual source terrain, HMF materials, saved wall and asphalt meshes. Lighting/filtering are approximate; these are not game screenshots.\n\nThe roller is about 29m long, has a 9m-wide riding crest and rounded 15m-wide shoulders. Maximum added height is 1.90m. The wall, asphalt and existing double are unchanged. The launch face is shallow (about 9 degrees); no landing has been added.\n\nSimplified ballistics only: wall clearance and landing are estimated, and MX Bikes suspension/tyres are not simulated. A riding test is needed after approval. No native final compilation has been started.\n',encoding='utf-8')
 archive=R/'BUILD/Orlando_v061_Wall_Roller_Previews.zip';temp=archive.with_suffix('.writing.zip')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in [r['file'] for r in rows]+sheets+['Review_Manifest.json','Read_Me.txt']:z.write(OUT/name,name)
 with zipfile.ZipFile(temp) as z:assert z.testzip() is None
 temp.replace(archive);os.utime(archive,None);save(S/'preview_archive.json',dict(file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),final_compilation_started=False))
 print('V061_ROLLER_PREVIEWS_READY',archive,flush=True)

def main():
 OUT.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True,parents=True)
 assert json.loads((O/'validation.json').read_text())['checks_pass'];meshes,textures=scene();rows=[]
 selected=VIEWS if len(sys.argv)==1 else [v for v in VIEWS if v['id'] in sys.argv[1:]]
 for v in selected:rows.append(render_one(v,meshes,textures))
 if len(selected)==len(VIEWS):
  rows.append(render_one(VIEWS[2],meshes,textures,before=True));package(rows)

if __name__=='__main__':main()
