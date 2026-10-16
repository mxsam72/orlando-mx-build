"""Package completed, visually inspected source renders for user approval."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1]
ROWS=[
 ('09_full_track_overview','01_Full_layout','Full layout'),
 ('02_flowing_corner','02_Flowing_corner','B corner | Flowing grooves'),
 ('03_tabletop','03_Jump_face','Jump face | C soil'),
 ('04_rhythm_section','04_Rhythm_section','Rhythm section'),
 ('06_start_straight','05_Start_straight','Start straight'),
 ('07_rider_height_start','06_Rider_height_start','Start at rider height'),
]

def font(n,bold=False):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf')
 return ImageFont.truetype(str(p),n) if p.exists() else ImageFont.load_default(size=n)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
 out=args.out;out.mkdir(parents=True,exist_ok=True);src=R/'DOCUMENTATION/v067_review'
 manifest=json.loads((src/'renders.json').read_text());spec=json.loads((R/'V067_SOURCE/visual_spec.json').read_text())
 assert manifest['lighting_spec']==spec and manifest['source_version']=='v067'
 assert not manifest['native_compilation_started'] and not manifest['in_game_capture']
 assert len(manifest['renders'])==6
 w,h=1920,1830;sheet=Image.new('RGB',(w,h),(23,27,29));d=ImageDraw.Draw(sheet)
 d.text((36,25),'ORLANDO MX  /  v067',font=font(40,True),fill=(239,230,210))
 d.text((36,80),'Late-morning lighting and dirt review  |  Same track layout',font=font(23),fill=(177,187,189))
 files=[]
 for i,(stem,name,title) in enumerate(ROWS):
  p=src/(stem+'.png');im=Image.open(p);im.load();assert im.size==(1920,1080),p
  dest=out/('OrlandoMX_v067_'+name+'.png');shutil.copyfile(p,dest);files.append(dest)
  x=24+(i%2)*948;y=135+(i//2)*548
  d.text((x,y),title,font=font(22,True),fill=(217,197,163))
  thumb=im.resize((924,520),Image.Resampling.LANCZOS);sheet.paste(thumb,(x,y+28))
 d.rectangle((0,1788,1920,1830),fill=(15,18,19))
 d.text((27,1797),'OFFLINE SOURCE RENDERS  |  Full compilation has not started',font=font(21),fill=(179,188,190))
 sheet_path=out/'OrlandoMX_v067_Preview_Sheet.jpg';sheet.save(sheet_path,quality=95,subsampling=0)
 readme=out/'OrlandoMX_v067_Preview_Notes.txt'
 readme.write_text('ORLANDO MX v067 — PRE-COMPILATION REVIEW\n\n'
  'Six actual-source Blender renders at 1920 x 1080. These are offline source renders, not in-game captures.\n'
  'Lighting target: clear Florida late morning, approximately 11 a.m., with a 45-degree southeast sun.\n'
  'Refined photographic soil grain, clod normals and compacted-soil definition; approved B corners and C soil elsewhere.\n'
  'All terrain samples, riding routes, scenery and grass masks remain identical to v066.\n'
  'No native v067 compilation has started. Review these images before approving the full build.\n'
  'Exact MX Bikes rendering and performance require the later compiled build and in-game testing.\n\n'
  'Source branch: https://github.com/mxsam72/orlando-mx-build/tree/rebuild-v067\n')
 bundle=out/'OrlandoMX_v067_Full_Resolution_Previews.zip'
 with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for p in [*files,sheet_path,readme]:z.write(p,p.name)
  z.write(R/'V067_SOURCE/precompile_validation.json','source_validation.json')
  z.write(R/'V067_SOURCE/visual_spec.json','visual_spec.json')
 with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
 print(json.dumps(dict(files=[str(p) for p in [sheet_path,*files,bundle]],bytes=bundle.stat().st_size)))
if __name__=='__main__':main()
