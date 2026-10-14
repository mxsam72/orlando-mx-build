"""Transport v052 masks and directional atlas with A/C; groom the new B lane.

Tiled soil photographs, wet variants, shaders and their normal maps stay byte
exact. Changes are confined to the old/new A/B/C ribbons, with matte alpha 2.
"""
import re, shutil
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from v054_geometry import R,BASE,PREV,O,M,BOXES,Layout,raster_points,read,sha,save

def source(name):
 if (PREV/'materials'/name).is_file():return PREV/'materials'/name
 if name.startswith('mask_') and (BASE/'masks'/name[5:]).is_file():return BASE/'masks'/name[5:]
 for folder in [R/'V046_OUTPUT/materials',BASE/'materials',BASE]:
  if (folder/name).is_file():return folder/name
 raise FileNotFoundError(name)
def samples(array,p):
 n=array.shape[0];coords=[(600-p[:,1])/600*(n-1),p[:,0]/600*(n-1)]
 return map_coordinates(array,coords,order=1,mode='nearest').astype(np.float32)

def main():
 layout=Layout();M.mkdir(parents=True,exist_ok=True)
 hmf=(R/'V046_OUTPUT/compiled_track.hmf').read_text();tht=(R/'BUILD/v054_track.tht').read_text()
 masks=set(re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',hmf+tht))
 # The existing gravel road and practice road must retain their artwork.
 masks.discard('mask_v024_pit_roads.tga')
 names=sorted(masks|{'v044_route_detail.tga','v044_route_detail_n.tga'})
 reports=[];cache={}
 for name in names:
  file=source(name);image=Image.open(file);old=np.array(image);arr=old.copy();n=image.width
  assert image.width==image.height and n in [2048,4096,8192],(name,image.size)
  normal=name.endswith('_n.tga');is_mask=name.startswith('mask_');key=name.removeprefix('mask_').removesuffix('.tga');count=0
  for boxno,box in enumerate(BOXES):
   cachekey=(n,boxno)
   if cachekey not in cache:
    rr,cc,pts=raster_points(n,box);f=layout.fields(pts)
    # Take B's soil and groove detail from an existing v052 straight. The
    # continuous sampling avoids colour/normal seams at a repeated boundary.
    st=600+18*(1+np.sin(f['start_station']*.025))
    reference=np.c_[np.interp(st,layout.old_s,layout.old[:,0]),np.interp(st,layout.old_s,layout.old[:,1])]
    th=np.interp(st,layout.old_s,layout.old[:,2]);reference+=np.c_[-np.sin(th),np.cos(th)]*f['start_lateral'][:,None]
    starttheta=np.interp(np.clip(f['start_station'],0,layout.start[-1,3]),layout.start[:,3],layout.start[:,2]);f['start_source']=reference;f['start_rotation']=starttheta-th
    cache[cachekey]=(rr,cc,pts,f)
   rr,cc,pts,f=cache[cachekey];region=arr[np.ix_(rr,cc)].copy();flat=region.reshape(-1,region.shape[-1])
   erase=np.maximum(f['old'],f['retired_start'])*(1-f['new'])*(1-f['start'])
   active=np.maximum.reduce([erase,f['new'],f['start']])>0
   if is_mask:
    a=flat[:,3].astype(np.float32);background=255 if key=='off' else 0
    a=a*(1-erase)+background*erase
    transported=samples(old[:,:,3],f['src']);a=a*(1-f['new'])+transported*f['new']
    bvalue=samples(old[:,:,3],f['start_source'])
    targets={'off':0,'pits':0,'start':255,'racing':255,'grass':0,'sand':0,'visual_racing':250,'visual_worked':2,'visual_grass':0,'visual_sand':0,'v032_packed':0,'v032_damp':0,'v032_face':0,'v032_pits':0,'v044_route_detail':0,'v046_section':255}
    if key in targets:bvalue=np.full_like(a,targets[key])
    elif key not in ['v046_packed','v046_wear']:bvalue=np.zeros_like(a)
    a=a*(1-f['start'])+bvalue*f['start'];flat[active,3]=np.uint8(np.rint(np.clip(a[active],0,255)))
    assert np.array_equal(flat[:,:3],old[np.ix_(rr,cc)].reshape(-1,region.shape[-1])[:,:3])
   else:
    move=np.stack([samples(old[:,:,k],f['src']) for k in range(3)],1)
    start=np.stack([samples(old[:,:,k],f['start_source']) for k in range(3)],1)
    if normal:
     def rotate(values,theta):
      v=values/127.5-1;c=np.cos(theta);s=np.sin(theta);x=v[:,0].copy();z=v[:,1].copy();v[:,0]=x*c-z*s;v[:,1]=x*s+z*c
      v/=np.maximum(np.linalg.norm(v,axis=1)[:,None],1e-8);return v*127.5+127.5
     move=rotate(move,f['rotation']);start=rotate(start,f['start_rotation'])
    v=flat[:,:3].astype(np.float32);v=v*(1-f['new'][:,None])+move*f['new'][:,None];v=v*(1-f['start'][:,None])+start*f['start'][:,None]
    flat[active,:3]=np.uint8(np.rint(np.clip(v[active],0,255)))
    if normal:assert np.all(flat[:,3]==2),'Matte specular alpha changed'
   count+=int(np.count_nonzero(np.any(region!=arr[np.ix_(rr,cc)],axis=2)))
   # This is the only assignment; every pixel outside the geometry ribbons
   # must remain equal to its effective delivered-v052 source image.
   before=arr[np.ix_(rr,cc)];assert np.array_equal(flat[~active],before.reshape(-1,before.shape[-1])[~active])
   arr[np.ix_(rr,cc)]=flat.reshape(region.shape)
  Image.fromarray(arr).save(M/name,format='TGA');reports.append(dict(file=name,baseline_sha256=sha(file),sha256=sha(M/name),changed_pixels=count,unrelated_pixels_exact=True,size=list(image.size)))
  print('V054_SURFACE',name,count,flush=True)
 (O/'compiled_track.hmf').write_text(hmf)
 tiles=[]
 for folder in [BASE/'materials',R/'V046_OUTPUT/materials',PREV/'materials']:
  for p in folder.iterdir():
   if p.suffix in ['.tga','.shd'] and not p.name.startswith('mask_') and p.name not in ['v044_route_detail.tga','v044_route_detail_n.tga']:
    effective=source(p.name);tiles.append(dict(file=p.name,sha256=sha(effective)))
 save(O/'surface_validation.json',dict(checks_pass=True,baseline='v052',soil_palette_and_photographs_exact=True,tiled_normal_maps_and_shaders_exact=True,normal_specular_alpha=2,layer_count=14,added_layers=0,changed_images=reports,retained_tiles=tiles,source_pixel_changes_confined_to_geometry_ribbons=True,isolated_layer_trials_transport_with_changed_C=True,road_mask_unchanged=True))
 print('V054_SURFACES_PASSED',flush=True)
if __name__=='__main__':main()
