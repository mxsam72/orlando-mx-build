"""Cinematic feature photos of the exact released v065 source.

Four original pit vehicles, candy board, approved Pup artwork and the existing
photographic crocodile are framed from their serialized bounds. No track or
scenery source is edited. Rendering uses presentation lighting, not game capture.
"""
from pathlib import Path
import argparse,json,math,time,hashlib
import numpy as np
import bpy
from mathutils import Vector,Quaternion
import v065_cinematic_render as base

R=base.R;W=base.W;OUT=R/'DOCUMENTATION/v065_feature_cinematics'

def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()

def cameras():
 bounds=read(W/'scene_bounds.json');raw=np.fromfile(base.B/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
 route=np.load(base.B/'route.npz')['q']
 def ground(x,y):
  c=np.clip(x/600*2048,0,2047.999);r=np.clip((600-y)/600*2048,0,2047.999);i,j=int(r),int(c);fr,fc=r-i,c-j
  return float((1-fr)*((1-fc)*raw[i,j]+fc*raw[i,j+1])+fr*((1-fc)*raw[i+1,j]+fc*raw[i+1,j+1]))
 def loc(x,y,h):return [float(x),float(y),ground(x,y)+h]
 def at(s,l,h):
  x,y,t=[np.interp(s,route[:,3],route[:,i]) for i in [0,1,2]]
  return loc(x-math.sin(t)*l,y+math.cos(t)*l,h)
 def combine(prefix):
  found=[np.asarray(b) for n,b in bounds.items() if n.startswith(prefix)]
  assert found,prefix
  return np.min([b[0] for b in found],0),np.max([b[1] for b in found],0)
 lo,hi=combine('v041_pond_crocodile_photographic');c=(lo+hi)/2
 # The delivered crocodile is a photographic profile relief. Its broad face
 # is along game Z: photograph that actual face instead of inventing geometry.
 crop_eye=[float(c[0]),float(c[1]-20),max(float(c[2]+2.9),ground(c[0],c[1]-20)+1.8)]
 crop_target=[float(c[0]),float(c[1]),float(c[2]+.15)]
 croc_wide=[float(c[0]-8),float(c[1]-31),max(float(c[2]+11),ground(c[0]-8,c[1]-31)+7)]
 cams=[
  dict(name='01_four_vehicles_and_candy',title='The four-vehicle lineup',eye=[351,130,8.0],target=[336,153,4.2],lens=36,fstop=9,
       fit=['truck_jordan_','truck_premier_','truck_sam_','van_shane_','v057_cardboard_sign_']),
  dict(name='02_chevy_express_and_candy',title='Express and candy sign',eye=[351,141,5.8],target=[342.7,151.5,4.05],lens=42,fstop=7.1,
       fit=['van_shane_','v057_cardboard_sign_']),
  dict(name='03_sam_king_ranch',title="Sam's Ford King Ranch",eye=[335.9,143,5.2],target=[338.4,153.0,4.05],lens=50,fstop=5.6,fit=['truck_sam_']),
  dict(name='04_premier_chevy',title='Premier service Chevrolet',eye=[329,142.5,5.6],target=[333,153.5,4.1],lens=50,fstop=5.6,fit=['truck_premier_']),
  dict(name='05_silver_cybertruck',title='Stainless Cybertruck',eye=[320.5,143.5,5.1],target=[327.4,153.2,4.1],lens=50,fstop=5.6,fit=['truck_jordan_']),
  dict(name='06_pup_memorial_close',title='Pup Whatley memorial',eye=[322,126,7.7],target=[322,144,7.3],lens=46,fstop=9,
       fit=['v032_pup_whatley_memorial_memorial']),
  dict(name='07_pup_memorial_pits',title='Remembering Pup in the pits',eye=[307,122,8.7],target=[322,144,6.8],lens=40,fstop=8,
       fit=['v032_pup_whatley_memorial_']),
  dict(name='08_crocodile_close',title='The pond resident',eye=crop_eye,target=crop_target,lens=48,fstop=6.3,
       fit=['v041_pond_crocodile_photographic']),
  dict(name='09_crocodile_pond',title='Crocodile pond',eye=croc_wide,target=crop_target,lens=40,fstop=8,
       fit=['v041_pond_crocodile_photographic']),
  dict(name='10_wall_entry_roller',title='The wall-entry roller',eye=loc(542,207,4.5),target=loc(535,246.2,.25),lens=38,fstop=9),
  dict(name='11_tabletop_three_quarter',title='Loam on the tabletop',eye=at(789,-18,10),target=at(816,0,.9),lens=43,fstop=8),
  dict(name='12_berm_golden_hour',title='Golden-hour berm',eye=at(80,-9,2.8),target=at(110,0,.5),lens=40,fstop=8,
       sun_azimuth_degrees=310,sun_elevation_degrees=13),
 ]
 for cam in cams:
  e=np.asarray(cam['eye'],float);target=np.asarray(cam['target'],float)
  # Native terrain is authoritative for camera clearance too.
  e[2]=max(e[2],ground(e[0],e[1])+.65);cam['eye']=e.tolist()
  if not cam.get('fit'):continue
  points=[]
  for prefix in cam['fit']:
   low,high=combine(prefix)
   points.extend([[x,y,z] for x in [low[0],high[0]] for y in [low[1],high[1]] for z in [low[2],high[2]]])
  p=np.asarray(points);f=target-e;f/=np.linalg.norm(f);right=np.cross(f,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,f)
  d=p-e;depth=d@f;assert np.all(depth>.05),cam['name']
  u=cam['lens']/36*(d@right)/depth;v=cam['lens']/20.25*(d@up)/depth
  factor=min(1,.43/max(np.max(abs(u)),1e-8),.43/max(np.max(abs(v)),1e-8))
  cam['lens']=float(cam['lens']*factor)
 return cams

def lights(scene,cam):
 az=math.radians(cam.get('sun_azimuth_degrees',230));el=math.radians(cam.get('sun_elevation_degrees',23))
 sky=next(n for n in scene.world.node_tree.nodes if n.type=='TEX_SKY');sky.sun_rotation=az;sky.sun_elevation=el
 sun=bpy.data.objects['Presentation sun'];direction=Vector((math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)))
 sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler();sun.data.energy=3.2
 sun.data.color=(1,.89,.73) if el>math.radians(16) else (1,.76,.51)
 scene.view_settings.exposure=.65

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--draft',action='store_true');ap.add_argument('--shots',default='all');args=ap.parse_args()
 OUT.mkdir(parents=True,exist_ok=True);cams=cameras()
 if args.shots!='all':cams=[c for c in cams if c['name'].split('_')[0] in args.shots.split(',')]
 assert cams
 scene=base.load_scene()
 # Faithful PBR translation of the existing water surface for path tracing.
 # Its original mesh, UVs and diffuse photograph remain untouched.
 water=bpy.data.materials.get('water')
 if water:
  p=water.node_tree.nodes.get('Principled BSDF');p.inputs['IOR'].default_value=1.333;p.inputs['Roughness'].default_value=.20
  p.inputs['Coat Weight'].default_value=.6;p.inputs['Coat Roughness'].default_value=.12
 scene.render.resolution_x=1120 if args.draft else 2560;scene.render.resolution_y=630 if args.draft else 1440
 scene.cycles.samples=16 if args.draft else 48;scene.cycles.adaptive_min_samples=6 if args.draft else 12
 scene.cycles.adaptive_threshold=.12 if args.draft else .045
 folder=OUT/'drafts' if args.draft else OUT;folder.mkdir(exist_ok=True)
 prior=read(folder/'renders.json') if (folder/'renders.json').exists() else {};names={c['name'] for c in cams}
 rows=[r for r in prior.get('renders',[]) if r['name'] not in names]
 provenance=dict(version='v065',source_assets='Released v065 checkpoint',source_only=True,in_game_capture=False,
  terrain_sha256=sha(base.B/'terrain.raw'),scenery_sha256=sha(base.B/'scenery.fbx'),
  material_validation_sha256=read(W/'preparation.json')['material_validation_sha256'])
 for cam in cams:
  start=time.time();obj=scene.camera;obj.location=cam['eye'];direction=Vector(cam['target'])-obj.location
  obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();obj.data.lens=cam['lens']
  obj.data.dof.use_dof=not args.draft;obj.data.dof.aperture_fstop=cam.get('fstop',8);obj.data.dof.focus_distance=direction.length
  lights(scene,cam);path=folder/(cam['name']+'.png');scene.render.filepath=str(path)
  print('FEATURE_RENDER_START',cam['name'],flush=True);bpy.ops.render.render(write_still=True)
  rows.append(dict(cam,file=path.name,seconds=round(time.time()-start,1),sha256=sha(path)));rows.sort(key=lambda r:r['name'])
  report=dict(provenance,renders=rows)
  (folder/'renders.json').write_text(json.dumps(report,indent=2)+'\n')
  print('FEATURE_RENDER_SAVED',path.name,round(time.time()-start,1),flush=True)
 print('FEATURE_CINEMATICS_COMPLETE',flush=True)

if __name__=='__main__':main()
