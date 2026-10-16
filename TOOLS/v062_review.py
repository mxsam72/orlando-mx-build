"""Matched v062 material/daylight previews on unchanged v061 terrain."""
import gc,json,math,os,sys,time,zipfile
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
from v062_trials import R,O,S,CACHE,BASE,METHODS,Circuit,source,baseline,sha,save
from v049_previews import font
import v058_render as ray
import v058_full_review as material
import v061_review as camera

OUT=R/'BUILD/v062_review';W,H=1600,1000
VIEWS=[
 dict(id='01',title='Corner 01 / approaching the turn',eye_s=68.,target_s=98.,eye_h=1.85,target_h=.35,eye_l=0.,target_l=0.,fov=66.),
 dict(id='02',title='Corner 01 / full berm and riding line',eye_s=78.,target_s=103.,eye_h=6.,target_h=.35,eye_l=-9.,target_l=0.,fov=64.),
 dict(id='03',title='R03 table-single / takeoff face',eye_s=226.,target_s=249.,eye_h=1.8,target_h=.55,eye_l=0.,target_l=0.,fov=64.),
 dict(id='04',title='Corner 03 / landing exit into the turn',eye_s=270.,target_s=294.,eye_h=1.85,target_h=.35,eye_l=0.,target_l=0.,fov=65.),
 dict(id='05',title='Corner 03 / full width and boundary',eye_s=276.,target_s=301.,eye_h=6.,target_h=.35,eye_l=-9.,target_l=0.,eye_xzy_m=[230.,269.,19.],target_xzy_m=[250.,289.,3.5],fov=64.),
 dict(id='06',title='R04 / flatter riding surface and face',eye_s=316.,target_s=341.,eye_h=1.85,target_h=.35,eye_l=0.,target_l=0.,fov=64.),
 dict(id='07',title='Corner 09 / approach after R10',eye_s=860.,target_s=885.,eye_h=2.0,target_h=.40,eye_l=0.,target_l=0.,fov=65.),
]
TITLES={'REF':'Current v060 dirt',**{m:METHODS[m]['title'] for m in METHODS}}

class Materials(material.ProductionMaterials):
 def __init__(self,method):
  self.method=method;self.resolve=baseline if method=='REF' else lambda name:source(name,method)
  material.O=BASE if method=='REF' else O/method;material.source=self.resolve
  def shader(name):
   try:return self.resolve(str(__import__('pathlib').Path(name).with_suffix('.shd')))
   except FileNotFoundError:return None
  material.old_shader=shader;super().__init__()
  self.key=sha(S/'trial_validation.json')+sha(R/'TOOLS/v062_trials.py')+sha(R/'TOOLS/v062_review.py')
 def texture(self,name):
  # The new macro colour is deliberately different from the repeated photo.
  if name not in self.textures:self.textures[name]=ray.Texture(self.resolve(name))
  return self.textures[name]
 def alpha(self,name,ctx):
  if name is None:return np.ones(len(ctx['x']),np.float32)
  if name not in self.masks:self.masks[name]=np.asarray(Image.open(self.resolve(name)).getchannel('A'))
  a=self.masks[name];return map_coordinates(a,[(600-ctx['z'])/600*a.shape[0]-.5,ctx['x']/600*a.shape[1]-.5],order=1,mode='nearest',output=np.float32)/255

def daylight(c,ctx,old=False):
 light=np.array([2.,-7.,10.]);light/=np.linalg.norm(light);x,z,h=ctx['x'],ctx['z'],ctx['ground']
 if not hasattr(c,'shadow_cache'):c.shadow_cache={}
 key=tuple(ctx['eye'])
 if key in c.shadow_cache:shadow=c.shadow_cache[key]
 else:
  shadow=np.zeros(len(x),bool)
  for distance in np.r_[np.arange(.7,8,.65),np.arange(8,38,1.5)]:
   obstruct=c.terrain.ground(x+light[0]*distance,z+light[1]*distance)>h+light[2]*distance+.075;shadow|=obstruct
  c.shadow_cache[key]=shadow
 return dict(direction=light,shadow=shadow,ambient=np.array([.44,.49,.56] if old else [.30,.34,.40]),sun=np.array([1.,.97,.90]),fog=.00030 if old else .00018)

def shade(ctx,rgb,raw,ids,lighting):
 tn=raw[:,:3]/127.5-1;tn/=np.maximum(np.linalg.norm(tn,axis=1,keepdims=True),1e-8)
 n=tn[:,0,None]*ctx['tangent']+tn[:,1,None]*ctx['bitangent']+tn[:,2,None]*ctx['base'];n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)
 direct=np.maximum(n@lighting['direction'],0)*np.where(lighting['shadow'],.08,1.)
 diffuse=lighting['ambient'][None,:]*.65+lighting['sun'][None,:]*direct[:,None]*.85
 colour=np.clip((rgb/255)**2.2*diffuse,0,1)**(1/2.2)*255
 points=np.c_[ctx['x'],ctx['z'],ctx['ground']];distance=np.linalg.norm(points-ctx['eye'],axis=1);fog=1-np.exp(-lighting['fog']*distance)
 colour=colour*(1-fog[:,None])+np.array([189.,207.,222.])*fog[:,None]
 image=np.empty((W*H,3),np.uint8);image[:]=[157,194,226];image[ids]=np.uint8(np.rint(np.clip(colour,0,255)))
 return Image.fromarray(image.reshape(H,W,3))

def trace(c,view):
 camera.W=W;camera.H=H;ray.WIDTH=W;ray.HEIGHT=H;ray.CACHE=CACHE/'rays';ray.CACHE.mkdir(parents=True,exist_ok=True)
 v=dict(view)
 if 'eye_xzy_m' not in v:v['eye_xzy_m']=ray.location(c,v['eye_s'],v['eye_l'],v['eye_h']).tolist()
 if 'target_xzy_m' not in v:v['target_xzy_m']=ray.location(c,v['target_s'],v['target_l'],v['target_h']).tolist()
 return camera.trace(c,v)

def image_for(c,m,v,old_light=False):
 label=m.method+('_oldlight' if old_light else '');record=OUT/(f'render_{label}_'+v['id']+'.json')
 if record.is_file():
  old=json.loads(record.read_text());p=OUT/old['file']
  if old.get('key')==m.key and old['view']==v and p.is_file() and sha(p)==old['sha256']:
   print('CHECKED_RENDER_REUSED',p.name,flush=True);return old
 t=time.monotonic();data=trace(c,v);ctx,ids=material.context(c,data);rgb,n,stats=m.composite(ctx);light=daylight(c,ctx,old_light);im=shade(ctx,rgb,n,ids,light)
 d=ImageDraw.Draw(im);d.rectangle((0,0,W,82),fill=(22,25,29))
 d.text((18,9),TITLES[m.method]+' | '+v['title'],font=font(24),fill='white')
 d.text((18,47),('Original daylight control' if old_light else 'Same proposed daylight')+' | Actual terrain/material source render; scenery omitted | Not in-game',font=font(17),fill=(204,216,224))
 p=OUT/(f'Orlando_v062_{label}_'+v['id']+'.jpg');im.save(p,quality=96,subsampling=0)
 # Track-only contrast at medium distance, on the same rendered camera.
 dist=np.linalg.norm(np.c_[ctx['x'],ctx['z'],ctx['ground']]-ctx['eye'],axis=1);dirt=c.dirt;sc=map_coordinates(dirt,[(600-ctx['z'])/600*len(dirt)-.5,ctx['x']/600*len(dirt)-.5],order=1,mode='nearest')
 sample=np.flatnonzero((dist>12)&(dist<45)&(sc>.9));lum=rgb@np.array([.2126,.7152,.0722]);contrast=float(np.std(lum[sample])) if len(sample) else 0.
 row=dict(key=m.key,file=p.name,method=m.method,original_light=old_light,view=v,sha256=sha(p),eye_xzy_m=data['eye'].tolist(),target_xzy_m=data['target'].tolist(),seconds=round(time.monotonic()-t,2),terrain_pixels=len(ids),medium_distance_albedo_luma_std=contrast,medium_distance_pixels=len(sample),layers=stats)
 save(OUT/(f'render_{label}_'+v['id']+'.json'),row);print('RENDER_READY',p.name,row['seconds'],'seconds;',round(contrast,2),'medium-distance contrast',flush=True)
 del data,ctx,rgb,n;gc.collect();return row

def package(rows):
 sheets=[];tw,th=1000,625
 for v in VIEWS:
  sheet=Image.new('RGB',(tw*2,th*2+74),(22,25,29));d=ImageDraw.Draw(sheet)
  d.text((18,9),v['id']+'  '+v['title']+' — reference / A / B / C',font=font(27),fill='white')
  d.text((18,46),'Matching geometry, camera, sun and daylight. Source previews; scenery omitted.',font=font(18),fill=(204,216,224))
  for i,m in enumerate(['REF','A','B','C']):
   row=next(r for r in rows if r['method']==m and r['view']['id']==v['id'] and not r['original_light']);im=Image.open(OUT/row['file']).resize((tw,th),Image.Resampling.LANCZOS);sheet.paste(im,((i%2)*tw,74+(i//2)*th))
  p=OUT/('Orlando_v062_Compare_'+v['id']+'.jpg');sheet.save(p,quality=96,subsampling=0);sheets.append(p.name)
 # One lighting control holds the candidate material fixed.
 lightrows=[r for r in rows if r['method']=='B' and r['view']['id']=='04'];sheet=Image.new('RGB',(W*2,H))
 for i,r in enumerate(sorted(lightrows,key=lambda r:not r['original_light'])):sheet.paste(Image.open(OUT/r['file']),(i*W,0))
 lp=OUT/'Orlando_v062_Daylight_Control.jpg';sheet.save(lp,quality=96,subsampling=0);sheets.append(lp.name)
 manifest=dict(version='v062 three dirt trials',source_only=True,in_game_captures=False,scenery_omitted=True,final_compilation_started=False,wall_roller_preserved=True,terrain_sha256=sha(BASE/'terrain.raw'),scenery_sha256=sha(BASE/'scenery.fbx'),trial_validation_sha256=sha(S/'trial_validation.json'),resolution=[W,H],designs=METHODS,renders=rows,comparisons=sheets)
 save(OUT/'Review_Manifest.json',manifest);save(S/'preview_review.json',manifest)
 (OUT/'Read_Me.txt').write_text('Orlando MX v062 dirt comparisons\n\nA: heavy tilled loam. B: grooves flowing through corners and up faces. C: broken riding ruts with loose clods and churned shoulders.\n\nSeven matching cameras include corner 01, the R03 face, corner 03, R04 and corner 09 after R10. Each comparison sheet uses current v060 dirt at top left, A at top right, B at bottom left and C at bottom right. All four use identical proposed daylight. Separate daylight control holds style B fixed and compares original/proposed clear-day ambient and fog.\n\nThese are actual material and terrain source renders with approximate lighting, mip filtering and terrain shadows. Scenery is omitted. They are not MX Bikes screenshots. A compiled in-game test is required after choosing a method.\n\nAll candidates preserve the complete v061 terrain, wall roller, road, big double, MX jumps/corners, route, vehicles and scenery. No extra terrain layers or texture allocation. No final native compilation has started.\n',encoding='utf-8')
 archive=R/'BUILD/Orlando_v062_Dirt_Comparisons.zip';temp=archive.with_suffix('.writing.zip')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in [r['file'] for r in rows]+sheets+['Review_Manifest.json','Read_Me.txt']:z.write(OUT/name,name)
 with zipfile.ZipFile(temp) as z:assert z.testzip() is None
 temp.replace(archive);os.utime(archive,None);save(S/'preview_archive.json',dict(file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive)))
 print('V062_COMPARISONS_READY',len(rows),'renders',archive,flush=True)

def main():
 OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True);assert json.loads((S/'trial_validation.json').read_text())['checks_pass'];c=Circuit();rows=[]
 args=sys.argv[1:];methods=[m for m in ['REF','A','B','C'] if not args or m in args];selected=[v for v in VIEWS if not any(a.isdigit() for a in args) or v['id'] in args]
 for method in methods:
  m=Materials(method)
  for v in selected:rows.append(image_for(c,m,v))
  if method=='B' and len(selected)==len(VIEWS):rows.append(image_for(c,m,VIEWS[3],old_light=True))
  del m;gc.collect()
 if not args:package(rows)

if __name__=='__main__':main()
