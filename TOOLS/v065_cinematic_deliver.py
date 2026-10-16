"""Validate and bundle the cinematic source renders for posting."""
from pathlib import Path
import hashlib,json,zipfile,shutil
from PIL import Image,ImageDraw,ImageFont
from v065_start import R,O,sha,save,TERRAIN_SHA,SCENERY_SHA

SOURCE=R/'DOCUMENTATION/v065_cinematic'
OUT=R.parent/'OrlandoMX-v065-Cinematic-Renders'
RUN_URL='https://github.com/mxsam72/orlando-mx-build/actions?query=branch%3Arebuild-v065'
SHOTS=[('01_orlando_hero','Aerial overview'),('02_flowing_corner','Flowing corner'),
 ('03_tabletop','Tabletop face'),('04_rhythm_section','Rhythm section'),
 ('05_speedway_double','Speedway double'),('06_start_straight','C dirt start straight'),
 ('09_full_track_overview','Full course overview')]

def font(size,bold=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
def main():
 OUT.mkdir(parents=True,exist_ok=True);proof=json.loads((O/'surface_validation.json').read_text());assert proof['checks_pass']
 assert sha(O/'terrain.raw')==TERRAIN_SHA and sha(O/'scenery.fbx')==SCENERY_SHA
 rows=[];sheet=Image.new('RGB',(1600,1510),(24,27,28));draw=ImageDraw.Draw(sheet)
 draw.text((28,22),'ORLANDO MX  /  v065',font=font(31,True),fill=(245,241,232))
 draw.text((30,66),'Six cinematic views + full course aerial  ·  2560 × 1440 originals',font=font(20),fill=(182,185,183))
 for i,(name,title) in enumerate(SHOTS):
  src=SOURCE/(name+'.png');dest=OUT/('OrlandoMX_v065_'+name+'.png')
  with Image.open(src) as im:
   im.load();assert im.size==(2560,1440) and im.mode=='RGB',(name,im.size,im.mode)
   # Uniform or empty frames indicate a failed render, not a deliverable.
   assert max(hi-lo for lo,hi in im.getextrema())>120
   thumb=im.resize((772,434),Image.Resampling.LANCZOS)
  shutil.copy2(src,dest)
  if i<6:
   x=14+(i%2)*800;y=110+(i//2)*460;sheet.paste(thumb,(x,y))
   draw.text((x+10,y+441),title,font=font(16),fill=(222,220,211))
  rows.append(dict(file=dest.name,title=title,size=[2560,1440],sha256=sha(dest)))
 draw.text((28,1490),'Rendered from actual track assets with presentation lighting; these are not in-game captures.',font=font(14),fill=(175,179,177))
 preview=OUT/'OrlandoMX_v065_Cinematic_Preview.jpg';sheet.save(preview,quality=94,subsampling=0)
 text=('Orlando MX v065 — cinematic renders\n\nSeven clean 2560 x 1440 PNG images, ready to post.\n\n'
  'Rendered in Blender Cycles from the actual track terrain, photographic materials and scenery. '
  'The lighting and cameras are cinematic presentation settings; these are source renders, not MX Bikes screenshots.\n\n'
  'v065 extends style C across the opening start straight and clears the circled grass strip to its left. '
  'The approved B corners, remaining C surfaces, all terrain heights, wall roller, vehicles and scenery are retained. '
  'Game texture slots, dimensions and layer count are unchanged.\n\nNative game build status:\n'+RUN_URL+'\n')
 (OUT/'Readme.txt').write_text(text,encoding='utf-8')
 save(OUT/'Render_Provenance.json',dict(source_render=True,in_game_capture=False,version='v065',terrain_sha256=TERRAIN_SHA,
  scenery_sha256=SCENERY_SHA,surface_validation_sha256=sha(O/'surface_validation.json'),renderer='Blender Cycles 4.5.3 CPU, AgX',
  lighting='Cinematic presentation, separate from approved game lighting',images=rows))
 archive=OUT/'OrlandoMX_v065_Cinematic_Renders.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for row in rows:z.write(OUT/row['file'],row['file'])
  for name in ['Readme.txt','Render_Provenance.json']:z.write(OUT/name,name)
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.infolist())==9
 print(json.dumps(dict(checks_pass=True,folder=str(OUT),images=rows,preview=str(preview),archive=str(archive),archive_bytes=archive.stat().st_size),indent=2))
if __name__=='__main__':main()
