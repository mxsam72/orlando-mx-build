"""Additional near-surface views to judge the perpendicular pass at useful scale."""
import hashlib,json,os,zipfile
from PIL import Image,ImageDraw
import v058_full_review as review
from v059_review import configure,OUT,CACHE
from v059_surface import R,S,sha,save,Circuit
from v049_previews import font

DETAILS=[
 dict(id='D01',title='Corner 01 / perpendicular marks close-up',eye_s=97.,target_s=101.,eye_h=.75,target_h=.03,eye_l=.3,target_l=.3,fov=59.,path='main'),
 dict(id='D02',title='R04 straight / perpendicular marks close-up',eye_s=322.,target_s=326.,eye_h=.7,target_h=.03,eye_l=0.,target_l=0.,fov=59.,path='main'),
 dict(id='D03',title='R03 takeoff / full-width grooming close-up',eye_s=236.,target_s=240.,eye_h=.75,target_h=.03,eye_l=2.,target_l=2.,fov=59.,path='main'),
 dict(id='D04',title='R14 face / perpendicular marks close-up',eye_s=1040.,target_s=1044.,eye_h=.75,target_h=.03,eye_l=0.,target_l=0.,fov=59.,path='main'),
]

def main():
 configure();c=Circuit();m=review.ProductionMaterials();key=sha(R/'TOOLS/v059_details.py')+sha(R/'V059_OUTPUT/surface_validation.json');rows=[]
 for v in DETAILS:
  p=OUT/f'photo_{v["id"]}.json'
  if p.exists():
   prior=json.loads(p.read_text())
   if prior['key']==key and sha(OUT/prior['file'])==prior['sha256']:rows.append(prior);continue
  rows.append(review.render_one(c,m,v,key))
 sheet=Image.new('RGB',(3200,2070),(22,25,29));d=ImageDraw.Draw(sheet);d.text((20,14),'v059 / near-surface grooming details',font=font(31),fill='white')
 for i,r in enumerate(rows):sheet.paste(Image.open(OUT/r['file']),((i%2)*1600,70+(i//2)*1000))
 sheet.save(OUT/'Orlando_v059_Grooming_Details.jpg',quality=96,subsampling=0);save(OUT/'detail_manifest.json',dict(source_only=True,not_game_captures=True,renders=rows,sheet='Orlando_v059_Grooming_Details.jpg'))
 print('V059_FOUR_DETAIL_VIEWS_READY',flush=True)

def append_to_archive():
 archive=R/'BUILD/Orlando_v059_Full_Track_Photos.zip';temporary=CACHE/'review_with_details.zip';q=json.loads((OUT/'detail_manifest.json').read_text());names=[r['file'] for r in q['renders']]+[q['sheet'],'detail_manifest.json']
 p=S/'full_track_review.json';data=json.loads(p.read_text());data['detail_views']=q
 inner={k:v for k,v in data.items() if k!='archive'}
 save(OUT/'Review_Manifest.json',inner)
 with zipfile.ZipFile(archive) as old,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as new:
  for item in old.infolist():
   if item.filename not in names and item.filename!='Review_Manifest.json':new.writestr(item,old.read(item.filename))
  for name in names:new.write(OUT/name,name)
  new.write(OUT/'Review_Manifest.json','Review_Manifest.json')
 with temporary.open('rb') as f:os.fsync(f.fileno())
 with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
 temporary.replace(archive);os.utime(archive,None)
 data.update(archive=dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size));save(p,data)

if __name__=='__main__':
 import sys
 if '--append' in sys.argv:append_to_archive()
 else:main()
