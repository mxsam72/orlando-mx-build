"""Match the marked v062 B camera to the dense full-width v063 update."""
import gc,json,os,sys,time,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
from v063_dense import R,O,S,BASE,Circuit,source,sha,save
from v049_previews import font
import v062_review as previous
import v058_full_review as material

OUT=R/'BUILD/v063_review';OLD=R/'BUILD/v062_review';VIEWS=previous.VIEWS;W,H=1600,1000

class Materials(material.ProductionMaterials):
 def __init__(self):
  self.resolve=source;material.O=O;material.source=source
  def shader(name):
   try:return source(str(Path(name).with_suffix('.shd')))
   except FileNotFoundError:return None
  material.old_shader=shader;super().__init__();self.key=sha(S/'surface_validation.json')+sha(R/'TOOLS/v063_dense.py')+sha(R/'TOOLS/v063_review.py')
 def texture(self,name):return previous.Materials.texture(self,name)
 def alpha(self,name,ctx):return previous.Materials.alpha(self,name,ctx)

def one(c,m,v):
 record=OUT/('render_'+v['id']+'.json')
 if record.is_file():
  row=json.loads(record.read_text())
  if row.get('key')==m.key and row['view']==v and (OUT/row['file']).is_file() and sha(OUT/row['file'])==row['sha256']:
   print('CHECKED_DENSE_RENDER_REUSED',v['id'],flush=True);return row
 started=time.monotonic();data=previous.trace(c,v);ctx,ids=material.context(c,data);rgb,n,stats=m.composite(ctx);im=previous.shade(ctx,rgb,n,ids,previous.daylight(c,ctx))
 draw=ImageDraw.Draw(im);draw.rectangle((0,0,W,82),fill=(22,25,29));draw.text((18,9),'v063 - Full-width overlapping passes | '+v['title'],font=font(24),fill='white')
 draw.text((18,47),'Same v062 B photo/lighting | Actual terrain/material source render; scenery omitted | Not in-game',font=font(17),fill=(204,216,224))
 path=OUT/('Orlando_v063_Dense_'+v['id']+'.jpg');im.save(path,quality=96,subsampling=0)
 ref=json.loads((OLD/('render_B_'+v['id']+'.json')).read_text());assert ref['view']==v
 assert ref['eye_xzy_m']==data['eye'].tolist() and ref['target_xzy_m']==data['target'].tolist()
 assert sha(OLD/ref['file'])==ref['sha256']
 row=dict(key=m.key,file=path.name,sha256=sha(path),view=v,eye_xzy_m=data['eye'].tolist(),target_xzy_m=data['target'].tolist(),
  previous=dict(file=ref['file'],sha256=ref['sha256']),seconds=round(time.monotonic()-started,2),layers=stats)
 save(record,row);print('DENSE_RENDER_READY',path.name,row['seconds'],'seconds',flush=True);del data,ctx,rgb,n;gc.collect();return row

def package(rows):
 comparisons=[];tw,th=1200,750
 for row in rows:
  v=row['view'];sheet=Image.new('RGB',(tw*2,th+74),(22,25,29));draw=ImageDraw.Draw(sheet)
  draw.text((18,9),v['id']+'  '+v['title']+' | Previous B / Dense full-width passes',font=font(27),fill='white')
  draw.text((18,46),'Identical camera, geometry, photographs and daylight. Source previews; no final compilation.',font=font(19),fill=(204,216,224))
  sheet.paste(Image.open(OLD/row['previous']['file']).resize((tw,th),Image.Resampling.LANCZOS),(0,74))
  sheet.paste(Image.open(OUT/row['file']).resize((tw,th),Image.Resampling.LANCZOS),(tw,74))
  path=OUT/('Orlando_v063_Compare_'+v['id']+'.jpg');sheet.save(path,quality=96,subsampling=0);comparisons.append(dict(file=path.name,sha256=sha(path)))
 manifest=dict(version='v063 dense full-width B',source_only=True,in_game_captures=False,scenery_omitted=True,final_compilation_started=False,
  same_cameras_and_daylight_as_v062_B=True,wall_roller_preserved=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
  surface_validation_sha256=sha(S/'surface_validation.json'),resolution=[W,H],renders=rows,comparisons=comparisons)
 save(OUT/'Review_Manifest.json',manifest);save(S/'preview_review.json',manifest)
 (OUT/'Read_Me.txt').write_text('Orlando MX v063 - dense full-width grooming\n\nEach comparison has the previous v062 B trial on the left and the dense v063 version on the right. The original marked image is camera 04.\n\nPrimary passes overlap at approximately 0.25-0.31m spacing, with an additional pass halfway between every pair and an explicit centre pass. The centre and the full racing width stay worked throughout. Small alternating rims suggest travelling in opposite directions. All marks follow the riding line through corners and up jump faces.\n\nOnly the existing normal RGB atlas and packed-soil alpha blend change. Photographic colour, fine normals, wear mask, lighting, image sizes, 14 HMF layers and texture allocation stay identical to B. All terrain/scenery, including the wall roller, remain exact.\n\nActual material and terrain source renders with approximate filtering and lighting. Scenery omitted; not MX Bikes screenshots. No final native compilation has been started.\n',encoding='utf-8')
 archive=R/'BUILD/Orlando_v063_Dense_Grooming_Previews.zip';temp=archive.with_name(archive.stem+'.'+str(os.getpid())+'.tmp.zip')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for row in rows:z.write(OLD/row['previous']['file'],row['previous']['file']);z.write(OUT/row['file'],row['file'])
  for item in comparisons:z.write(OUT/item['file'],item['file'])
  for name in ['Review_Manifest.json','Read_Me.txt']:z.write(OUT/name,name)
 with zipfile.ZipFile(temp) as z:assert z.testzip() is None
 temp.replace(archive);os.utime(archive,None);save(S/'preview_archive.json',dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size))
 print('V063_DENSE_PREVIEWS_READY',len(rows),'matching views',archive,flush=True)

def main():
 OUT.mkdir(parents=True,exist_ok=True);assert json.loads((S/'surface_validation.json').read_text())['checks_pass'];c=Circuit();m=Materials();rows=[]
 selected=[VIEWS[i] for i in [3,4,2,1,0,5,6]] if len(sys.argv)==1 else [v for v in VIEWS if v['id'] in sys.argv[1:]]
 for v in selected:rows.append(one(c,m,v))
 if len(selected)==len(VIEWS):package(rows)

if __name__=='__main__':main()
