"""Full-course review of the actual v058 HMF, textures and accepted terrain.

These are terrain/material source renders, not game captures. Approved scenery
is preserved separately and deliberately omitted so dirt remains easy to judge.
No model-generated imagery or substitute dirt geometry is used.
"""
import gc,hashlib,json,os,re,sys,time,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
import v058_render as render
from v058_surface import Circuit,source,baseline,old_shader,layers
from v058_inputs import R,O,M,PREV,sha,save
from v049_previews import font

OUT=R/'BUILD/v058_full_review';CACHE=R/'BUILD/v058_full_cache'
W,H=1600,1000
VERSION='v058';REVIEW_TITLE='Full-track C+B';SOURCE_DIR=R/'V058_SOURCE'

def view(number,title,eye,target,h=1.8,th=.55,l=0.,tl=0.,group='Main course',path='main',fov=64.):
 return dict(id=f'{number:02d}',title=title,eye_s=float(eye),target_s=float(target),eye_h=float(h),target_h=float(th),eye_l=float(l),target_l=float(tl),fov=fov,group=group,path=path)

VIEWS=[
 view(1,'Finish tabletop / approach',6,32),
 view(2,'Finish tabletop / landing and exit',29,46,h=7,l=-12,th=.25),
 view(3,'First straight / cultivated loam',58,79,th=.3,l=.2),
 view(4,'Corner 01 / full width and edge',75,103,h=6,l=-9,th=.3),
 view(5,'Triple R02 / jump-face grooves',120,142,h=1.7,th=.65),
 view(6,'Corner 02 / berm and track edge',192,211,h=5,l=-8,th=.3),
 view(7,'Table-single R03 / takeoff',226,249),
 view(8,'Table-single R03 / corrected landing',253,269,h=7,l=-12,th=.2),
 view(9,'Corner 03 / landing exit',270,294,h=6,l=-9,th=.3),
 view(10,'Straight R04 / flat dirt',321,343,th=.3),
 view(11,'Corner 04 / berm and edge',341,359,h=6,l=-8,th=.3),
 view(12,'Double R05 / approach and face',392,415),
 view(13,'Corner 05 / long turn',438,465,h=7,l=-10,th=.3),
 view(14,'Corner 06 / linked turn',493,513,h=6,l=-8,th=.3),
 view(15,'Ant hill R07 / jump-face detail',535,555),
 view(16,'Corner 07 / full riding surface',565,590,h=6,l=-10,th=.3),
 view(17,'Straight R08 / loam and edge',613,637,th=.3),
 view(18,'Corner 08 / berm and exit',660,685,h=6,l=-9,th=.3),
 view(19,'Double R09 / face and crest',728,754),
 view(20,'Tabletop R10 / long jump face',782,810),
 view(21,'Corner 09 / berm and edge',860,885,h=7,l=-8,th=.3),
 view(22,'R11 entry single and double',901,924,h=3.5,th=.65),
 view(23,'Rollers R12 / cultivated faces',940,963,h=4,th=.4),
 view(24,'Corner 10 / roller exit',978,1004,h=6,l=-9,th=.3),
 view(25,'Triple R14 / takeoff grooves',1028,1052),
 view(26,'Triple R14 / landing and runout',1080,1105,h=7,l=-12,th=.3),
 view(27,'Corner 11 / linked jumps',1136,1159,h=7,l=-9,th=.3),
 view(28,'Single R15 / face and soil',1167,1187),
 view(29,'Table R16 / approach and deck',1195,1221,h=2.2),
 view(30,'Corner 12 / full width and edge',1257,1282,h=6,l=-8,th=.3),
 view(31,'Corner 13 / roller entry',1320,1348,h=6,l=-9,th=.3),
 view(32,'Rollers R17 / first section',1350,1381,h=6,l=-7,th=.4),
 view(33,'Rollers R17 / final section',1390,1419,h=5,l=-8,th=.4),
 view(34,'Inside roller R18 / inside riding line',1449,1460,h=2.2,l=3.4,tl=3.4),
 view(35,'Corner 14 / return to finish',1460,1482,h=7,l=-9,th=.3),
 view(36,'Close-up / clods, grooves and track edge',56,59.2,h=.60,th=.02,l=3.1,tl=3.,fov=59.),
 view(37,'Start straight / soil and cultivation',8,40,h=4,th=.35,path='start'),
 view(38,'Start merge / surface transition',132,171,h=6,th=.35,l=-7,path='start'),
]

class ProductionMaterials:
 def __init__(self):
  self.textures={};self.masks={};self.records=[]
  self.blocks=list(layers((O/'compiled_track.hmf').read_text()))
  for index,block in self.blocks:
   name=re.search(r'(?m)^\s*map\s*=\s*(\S+)',block)[1]
   rep=float(re.search(r'repetitions\s*=\s*([\d.]+)',block)[1])
   mm=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
   sh=source(name).with_suffix('.shd')
   if not sh.is_file():
    try:sh=old_shader(name)
    except StopIteration:sh=None
   normal=None;nrep=1.
   if sh:
    bump=re.search(r'bump\s*\{([^}]+)\}',sh.read_text())
    if bump:
     normal=re.search(r'map\s*=\s*(\S+)',bump[1])[1]
     rr=re.search(r'repetitions\s*=\s*([\d.]+)',bump[1]);nrep=float(rr[1]) if rr else 1.
     nrep=nrep or rep
   self.records.append(dict(index=index,map=name,rep=rep,normal=normal,nrep=nrep,mask=mm[1] if mm else None))
 def texture(self,name):
  # The production colour slots are byte-identical; share their CPU mip cache.
  if name=='v044_route_detail.tga':name='v045_loose.tga'
  path=source(name)
  if name not in self.textures:self.textures[name]=render.Texture(path)
  return self.textures[name]
 def alpha(self,name,ctx):
  if name is None:return np.ones(len(ctx['x']),np.float32)
  if name not in self.masks:self.masks[name]=np.asarray(Image.open(source(name)).getchannel('A'))
  a=self.masks[name]
  return map_coordinates(a,[(600-ctx['z'])/600*a.shape[0]-.5,ctx['x']/600*a.shape[1]-.5],order=1,mode='nearest',output=np.float32)/255
 def composite(self,ctx):
  size=len(ctx['x']);trans=np.ones(size,np.float32);rgb=np.zeros((size,3),np.float32);normal=np.zeros((size,4),np.float32);stats=[]
  # Exact over-composition written from the top down. Occluded layers never
  # need texture sampling; this changes preview time, not the game material.
  for p in reversed(self.records):
   alpha=self.alpha(p['mask'],ctx);weight=trans*alpha;idx=np.flatnonzero(weight>0)
   if len(idx):
    rgb[idx]+=self.texture(p['map']).sample(ctx,p['rep'],idx)[:,:3]*weight[idx,None]
    if p['normal']:
     sampled=self.texture(p['normal']).sample(ctx,p['nrep'],idx)
     n=np.empty((len(idx),4),np.float32);n[:]=[127.5,127.5,255,0];n[:,:sampled.shape[1]]=sampled
    else:n=np.broadcast_to(np.array([127.5,127.5,255,0],np.float32),(len(idx),4))
    normal[idx]+=n*weight[idx,None]
   trans*=1-alpha
   stats.append(dict(layer=p['index'],sampled_pixels=len(idx),colour=p['map'],colour_repeats=p['rep'],normal=p['normal'],normal_repeats=p['nrep']))
  assert np.max(trans)<1e-6
  return rgb,normal,stats

def route_for(c,path):
 if path=='main':return c
 class Start:
  q=c.start;v=c.start_v;terrain=c.terrain
 return Start()

def context(c,data):
 valid=data['hit']&(data['x']>=0)&(data['x']<=600)&(data['z']>=0)&(data['z']<=600)
 ids=np.flatnonzero(valid);n=len(data['x']);ctx={k:(v[ids] if isinstance(v,np.ndarray) and v.ndim>0 and len(v)==n else v) for k,v in data.items()}
 hx,hz=c.terrain.slope(ctx['x'],ctx['z'])
 base=np.stack([-hx,-hz,np.ones_like(hx)],1);base/=np.linalg.norm(base,axis=1,keepdims=True)
 tangent=np.stack([np.ones_like(hx),np.zeros_like(hx),hx],1);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
 ctx.update(base=base,tangent=tangent,bitangent=np.cross(base,tangent));return ctx,ids

def shade(ctx,rgb,raw_normal,ids):
 tn=raw_normal[:,:3]/127.5-1;tn/=np.maximum(np.linalg.norm(tn,axis=1,keepdims=True),1e-7)
 n=tn[:,0,None]*ctx['tangent']+tn[:,1,None]*ctx['bitangent']+tn[:,2,None]*ctx['base'];n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-7)
 light=np.array([2.,-7.,10.],np.float32);light/=np.linalg.norm(light)
 diffuse=.38+.70*np.maximum(n@light,0)
 point=np.stack([ctx['x'],ctx['z'],ctx['ground']],1);vv=ctx['eye']-point;vv/=np.maximum(np.linalg.norm(vv,axis=1,keepdims=True),1e-7)
 halfway=vv+light;halfway/=np.maximum(np.linalg.norm(halfway,axis=1,keepdims=True),1e-7)
 specular=raw_normal[:,3]/255*np.maximum(np.sum(n*halfway,axis=1),0)**8*.45
 pixels=np.uint8(np.rint(np.clip((rgb/255)**2.2*diffuse[:,None]+specular[:,None],0,1)**(1/2.2)*255))
 image=np.empty((W*H,3),np.uint8);image[:]=[157,194,226];image[ids]=pixels
 return Image.fromarray(image.reshape(H,W,3))

def render_one(c,m,v,key):
 t=time.monotonic();data=render.trace(route_for(c,v['path']),v);ctx,ids=context(c,data)
 rgb,n,stats=m.composite(ctx);im=shade(ctx,rgb,n,ids)
 draw=ImageDraw.Draw(im);draw.rectangle((0,0,W,68),fill=(22,25,29))
 draw.text((16,8),v['id']+'  '+v['title'],font=font(25),fill='white')
 draw.text((16,39),REVIEW_TITLE+' | Terrain/material preview; scenery omitted | Not an in-game capture',font=font(17),fill=(199,211,219))
 path=OUT/(f'Orlando_{VERSION}_'+v['id']+'.jpg');im.save(path,quality=96,subsampling=0)
 eye=data['eye'];target=data['target'];delta=target[:2]-eye[:2];distance=np.linalg.norm(delta);direction=delta/distance
 positions=np.stack([ctx['x'],ctx['z']],1)-eye[:2]
 near=np.sum(positions*direction,axis=1)
 # Visible station range is recorded for the map and coverage audit; include
 # only the nearest 80m, since a second lane can appear in the far background.
 nearids=np.flatnonzero((near>0)&(near<80))
 ss,ll=c.coords(ctx['x'][nearids],ctx['z'][nearids]);scope=c.scope(ctx['x'][nearids],ctx['z'][nearids])
 report=dict(key=key,file=path.name,sha256=sha(path),view=v,eye_xzy_m=eye.tolist(),target_xzy_m=target.tolist(),terrain_pixels=len(ids),
  photographic_pixels=int(np.count_nonzero(scope>.5)),layers=stats,seconds=round(time.monotonic()-t,2))
 save(OUT/('photo_'+v['id']+'.json'),report);print('PHOTO_READY',v['id'],v['title'],report['seconds'],'seconds',flush=True)
 del ctx,data,rgb,n;gc.collect();return report

def package(c,rows):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(13,14));fig.patch.set_facecolor('#f0eae0');ax.set_facecolor('#f0eae0')
 ax.plot(c.p[:,0],c.p[:,1],lw=12,color='#b0a18b',solid_capstyle='round');ax.plot(c.p[:,0],c.p[:,1],lw=1,color='#614b35')
 ax.plot(c.start[:,0],c.start[:,1],lw=7,color='#c68941')
 for v in VIEWS:
  route=route_for(c,v['path']);e=render.location(route,v['eye_s'],v['eye_l'],v['eye_h']);t=render.location(route,v['target_s'],v['target_l'],v['target_h'])
  ax.annotate('',xy=t[:2],xytext=e[:2],arrowprops=dict(arrowstyle='->',color='#317887',lw=1.4,alpha=.8))
  offset=(0,22) if v['id']=='36' else (12,-5) if v['id']=='03' else (0,0)
  ax.annotate(v['id'],e[:2],xytext=offset,textcoords='offset points',ha='center',va='center',fontsize=8.5,fontweight='bold',color='white',bbox=dict(boxstyle='circle,pad=.2',fc='#1d5561',ec='white',lw=.7))
 ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
 for spine in ax.spines.values():spine.set_visible(False)
 ax.set_title('Orlando MX — full-course photo locations\n38 views • '+REVIEW_TITLE,fontsize=19,pad=20)
 ax.text(.5,-.02,'Numbers match the individual photos and the contact sheets. Arrows show viewing direction.',transform=ax.transAxes,ha='center',fontsize=10,color='#4e514f')
 fig.tight_layout();fig.savefig(OUT/f'Orlando_{VERSION}_Photo_Locations.jpg',dpi=180);plt.close(fig)
 sheets=[]
 for page,start in enumerate(range(0,len(rows),8),1):
  batch=rows[start:start+8];tw,th=1000,625;sheet=Image.new('RGB',(tw*2,th*((len(batch)+1)//2)+100),(22,25,29));d=ImageDraw.Draw(sheet)
  d.text((22,12),f'Orlando MX | {REVIEW_TITLE} | Photo sheet {page} / 5',font=font(27),fill='white')
  d.text((22,57),'Actual terrain and material source previews. Full-resolution photos are included in the ZIP.',font=font(20),fill=(199,211,219))
  for i,row in enumerate(batch):
   im=Image.open(OUT/row['file']);im=im.resize((tw,th),Image.Resampling.LANCZOS);sheet.paste(im,((i%2)*tw,100+(i//2)*th))
  path=OUT/f'Orlando_{VERSION}_Photo_Sheet_{page}.jpg';sheet.save(path,quality=96,subsampling=0);sheets.append(path.name)
 manifest=dict(checks_pass=True,version=VERSION,approved_method=REVIEW_TITLE,source_only=True,in_game_captures=False,scenery_omitted=True,
  final_compilation_started=False,photo_count=len(rows),all_14_corners_have_dedicated_views=True,
  all_jump_groups_have_views=True,start_straight_and_merge_have_views=True,resolution=[W,H],
  terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),hmf_sha256=sha(O/'compiled_track.hmf'),
  source_validation_sha256=sha(O/'surface_validation.json'),map=f'Orlando_{VERSION}_Photo_Locations.jpg',sheets=sheets,renders=rows)
 save(OUT/'Review_Manifest.json',manifest)
 (OUT/'Read_Me.txt').write_text(f'Orlando MX {VERSION} — {REVIEW_TITLE}\n\n38 photos cover all 14 corners, jump groups, straights, start lane and merge.\nThe numbered map shows every camera. Photo sheets provide an overview; individual JPEGs are 1600 x 1000.\n\nThese are actual terrain/material source renders, not MX Bikes captures. Scenery is omitted to keep the dirt visible. The approved van, sign and truck changes are retained unchanged in source.\n\nFinal compilation is on hold for approval of this review. Actual in-game lighting, texture filtering, RAM/VRAM use and FPS remain to be checked after compilation.\n',encoding='utf-8')
 archive=R/f'BUILD/Orlando_{VERSION}_Full_Track_Photos.zip'
 temporary=CACHE/f'Full_Track_Photos_{os.getpid()}.tmp.zip'
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in [r['file'] for r in rows]+sheets+[manifest['map'],'Review_Manifest.json','Read_Me.txt']:z.write(OUT/name,name)
 with temporary.open('rb') as f:os.fsync(f.fileno())
 with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
 expected=sha(temporary);temporary.replace(archive);os.utime(archive,None);assert sha(archive)==expected
 save(SOURCE_DIR/'full_track_review.json',dict(manifest,archive=dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size)))
 print(VERSION.upper()+'_FULL_TRACK_REVIEW_READY',len(rows),'photos',archive,flush=True)

def main():
 OUT.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True,parents=True);render.CACHE=CACHE;render.WIDTH=W;render.HEIGHT=H
 assert json.loads((O/'surface_validation.json').read_text())['checks_pass']
 c=Circuit();m=ProductionMaterials();rows=[]
 inputs=[R/'TOOLS/v058_full_review.py',R/'TOOLS/v058_render.py',O/'compiled_track.hmf',O/'surface_validation.json']
 key=hashlib.sha256(''.join(sha(p) for p in inputs).encode()).hexdigest()
 selected=VIEWS if len(sys.argv)==1 else [v for v in VIEWS if v['id'] in sys.argv[1:]]
 for v in selected:
  cache=OUT/('photo_'+v['id']+'.json')
  if cache.exists():
   prior=json.loads(cache.read_text())
   if prior['key']==key and prior['view']==v and (OUT/prior['file']).is_file() and sha(OUT/prior['file'])==prior['sha256']:
    rows.append(prior);print('CHECKED_PHOTO_REUSED',v['id'],flush=True);continue
  rows.append(render_one(c,m,v,key))
 if len(selected)==len(VIEWS):package(c,rows)

if __name__=='__main__':main()
