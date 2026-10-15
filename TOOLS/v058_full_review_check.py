"""Audit the completed user review: real coverage, controls and preserved inputs."""
import json,zipfile
import numpy as np
from PIL import Image
from v058_full_review import R,O,OUT,CACHE,VIEWS,W,H,sha,save,Circuit
from v056_geometry import corner_regions

CORNER_PHOTOS=[4,6,9,11,13,14,16,18,21,24,27,30,31,35]
FEATURE_PHOTOS={'R01':1,'R02':5,'R03':7,'R05':12,'R07':15,'R09':19,'R10':20,'R11_ENTRY':22,'R11':22,'R12':23,'R14':25,'R15':28,'R16':29,'R17':32,'R18':34}

def visible(c,number):
 with np.load(CACHE/f'{number:02d}_hits.npz') as z:
  use=np.flatnonzero(z['hit'])[::8];x=z['x'][use];zz=z['z'][use]
  scope=c.scope(x,zz);s,l=c.coords(x,zz)
 return s,l,scope

def main():
 c=Circuit();manifest=json.loads((OUT/'Review_Manifest.json').read_text());rows=manifest['renders']
 assert len(rows)==38 and len({r['file'] for r in rows})==38
 for row,v in zip(rows,VIEWS):
  assert row['view']==v and sha(OUT/row['file'])==row['sha256']
  im=Image.open(OUT/row['file']);assert im.size==(W,H)
  assert row['terrain_pixels']>W*H*.25 and row['photographic_pixels']>5000
  bound={p['layer']:p for p in row['layers']}
  for layer in [3,11,13]:assert bound[layer]['colour_repeats']==200
  assert bound[13]['normal_repeats']==1 and bound[11]['normal_repeats']==200
 corners=[]
 for (name,lo,hi),number in zip(corner_regions(c.q,c.route['v054_old_station']),CORNER_PHOTOS):
  s,l,scope=visible(c,number);active=(s>=lo)&(s<=hi)&(abs(l)<12)&(scope>.5)
  assert active.sum()>250,(name,number,int(active.sum()))
  corners.append(dict(corner=name,photo=number,subsampled_visible_dirt_pixels=int(active.sum()),geometry_exact_v056=True))
 features=[]
 for name,lo,hi in c.features:
  number=FEATURE_PHOTOS[name];s,l,scope=visible(c,number)
  active=(s>=lo)&(s<=hi)&(abs(l)<12)&(scope>.5)
  assert active.sum()>100,(name,number,int(active.sum()))
  features.append(dict(feature=name,photo=number,subsampled_visible_dirt_pixels=int(active.sum())))
 old=np.asarray(Image.open(R/'BUILD/v058_hybrid_review/H_03_triple.jpg')).astype(np.int16)[70:]
 new=np.asarray(Image.open(OUT/'Orlando_v058_05.jpg')).astype(np.int16)[70:]
 delta=np.abs(old-new);mean=float(delta.mean());close=float((delta.max(2)<4).mean())
 assert mean<.5 and close>.98,(mean,close)
 for name in ['terrain_validation.json','race_validation.json','scenery_validation.json','surface_validation.json']:
  report=json.loads((O/name).read_text());assert report['checks_pass']
 assert sha(O/'terrain.raw')==sha(R/'V056_OUTPUT/terrain.raw')
 assert sha(O/'scenery.fbx')==sha(R/'V057_OUTPUT/scenery.fbx')
 archive=R/'BUILD/Orlando_v058_Full_Track_Photos.zip'
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert set(z.namelist())=={r['file'] for r in rows}|set(manifest['sheets'])|{manifest['map'],'Read_Me.txt','Review_Manifest.json'}
 report=dict(checks_pass=True,photo_count=38,all_14_corners_visibly_covered=corners,all_15_jump_groups_visibly_covered=features,
  approved_trial_match=dict(camera='R02 triple',mean_absolute_RGB_delta_8bit=mean,fraction_pixels_max_channel_delta_under_4=close,
   note='JPEG source previews; small edge, mask quantisation and JPEG differences are expected.'),
  terrain_exact_tested_v056=True,approved_v057_scenery_byte_exact=True,final_compilation_started=False,
  archive=dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size))
 save(R/'V058_SOURCE/full_track_review_check.json',report)
 print('V058_FULL_REVIEW_CHECKS_PASS: 38 photos, 14 corners, 15 jump groups; approved trial retained',flush=True)

if __name__=='__main__':main()
