"""Matched actual-source previews: original B / original C / v064 hybrid."""
import gc,json,os,sys,time,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from v064_hybrid import R,O,S,Circuit,source,sha,save
from v049_previews import font
import v062_review as previous
import v058_full_review as material

OUT=R/'BUILD/v064_review';OLD=R/'BUILD/v062_review';VIEWS=previous.VIEWS;W,H=1600,1000

class Materials(material.ProductionMaterials):
 def __init__(self):
  self.resolve=source;material.O=O;material.source=source
  def shader(name):
   try:return source(str(Path(name).with_suffix('.shd')))
   except FileNotFoundError:return None
  material.old_shader=shader;super().__init__();self.key=sha(S/'surface_validation.json')+sha(R/'TOOLS/v064_hybrid.py')+sha(R/'TOOLS/v064_review.py')
 def texture(self,name):return previous.Materials.texture(self,name)
 def alpha(self,name,ctx):return previous.Materials.alpha(self,name,ctx)

def one(c,m,v):
 record=OUT/('render_'+v['id']+'.json')
 if record.is_file():
  row=json.loads(record.read_text())
  if row.get('key')==m.key and row['view']==v and (OUT/row['file']).is_file() and sha(OUT/row['file'])==row['sha256']:
   print('CHECKED_HYBRID_RENDER_REUSED',v['id'],flush=True);return row
 started=time.monotonic();data=previous.trace(c,v);ctx,ids=material.context(c,data);rgb,n,stats=m.composite(ctx);im=previous.shade(ctx,rgb,n,ids,previous.daylight(c,ctx))
 draw=ImageDraw.Draw(im);draw.rectangle((0,0,W,82),fill=(22,25,29));draw.text((18,9),'v064 - B corners + C elsewhere | '+v['title'],font=font(24),fill='white')
 draw.text((18,47),'Original B/C methods | Actual terrain/material source render; scenery omitted | Not in-game',font=font(17),fill=(204,216,224))
 path=OUT/('Orlando_v064_Hybrid_'+v['id']+'.jpg');im.save(path,quality=96,subsampling=0);references=[]
 for method in ['B','C']:
  ref=json.loads((OLD/('render_'+method+'_'+v['id']+'.json')).read_text());assert ref['view']==v
  assert ref['eye_xzy_m']==data['eye'].tolist() and ref['target_xzy_m']==data['target'].tolist() and sha(OLD/ref['file'])==ref['sha256']
  references.append(dict(method=method,file=ref['file'],sha256=ref['sha256']))
 row=dict(key=m.key,file=path.name,sha256=sha(path),view=v,eye_xzy_m=data['eye'].tolist(),target_xzy_m=data['target'].tolist(),references=references,
  seconds=round(time.monotonic()-started,2),layers=stats)
 save(record,row);print('HYBRID_RENDER_READY',path.name,row['seconds'],'seconds',flush=True);del data,ctx,rgb,n;gc.collect();return row

def package(rows):
 comparisons=[];tw,th=1000,625
 for row in rows:
  v=row['view'];sheet=Image.new('RGB',(tw*3,th+74),(22,25,29));draw=ImageDraw.Draw(sheet)
  draw.text((18,9),v['id']+'  '+v['title']+' | Original B / Original C / Hybrid',font=font(27),fill='white')
  draw.text((18,46),'Same camera, geometry, photographs and daylight. B in corners; C on straights and jumps. Source previews.',font=font(19),fill=(204,216,224))
  for i,ref in enumerate(row['references']):sheet.paste(Image.open(OLD/ref['file']).resize((tw,th),Image.Resampling.LANCZOS),(i*tw,74))
  sheet.paste(Image.open(OUT/row['file']).resize((tw,th),Image.Resampling.LANCZOS),(tw*2,74))
  path=OUT/('Orlando_v064_Compare_'+v['id']+'.jpg');sheet.save(path,quality=96,subsampling=0);comparisons.append(dict(file=path.name,sha256=sha(path)))
 manifest=dict(version='v064 original B corners plus C elsewhere',source_only=True,in_game_captures=False,scenery_omitted=True,final_compilation_started=False,
  cameras_and_daylight_match_original_B_and_C=True,wall_roller_preserved=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
  surface_validation_sha256=sha(S/'surface_validation.json'),resolution=[W,H],renders=rows,comparisons=comparisons)
 save(OUT/'Review_Manifest.json',manifest);save(S/'preview_review.json',manifest)
 (OUT/'Read_Me.txt').write_text('Orlando MX v064 - Original B corners + C elsewhere\n\nOriginal v062 B flowing grooves cover all 14 named corner arcs. Original v062 C ridden loam covers the remaining surface, including straights, jump faces, landings and start lane. Five metre blends outside each corner avoid hard joins. Rejected dense v063 is not used.\n\nSeven hybrid photographs match the previous B/C cameras. Each comparison plate has original B on the left, original C in the centre, and the hybrid on the right. View 04 matches the previously marked screenshot.\n\nThe whole terrain, wall roller, scenery, van/sign and trucks remain exact. Existing macro normal RGB and packed/wear mask alpha are combined. Photographic RGB, fine scanned normals, normal specular alpha, mask boundaries, lighting, image sizes, 14 HMF layers and texture allocation are preserved.\n\nActual terrain/material source renders with approximate filtering and daylight, omitting scenery; not MX Bikes screenshots. Final native compilation remains on hold for preview approval.\n',encoding='utf-8')
 archive=R/'BUILD/Orlando_v064_B_C_Hybrid_Previews.zip';temp=archive.with_name(archive.stem+'.'+str(os.getpid())+'.tmp.zip')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for row in rows:
   for ref in row['references']:z.write(OLD/ref['file'],ref['file'])
   z.write(OUT/row['file'],row['file'])
  for item in comparisons:z.write(OUT/item['file'],item['file'])
  for name in ['Review_Manifest.json','Read_Me.txt']:z.write(OUT/name,name)
 with zipfile.ZipFile(temp) as z:assert z.testzip() is None
 temp.replace(archive);os.utime(archive,None);save(S/'preview_archive.json',dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size))
 print('V064_HYBRID_PREVIEWS_READY',len(rows),'matching views',archive,flush=True)

def main():
 OUT.mkdir(parents=True,exist_ok=True);assert json.loads((S/'surface_validation.json').read_text())['checks_pass'];c=Circuit();m=Materials();rows=[]
 selected=[VIEWS[i] for i in [4,2,3,1,0,5,6]] if len(sys.argv)==1 else [v for v in VIEWS if v['id'] in sys.argv[1:]]
 for v in selected:rows.append(one(c,m,v))
 if len(selected)==len(VIEWS):package(rows)

if __name__=='__main__':main()
