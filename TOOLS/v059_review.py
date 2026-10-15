"""v059 photo review with the exact v058 cameras and explicit before/after pairs."""
import hashlib,json,sys,zipfile
import numpy as np
from PIL import Image,ImageDraw
import v058_full_review as review
from v059_surface import R,O,M,S,PREV,sha,save,source,Circuit
from v049_previews import font

OUT=R/'BUILD/v059_review';CACHE=R/'BUILD/v059_cache';CHANGED_VIEWS=['04','07','08','09','10','15','21','22','25']

def configure():
 OUT.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True,parents=True)
 review.OUT=OUT;review.CACHE=CACHE;review.O=O;review.source=source;review.SOURCE_DIR=S;review.VERSION='v059';review.REVIEW_TITLE='v059 - Perpendicular grooming'
 review.render.CACHE=CACHE;review.render.WIDTH=review.W;review.render.HEIGHT=review.H
 for view in review.VIEWS:
  old=json.loads((R/'BUILD/v058_full_review'/('photo_'+view['id']+'.json')).read_text())
  view['eye_xzy_m']=old['eye_xzy_m'];view['target_xzy_m']=old['target_xzy_m']
 return review.VIEWS

def plot_geometry(c):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from v054_previews import Terrain
 from v059_geometry import cross_points
 before=Terrain(PREV/'terrain.raw');fig,axes=plt.subplots(3,1,figsize=(14,11));fig.patch.set_facecolor('#f2eee7')
 for ax,s,name in zip(axes[:2],[288.,883.],['Corner 03','Corner 09']):
  l=np.linspace(-9,9,600);p=cross_points(c.q,np.full_like(l,s),l)
  ax.plot(l,before.ground(p[:,0],p[:,1]),color='#9d7659',label='v058 before',lw=2)
  ax.plot(l,c.terrain.ground(p[:,0],p[:,1]),color='#177c84',label='v059 smoother bank',lw=2)
  ax.set_title(name+' — cross-section through the bank');ax.set_xlabel('Across the track (m)');ax.set_ylabel('Height (m)');ax.legend();ax.grid(alpha=.18)
 ax=axes[2];ss=np.linspace(903,981,1800);p=cross_points(c.q,ss,0);ax.plot(ss,before.ground(p[:,0],p[:,1]),color='#9d7659',label='v058 before',lw=2);ax.plot(ss,c.terrain.ground(p[:,0],p[:,1]),color='#177c84',label='v059 moved pair',lw=2)
 q=json.loads((O/'terrain_validation.json').read_text())['moved_pair']
 for old,new in zip(q['old_crest_stations_m'],q['new_crest_stations_m']):
  ax.annotate('',xy=(new,4.05),xytext=(old,4.05),arrowprops=dict(arrowstyle='->',color='#177c84',lw=2))
 ax.text(933,4.12,'Pair moved forward 9.9 m • spacing remains 9.9 m',ha='center',color='#145e66')
 ax.set_title('Screenshot 22 — only the second/third mound pair moves');ax.set_xlabel('Distance around track (m)');ax.set_ylabel('Height (m)');ax.set_ylim(2.65,4.38);ax.grid(alpha=.18);ax.legend(loc='lower left')
 fig.suptitle('v059 geometry checks — actual terrain samples',fontsize=20);fig.tight_layout(rect=[0,0,1,.97]);fig.savefig(OUT/'Orlando_v059_Geometry_Changes.jpg',dpi=160);plt.close(fig)

def package(c):
 rows=[json.loads((OUT/f'photo_{v["id"]}.json').read_text()) for v in review.VIEWS]
 assert len(rows)==38 and all(sha(OUT/r['file'])==r['sha256'] for r in rows)
 review.package(c,rows);plot_geometry(c);comparisons=[]
 for number in CHANGED_VIEWS:
  old=R/f'BUILD/v058_full_review/Orlando_v058_{number}.jpg';new=OUT/f'Orlando_v059_{number}.jpg';im=Image.new('RGB',(3200,1070),(22,25,29));d=ImageDraw.Draw(im)
  d.text((20,14),'v058 before',font=font(29),fill='white');d.text((1620,14),'v059 requested update',font=font(29),fill='white')
  im.paste(Image.open(old),(0,70));im.paste(Image.open(new),(1600,70));path=OUT/f'Orlando_v059_Compare_{number}.jpg';im.save(path,quality=96,subsampling=0);comparisons.append(path.name)
 # Append the checked comparisons and geometry plot by rebuilding atomically.
 archive=R/'BUILD/Orlando_v059_Full_Track_Photos.zip';temporary=CACHE/'complete_review.zip'
 with zipfile.ZipFile(archive) as old,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as new:
  for item in old.infolist():new.writestr(item,old.read(item.filename))
  for name in comparisons+['Orlando_v059_Geometry_Changes.jpg']:new.write(OUT/name,name)
 with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
 temporary.replace(archive)
 data=json.loads((S/'full_track_review.json').read_text());data.update(before_after=comparisons,geometry_plot='Orlando_v059_Geometry_Changes.jpg',exact_v058_world_cameras=True,archive=dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size));save(S/'full_track_review.json',data)
 print('V059_COMPLETE_REVIEW_READY: 38 photos, 9 matched comparisons, geometry plot; compilation held',flush=True)

def main():
 views=configure();c=Circuit()
 if '--package' in sys.argv:package(c);return
 assert json.loads((O/'surface_validation.json').read_text())['checks_pass']
 inputs=[R/'TOOLS/v059_review.py',R/'TOOLS/v059_surface.py',R/'TOOLS/v059_geometry.py',R/'TOOLS/v058_full_review.py',R/'TOOLS/v058_render.py',O/'surface_validation.json',O/'terrain_validation.json']
 key=hashlib.sha256(''.join(sha(p) for p in inputs).encode()).hexdigest();m=review.ProductionMaterials()
 selected=views if len(sys.argv)==1 else [v for v in views if v['id'] in sys.argv[1:]]
 for v in selected:
  path=OUT/f'photo_{v["id"]}.json'
  if path.exists():
   old=json.loads(path.read_text())
   if old['key']==key and old['view']==v and sha(OUT/old['file'])==old['sha256']:print('REUSED',v['id'],flush=True);continue
  review.render_one(c,m,v,key)
 if len(sys.argv)==1:package(c)

if __name__=='__main__':main()
