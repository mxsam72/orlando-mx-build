"""Restore v050 grass ground boundaries; retain the exact three v051 layer trials."""
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,map_coordinates,gaussian_filter
from scipy.spatial import cKDTree
from v048_surface import R,BASE,DIRT,SIZE,sha,save,tga,smooth,window

TRIALS=[
 dict(id='A',feature='R03 table-single',layer=2,mask='mask_visual_racing.tga',lo=232.,hi=279.,change='Remove only the historic prepared-soil overlay'),
 dict(id='B',feature='R10 big tabletop',layer=8,mask='mask_v032_packed.tga',lo=743.2,hi=813.2,change='Remove only the historic packed-soil overlay'),
 dict(id='C',feature='R17 eight rollers',layer=9,mask='mask_v032_face.tga',lo=1305.4,hi=1385.4,change='Remove only the historic jump-face overlay'),
]

def baseline_mask(name):
 for p in [BASE/'masks'/name.removeprefix('mask_'),BASE/'materials'/name]:
  if p.exists():return p
 raise FileNotFoundError(name)

def author(sample,out):
 out.mkdir(parents=True,exist_ok=True)
 original=baseline_mask('mask_visual_grass.tga')
 shutil.copy2(original,out/'mask_visual_grass.tga')
 assert sha(original)==sha(out/'mask_visual_grass.tga')
 reports=[]
 for trial in TRIALS:
  p=baseline_mask(trial['mask']);a=np.array(Image.open(p));n=a.shape[0];x=(np.arange(n)+.5)*SIZE/n;z=SIZE-x
  edited=a.copy();total=0;outside=0
  for y in range(0,n,64):
   xx,zz=np.meshgrid(x,z[y:y+64]);s,l=sample.coords(xx,zz)
   scope=sample.scope(xx,zz)*window(s,trial['lo'],trial['hi'],3.)
   alpha=np.uint8(np.rint(a[y:y+64,:,3]*(1-scope)))
   change=alpha!=a[y:y+64,:,3];total+=int(change.sum());outside+=int(np.count_nonzero(change&(scope<=0)))
   edited[y:y+64,:,3]=alpha
  assert total>0 and outside==0,(trial['id'],'empty or out-of-scope trial')
  assert np.array_equal(a[:,:,:3],edited[:,:,:3]);tga(edited,out/trial['mask'])
  reports.append(dict(trial,checks_pass=True,changed_pixels=total,changed_pixels_outside_section=outside,
   original_sha256=sha(p),authored_sha256=sha(out/trial['mask']),global_layer_retained=True))
 save(out.parent/'v052_layer_trials.json',dict(checks_pass=True,one_change_per_section=True,nonoverlapping_station_intervals=True,
  trials=reports,global_layer_count=14,global_texture_allocations_removed=0,
  note='Each old overlay is removed only in its named section. Textures remain required elsewhere; archive savings are measured after native compilation.'))
 save(out.parent/'v052_verge_validation.json',dict(checks_pass=True,existing_grass_layer=5,added_layers=0,
  changed_ground_pixels=0,new_grass_ground_area_m2=0.,restored_v050_ground_mask=True,
  v051_blanket_verge_expansion_removed=True,photographic_ground_tile_unchanged=True,
  original_mask_sha256=sha(original),mask_sha256=sha(out/'mask_visual_grass.tga')))
 return None

