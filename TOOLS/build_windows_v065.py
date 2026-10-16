"""Compile approved hybrid terrain; reuse authenticated unchanged native scenery."""
import json,mmap,os,re,shutil,struct,sys,zipfile
from pathlib import Path
import numpy as np
from v065_inputs import R,O,M,S,TESTED,NAME,DEST,SAVED,EXTRA,source,sha,save,check
from v027_scenery import parse,values,child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature,verify_files
from native_coordinate_scan_v044 import scan_points
from native_specular_v052 import specular_records
from v052_foliage import MATTE
from build_windows_v047 import run_native,native_tools

P=R/'BUILD/v065_stage';LOG=R/'DOCUMENTATION'
def read(path):return json.loads(Path(path).read_text())

def probes():
 q=read(O/'native_probes.json');return q['retained_geometry']+q['changed_geometry']

def stage():
 check();P.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
 for src,name in [(O/'terrain.raw','terrain.raw'),(O/'scenery.fbx','scenery.fbx'),(O/'compiled_track.hmf','track.hmf'),
  (O/'main.tcl','main.tcl'),(O/'start.tcl','start.tcl'),(R/'BUILD/v054_track.tht','track.tht'),
  (R/'BUILD/edf_params.ini','edf_params.ini'),(R/'BUILD/trh_params.ini','trh_params.ini')]:shutil.copy2(src,P/name)
 expected=read(S/'native_expected_inputs.json')
 assert sha(P/'terrain.raw')==expected['terrain'] and sha(P/'scenery.fbx')==expected['scenery'] and sha(P/'track.tht')==expected['physical_declarations']
 params=(R/'BUILD/map_params.ini').read_text()
 for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
  params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
 params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
 (P/'map_params.ini').write_text(params,encoding='utf-8',newline='\n')
 # Resolve the original accepted facility overrides in their production order.
 for folder in [TESTED/'facility_textures']:
  assert folder.is_dir(),folder
  for src in folder.iterdir():
   if src.suffix in ['.tga','.shd','.flg']:shutil.copy2(src,P/src.name)
 surface=read(O/'surface_validation.json')
 for row in surface['active_terrain_inventory']+surface['active_shaders']:
  src=source(row['file']);assert sha(src)==row['sha256'],row['file'];shutil.copy2(src,P/row['file'])
 nodes=parse((P/'scenery.fbx').read_bytes())[0];bindings=actual_diffuse_bindings(nodes)
 objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
 links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
 fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
 for b in bindings['bindings']:
  name=b['texture'];assert Path(name).name==name
  if not (P/name).is_file():
   video=next(objects[v[1]] for v in links if v[2]==b['texture_id'] and objects.get(v[1],{}).get('name')==b'Video')
   content=child(video,b'Content')['props'];assert content[:1]==b'R' and struct.unpack_from('<I',content,1)[0]==len(content)-5
   (P/name).write_bytes(content[5:])
 names=set(bindings['actual_diffuse_textures']);normals=set()
 for name in list(names):
  shader=P/(Path(name).stem+'.shd')
  if shader.is_file():
   shutil.copy2(shader,fbm/shader.name)
   for ref in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):
    assert Path(ref).name==ref and (P/ref).is_file(),(name,ref);names.add(ref)
    if ref!=MATTE:normals.add(ref)
 for name in names:
  bitmap_signature(P/name);shutil.copy2(P/name,fbm/name)
 for ref in re.findall(r'(?m)^\s*(?:data|map|mask)\s*=\s*(\S+)',(P/'track.hmf').read_text()+(P/'track.tht').read_text()):
  assert Path(ref).name==ref and (P/ref).is_file(),ref
 del nodes,objects,links
 saved=P/'scenery.edf'
 if not saved.exists():os.link(SAVED/'scenery.edf',saved)
 recovered=read(R/'BUILD/v065_recovered_inputs.json');assert sha(saved)==recovered['saved_edf_sha256']
 with saved.open('rb') as stream:assert stream.read(4)==b'EDF\0'
 textures=[P/n for n in sorted(names)];normal_paths=[P/n for n in sorted(normals)]
 # verify_files requires both EDF and MAP; the comprehensive pair check runs
 # after TerrainEd. Beforehand verify geometry and foliage in the pinned EDF.
 with saved.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  errors=scan_points(raw,[p['expected_xyz_m'] for p in probes()]);assert all(e is not None for e in errors)
  specular_records(raw,P/MATTE,minimum_records=2)
 for row in surface['active_terrain_inventory']+surface['active_shaders']:assert sha(P/row['file'])==row['sha256']
 record=dict(checks_pass=True,source_terrain_and_scenery_exact=True,all_active_textures_and_shaders_resolved=True,approved_daylight_installed=True,
  physical_declarations_exact_v060=True,reused_authenticated_v060_native_scenery=True,saved_edf_sha256=sha(saved),saved_edf_source_zip_sha256=EXTRA['v060_native_scenery.zip'][2],
  native_scenery_probe_count=len(errors),native_scenery_max_error_m=max(errors),terrain_texture_files=[r['file'] for r in surface['active_terrain_inventory']],
  object_texture_files=sorted(names),object_normal_files=sorted(normals),native_shadow_supersampling=4,native_shadowmap_scale=.1)
 save(O/'native_staging_validation.json',record)
 print('V065_NATIVE_STAGING_PASS; pinned native scene, all textures and',len(errors),'geometry probes checked',flush=True)
 return textures,normal_paths

def collision():
 assert os.name=='nt','Use the Windows workflow';record=read(O/'native_staging_validation.json');assert record['checks_pass']
 edfexe,terrainexe=native_tools();tracked=edfexe.parents[1]/'tracked/tracked.exe';assert tracked.is_file()
 import build_windows_v047 as helper
 helper.P,helper.LOG=P,LOG
 native=dict(scenery=dict(reused=True,sha256=record['saved_edf_sha256'],source_archive_sha256=record['saved_edf_source_zip_sha256'],exact_v060_source=True))
 trh=DEST/(NAME+'.trh');trh.unlink(missing_ok=True)
 native['collision']=run_native(terrainexe,['track.tht',trh,'trh_params.ini'],'terrained_trh_v065',7200)
 with trh.open('rb') as stream:assert stream.read(4)==b'TRH\0'
 native['unmerged_trh_sha256']=sha(trh)
 native['centreline']=run_native(tracked,['-merge',trh,'cl',P/'main.tcl','sa',P/'start.tcl'],'tracked_merge_v065',1800)
 assert sha(trh)!=native['unmerged_trh_sha256']
 from v057_native_heights import collision_heights
 assert np.array_equal(collision_heights(trh),np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049))
 native['complete_collision_grid_exact_approved_roller_source']=True;save(O/'native_compile_results.json',native)
 print('V065_COLLISION_AND_ROUTES_PASS; all 4198401 collision samples exact',flush=True)

def package():
 code=DEST/'code.txt'
 if code.exists():shutil.copy2(code,LOG/'v065_track_code.txt');code.unlink()
 pkz=R/'12_RELEASE/OrlandoMX_2026_v065.pkz';tmp=pkz.with_suffix('.pkz.tmp')
 with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(DEST.iterdir()):
   if p.is_file():z.write(p,NAME+'/'+p.name)
 with zipfile.ZipFile(tmp) as z:assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
 tmp.replace(pkz);pkz.with_suffix('.pkz.sha256').write_text(sha(pkz)+'  '+pkz.name+'\n');return pkz

def validate(native,pkz):
 stage=read(O/'native_staging_validation.json');textures=[P/n for n in stage['object_texture_files']];normals=[P/n for n in stage['object_normal_files']]
 edf=P/'scenery.edf';mappath=DEST/(NAME+'.map');trh=DEST/(NAME+'.trh')
 objects=verify_files(edf,mappath,[p for p in textures if p.name!=MATTE],LOG/'v065_native_object_texture_validation.json',
  legacy_materials=legacy_materials(P/'scenery.fbx',textures),normal_maps=normals);assert objects['checks_pass']
 payloads=[]
 with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  assert raw[:4]==b'MP2\0';matte=specular_records(raw,P/MATTE)
  for row in read(O/'surface_validation.json')['active_terrain_inventory']:
   name=row['file']
   if name.startswith('mask_'):continue
   w,h,digest=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+digest);assert offset>=0,('Native terrain texture mismatch',name)
   payloads.append(dict(texture=name,size=[w,h],pixel_md5=digest.hex(),map_offset=offset,source_sha256=sha(P/name)))
  errors=scan_points(raw,[p['expected_xyz_m'] for p in probes()]);assert all(e is not None for e in errors)
 from v065_native_heights import validate_native_heights
 heights=validate_native_heights(mappath,trh)
 race=read(O/'race_validation.json')
 for row in race['retained_game_files']:assert sha(DEST/row['file'])==row['sha256']
 assert sha(DEST/(NAME+'.amb'))==race['lighting_sha256']==read(S/'native_expected_inputs.json')['daylight']
 assert sha(trh)!=native['unmerged_trh_sha256'] and pkz.stat().st_size<=964987509
 source_checks={name:read(O/(name+'.json')) for name in ['terrain_validation','surface_validation','scenery_validation','race_validation','precompile_validation','native_staging_validation']}
 assert all(q['checks_pass'] for q in source_checks.values())
 surface=source_checks['surface_validation'];assert surface['rgba8_base_level_bytes_before']==surface['rgba8_base_level_bytes_after']
 report=dict(version='v065',baseline='v064 with corrected full start C coverage and the circled visual grass strip cleared',compiled=True,source_checks=True,centerline_merged=True,
  source_commit=os.environ['GITHUB_SHA'],native_build_run=int(os.environ['GITHUB_RUN_ID']),native_compile=native,source_validation=source_checks,
  native_object_textures=objects,native_height_validation=heights,native_collision_exact_accepted_source=True,wall_roller_visual_collision_exact=True,
  all_14_corner_heights_exact_v060=True,scenery_vehicles_sign_exact_v060=True,reused_authenticated_v060_native_scenery=True,
  estimated_source_texture_and_geometry_budget_not_increased=True,texture_allocation_bytes=surface['texture_allocation_bytes'],native_matte_foliage_MAP=matte,
  terrain_texture_payloads=payloads,native_geometry_probes=len(errors),native_geometry_error_max_m=max(errors),approved_daylight_exact=True,
  package_integrity_passed=True,package_size_budget_passed=True,pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),
  map_bytes=mappath.stat().st_size,map_sha256=sha(mappath),trh_sha256=sha(trh),in_game_visual_check=False,in_game_riding_test=False,performance_test=False,
  pending=['MX Bikes appearance and riding test','Wall roller clearance at game speeds','RAM/VRAM and FPS comparison'])
 save(R/'12_RELEASE/OrlandoMX_v065_Validation.json',report)
 (R/'12_RELEASE/Install_v065.txt').write_text('Orlando MX 2026 v065\n\nCopy OrlandoMX_2026_v065.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v065 and reset the track. All players need the same package.\n\nOriginal style B flowing cultivation in all 14 corners. Style C now covers the previously missing opening start straight and the circled left grass strip. Original B corners and the remaining C course stay intact, with 5 metre corner blends. Approved photographic grain, stronger dirt contrast and proposed clear-day lighting are included.\n\nAdds the approved rounded, low wall-entry roller before the large speedway double, landing on the original road. All other terrain and all v060 scenery remain exact, including the Express van, readable cardboard sign and alternating black/silver trucks.\n\nExisting texture slots, dimensions and 14 layers are retained. Source texture allocation is unchanged. Native complete visual/collision height grids, bitmap payloads, scenery probes, race-file hashes and archive CRC passed. Actual in-game visuals, roller riding, RAM/VRAM and FPS require your test.\n',encoding='utf-8')
 print('V065_NATIVE_VALIDATED',pkz.stat().st_size,'bytes',sha(pkz),flush=True)

def final():
 assert os.name=='nt','Use the Windows workflow';assert read(O/'native_staging_validation.json')['checks_pass']
 _,terrainexe=native_tools();import build_windows_v047 as helper
 helper.P,helper.LOG=P,LOG;native=read(O/'native_compile_results.json');assert native['complete_collision_grid_exact_approved_roller_source']
 mappath=DEST/(NAME+'.map');mappath.unlink(missing_ok=True)
 native['terrain']=run_native(terrainexe,['track.hmf',mappath,'map_params.ini'],'terrained_map_v065',9000)
 assert mappath.is_file() and 'Map File Write' in (LOG/'terrained_map_v065.log').read_text();save(O/'native_compile_results.json',native)
 pkz=package()
 from v065_transfer import preserve_native
 preserve_native();validate(native,pkz)

if __name__=='__main__':{'stage':stage,'collision':collision,'final':final}[sys.argv[1]]()
