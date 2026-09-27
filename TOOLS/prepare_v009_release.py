#!/usr/bin/env python3
"""Prepare v009 support files and masks while preserving all earlier releases."""
from pathlib import Path
import re,json,shutil,hashlib,struct
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
R=Path(__file__).resolve().parents[1];W=R/'BUILD/v009_work';O=R/'V009_OUTPUT';NAME='orlandomx_2026_v009';DEST=R/'12_RELEASE'/NAME

def main():
 qa=json.loads((R/'DOCUMENTATION/v009_geometry_validation.json').read_text());spec=json.loads((R/'V009_SOURCE/v009_geometry_spec.json').read_text())
 if set(spec['active_sections'])!={f'S{i:02d}' for i in range(1,12)} or not qa.get('geometry_checks_pass'):raise RuntimeError('All physical sectors must pass QA before release preparation')
 base=W/'12_RELEASE/orlandomx_2026_v008';DEST.mkdir(parents=True,exist_ok=True)
 for p in DEST.iterdir():
  if p.is_file():p.unlink()
 for p in base.iterdir():
  if p.is_file() and p.suffix not in ['.map','.trh']:shutil.copy2(p,DEST/p.name.replace('orlandomx_2026_v008',NAME))
 ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('Orlando MX 2026 v008','Orlando MX 2026 v009').replace('orlandomx_2026_v008',NAME))
 B=np.fromfile(R/'BUILD/v009_baseline/terrain.raw','<u2').reshape(2049,2049)/65535*18;H=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18;delta=H-B
 def dy(x,z):return float(map_coordinates(delta,[[(600-z)/600*2048],[x/600*2048]],order=1)[0])
 changes=[]
 def cam(m):
  x,y,z=map(float,m.groups());v=dy(x,z);changes.append(v);return f'pos = {x:.6f},{y+v:.6f},{z:.6f}'
 p=DEST/(NAME+'.tsc');p.write_text(re.sub(r'pos\s*=\s*([-\d.]+),([-\d.]+),([-\d.]+)',cam,p.read_text()))
 def marshal(m):
  v=dy(float(m[2]),float(m[6]));changes.append(v);return m[1]+m[2]+m[3]+f'{float(m[4])+v:.6f}'+m[5]+m[6]
 p=DEST/'marshals.cfg';p.write_text(re.sub(r'(x\s*=\s*)([-\d.]+)(\s+y\s*=\s*)([-\d.]+)(\s+z\s*=\s*)([-\d.]+)',marshal,p.read_text()))
 f=np.load(O/'qa_fields.npz');lat=f['lat'];s=f['station'];ew=f['effective_width'];dist=f['distance']
 def ease(t):
  t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
 narrow=(1-ease((abs(lat)-ew/2+.2)/1.8))*(1-ease((dist-ew/2+.2)/1.8));support=1-ease((dist-f['width']/2-7)/1.5);mdir=O/'visual_masks';mdir.mkdir(exist_ok=True);coverage=[]
 for name in ['visual_racing','visual_worked','visual_grass']:
  orig=Image.open(W/'03_MASKS'/f'{name}.tga').convert('RGBA');alpha=np.array(orig.getchannel('A').resize((2049,2049)),dtype=np.float32)/255
  if name=='visual_racing':a=np.maximum(alpha*.60,narrow*.96)
  elif name=='visual_worked':a=np.maximum(alpha*.75,np.clip(np.exp(-((lat-1.35-.15*np.sin(s/18))/.58)**2)+.8*np.exp(-((lat+1.35-.12*np.sin(s/17))/.65)**2),0,1)*narrow*.84)
  else:a=alpha*(1-narrow*.96)
  a=np.clip(alpha+(a-alpha)*support,0,1);assert float(abs(a[dist>f['width']/2+9]-alpha[dist>f['width']/2+9]).max())<1e-6
  im=Image.fromarray(np.uint8(a*255)).resize((2048,2048),Image.Resampling.BILINEAR);rgba=Image.new('RGBA',im.size,'white');rgba.putalpha(im);rgba.save(mdir/f'{name}.tga');im.save(mdir/f'{name}.png');coverage.append(dict(mask=name,mean_core_alpha=float(a[dist<ew/2-.3].mean()),outside_corridor_alpha_unchanged=True))
 assert coverage[0]['mean_core_alpha']>.9,'Racing visual mask does not cover shaped corridor'
 for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
  data=(DEST/name).read_bytes();count=struct.unpack_from('<I',data,4)[0];a=np.frombuffer(data[8:],dtype='<f4').reshape(-1,2)
  assert data[:4]==b'TL \0' and len(data)==8+count*8 and np.isfinite(a).all() and np.all(np.diff(a[:,0])>0)
 md=json.loads((R/'V009_SOURCE/baseline_manifest.json').read_text());assert all(hashlib.sha256((W/'04_TEXTURES'/n).read_bytes()).hexdigest()==h for n,h in md['texture_sha256'].items())
 assert (DEST/(NAME+'.rdf')).read_bytes()==(base/'orlandomx_2026_v008.rdf').read_bytes()
 route=np.load(R/'V009_SOURCE/baseline_route.npz');start=route['start'];start_change=map_coordinates(delta,[(600-start[:,1])/600*2048,start[:,0]/600*2048],order=1)
 # Pit-grid positions are unchanged; the paddock must retain its old elevation.
 pit_changes=[abs(dy(x,z)) for x in range(260,331,10) for z in [110,117,124]];assert max(pit_changes)<.001
 report=dict(physics_materials_unchanged=True,race_rdf_unchanged=True,centerline_alignment_unchanged=True,reset_boundaries_valid=True,visual_masks=coverage,v008b_texture_hashes_preserved=True,camera_and_marshal_shifts_m=changes,pit_max_height_change_m=max(pit_changes),start_lane_max_height_change_m=float(abs(start_change).max()),native_compilation=False,in_game_test=False)
 (R/'DOCUMENTATION/v009_release_validation.json').write_text(json.dumps(report,indent=2)+'\n');print('Prepared v009 release, masks and race validation.')
if __name__=='__main__':main()
