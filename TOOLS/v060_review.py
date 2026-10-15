"""Same-camera source QA at the four representative grooming areas."""
import json,sys
from PIL import Image,ImageDraw
import v058_full_review as review
from v059_details import DETAILS
from v060_surface import R,O,S,source,sha,save,Circuit
from v049_previews import font

OUT=R/'BUILD/v060_review';CACHE=R/'BUILD/v059_cache'
def main():
 OUT.mkdir(parents=True,exist_ok=True);review.OUT=OUT;review.O=O;review.source=source;review.SOURCE_DIR=S
 review.VERSION='v060';review.REVIEW_TITLE='v060 - Tighter grooming';review.render.CACHE=CACHE
 review.render.WIDTH=review.W;review.render.HEIGHT=review.H
 c=Circuit();m=review.ProductionMaterials();key=sha(R/'TOOLS/v060_review.py')+sha(O/'surface_validation.json')
 selected=[v.copy() for v in DETAILS if len(sys.argv)==1 or v['id'] in sys.argv[1:]]
 for v in selected:
  old=json.loads((R/'BUILD/v059_review'/f'photo_{v["id"]}.json').read_text())
  v.update(eye_xzy_m=old['eye_xzy_m'],target_xzy_m=old['target_xzy_m'])
  row=review.render_one(c,m,v,key);path=OUT/f'Orlando_v060_Compare_{v["id"]}.jpg'
  im=Image.new('RGB',(3200,1070),(22,25,29));d=ImageDraw.Draw(im)
  d.text((20,14),'v059 before',font=font(29),fill='white');d.text((1620,14),'v060 tighter spacing',font=font(29),fill='white')
  im.paste(Image.open(R/'BUILD/v059_review'/old['file']),(0,70));im.paste(Image.open(OUT/row['file']),(1600,70));im.save(path,quality=96,subsampling=0)
  save(S/f'photo_check_{v["id"]}.json',dict(row,matched_world_cameras=True,comparison=path.name,comparison_sha256=sha(path),source_only=True,in_game_capture=False))

if __name__=='__main__':main()
