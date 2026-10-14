"""Restore the delivered v052 sources plus native route/physical declarations."""
import concurrent.futures, io, json, os, shutil, zipfile
from pathlib import Path
from v052_transfer import INPUTS as PREVIOUS, api, identity, safe, extract
from download_v048_inputs import download
from v048_surface import R, BASE, DIRT, sha, save

O=R/'V054_OUTPUT'; PREV=R/'V052_OUTPUT'
EXTRA={
 'v052_source.zip':('v052-natural-dirt-grass-38537630164/OrlandoMX-v052-source-checkpoint.zip',418060442,'402566cd10ae9b724cadaf67ea2377cdc25f062fda563828b11ffc390a094c31'),
 'v052_validation.json':('v052-natural-dirt-grass-38537630164/OrlandoMX_v052_Validation.json',112355,'0742a0464dca264295d1d52035aeb87702ec0b3e84ee51fd5b54e304c6b3fa06')
}
ALL=PREVIOUS|EXTRA
def restore():
 identity(); tags={}
 for name,(url,size,digest) in ALL.items():
  tag,asset=url.split('/',1)
  if tag not in tags:
   rel=api('/releases/tags/'+tag);assert not rel['draft'];tags[tag]={a['name']:a for a in rel['assets']}
  item=tags[tag][asset];assert item['size']==size and item['digest']=='sha256:'+digest,name
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(download,ALL.items()))
 folder=R/'BUILD/v048_inputs'
 with zipfile.ZipFile(folder/'v044_source.zip') as z:
  listing=z.namelist()
  keep_names={'terrain.raw','route.npz','compiled_track.hmf','geometry_spec.json','jump_profiles.json','v024_pit_gravel.tga','main.tcl','start.tcl','turns.json','holeshot_layout.json','source_validation.json','track.tht'}
  for i in z.infolist():
   safe(i.filename)
   keep=i.filename.startswith(('V044_OUTPUT/materials/','V044_OUTPUT/masks/','V044_OUTPUT/facility_textures/','BUILD/v044_assets/grass_bermuda_01/'))
   keep|=i.filename.startswith('V044_OUTPUT/') and Path(i.filename).name in keep_names
   keep|=i.filename in ['BUILD/tool_versions.json','BUILD/map_params.ini','BUILD/trh_params.ini','BUILD/edf_params.ini','BUILD/v044_assets/grass_bermuda_01_metadata.json']
   if keep and not i.is_dir():extract(z,i,R/i.filename)
  parts=sorted(n for n in listing if n.startswith('BUILD_INPUTS/native_inputs.zip.part'))
  with zipfile.ZipFile(io.BytesIO(b''.join(z.read(n) for n in parts))) as inner:
   for name,target in [('05_NORMALS/grass_n.tga',BASE/'grass_n.tga'),('04_TEXTURES/basemap.tga',BASE/'basemap.tga')]:extract(inner,inner.getinfo(name),target)
   thts=[n for n in inner.namelist() if Path(n).name=='track.tht']
   assert len(thts)==1,thts
   extract(inner,inner.getinfo(thts[0]),R/'BUILD/v054_track.tht')
   save(R/'BUILD/v054_original_inputs_manifest.json',{'files':inner.namelist(),'v044_route_files':[n for n in listing if n.startswith('V044_OUTPUT/') and Path(n).name in keep_names]})
 for name,prefix in [('v046_source.zip',('V046_OUTPUT/','V046_SOURCE/')),('v047_source.zip',('V047_OUTPUT/','V047_SOURCE/')),('v052_source.zip',('V052_OUTPUT/','V052_SOURCE/'))]:
  with zipfile.ZipFile(folder/name) as z:
   for i in z.infolist():
    safe(i.filename)
    if not i.is_dir() and i.filename.startswith(prefix):extract(z,i,R/i.filename)
 baseline=json.loads((folder/'v052_validation.json').read_text())
 assert baseline['compiled'] and baseline['source_checks'] and baseline['pkz_sha256']=='6a874fefa8bce42044e976a3e32e8d3c25c869b82e01e437c23901e3436d3a64'
 assert sha(BASE/'terrain.raw')=='f6ce21f9b1a0ff4ca3a822d92dcba5904eeea860cd95952bd4ba44ac9cb5c4b9'
 assert sha(PREV/'scenery.fbx')==baseline['grass_validation']['scenery_sha256']
 for name,row in baseline['surface_validation']['files'].items():assert sha(PREV/name)==row['sha256'],name
 game=R/'BUILD/v054_baseline_game';game.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(folder/'v047.pkz') as z:
  for i in z.infolist():
   safe(i.filename)
   if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,game/Path(i.filename).name.replace('orlandomx_2026_v047','orlandomx_2026_v052'))
 ini=game/'orlandomx_2026_v052.ini';ini.write_text(ini.read_text().replace('v047','v052'))
 for row in baseline['retained_game_files']:assert sha(game/row['file'])==row['sha256'],row['file']
 for name in ['main.tcl','start.tcl','geometry_spec.json','jump_profiles.json','route.npz']:assert (BASE/name).is_file(),name
 save(R/'BUILD/v054_input_validation.json',dict(checks_pass=True,baseline_version='v052',pinned_inputs=ALL,baseline_pkz_sha256=baseline['pkz_sha256'],source_scenery_sha256=sha(PREV/'scenery.fbx'),physical_material_declarations_sha256=sha(R/'BUILD/v054_track.tht')))
 for p in folder.iterdir():
  if p.suffix in ['.zip','.pkz','.part']:p.unlink()
 print('V054_INPUTS_VERIFIED: delivered v052 source, geometry, scenery and race inputs.',flush=True)

def inspection():
 restore();out=R/'BUILD/v054_authoring_inputs';out.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out/'v054_authoring_inputs.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted((R/'TOOLS').glob('*.py')):z.write(p,p.relative_to(R).as_posix())
  for p in BASE.iterdir():
   if p.suffix in ['.raw','.npz','.json','.tcl','.hmf']:z.write(p,p.relative_to(R).as_posix())
  for p in (R/'BUILD/v054_baseline_game').iterdir():
   if p.suffix not in ['.trh','.tga']:z.write(p,p.relative_to(R).as_posix())
  for p in [R/'BUILD/v054_track.tht',R/'BUILD/v048_inputs/v052_validation.json',R/'BUILD/v054_original_inputs_manifest.json',R/'BUILD/v054_input_validation.json']:z.write(p,p.relative_to(R).as_posix())
 print('V054_AUTHORING_INPUTS_READY',flush=True)
if __name__=='__main__':
 import sys
 {'restore':restore,'inspect':inspection}[sys.argv[1]]()
