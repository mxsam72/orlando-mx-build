"""Compile reviewed v054 terrain/scenery and both native racing lines."""
import mmap,os,re,shutil,struct,zipfile
from pathlib import Path
from PIL import Image
from v054_geometry import R,BASE,PREV,O,M,DEST,NAME,read,sha,save
from v054_surfaces import source
from v027_scenery import parse,values,child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature,texture_record,verify_files
from native_coordinate_scan_v044 import scan_points
from native_specular_v052 import specular_records
from build_windows_v047 import run_native,native_tools
from v052_foliage import MATTE
from v052_scenery import TEXTURE
from v052_transfer import api,upload

P=R/'BUILD/v054_stage';LOG=R/'DOCUMENTATION'
def stage():
 for name in ['terrain_validation','surface_validation','scenery_validation','race_validation','independent_validation','native_route_validation']:assert read(O/(name+'.json'))['checks_pass']
 recovered=read(R/'BUILD/v054_recovery.json');assert recovered['reviewed_source_recovered_exact']
 assert sha(O/'terrain.raw')==recovered['descriptor']['terrain_sha256'] and sha(O/'scenery.fbx')==recovered['descriptor']['scenery_sha256']
 P.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
 folders=[BASE/'materials',R/'V046_OUTPUT/materials',PREV/'materials',BASE/'facility_textures',R/'V047_OUTPUT/facility_textures',PREV/'facility_textures']
 for folder in folders:
  for p in folder.iterdir():
   if p.suffix in ['.tga','.shd','.flg']:shutil.copy2(p,P/p.name)
 for p in (BASE/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
 for p in M.iterdir():
  if p.suffix in ['.tga','.shd','.flg']:shutil.copy2(p,P/p.name)
 for name in ['grass_n.tga','basemap.tga','v024_pit_gravel.tga']:shutil.copy2(BASE/name,P/name)
 for src,name in [(O/'terrain.raw','terrain.raw'),(O/'scenery.fbx','scenery.fbx'),(O/'main.tcl','main.tcl'),(O/'start.tcl','start.tcl'),(O/'compiled_track.hmf','track.hmf'),(R/'BUILD/v054_track.tht','track.tht'),(R/'BUILD/edf_params.ini','edf_params.ini'),(R/'BUILD/trh_params.ini','trh_params.ini')]:shutil.copy2(src,P/name)
 assert sha(P/'terrain.raw')==read(O/'terrain_validation.json')['terrain_sha256'];assert sha(P/'scenery.fbx')==read(O/'scenery_validation.json')['scenery_sha256']
 assert sha(P/'track.tht')==read(R/'BUILD/v054_input_validation.json')['physical_material_declarations_sha256']
 params=(R/'BUILD/map_params.ini').read_text()
 for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
 params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
 (P/'map_params.ini').write_text(params);assert 'num_layers = 14' in (P/'track.hmf').read_text()
 nodes=parse((P/'scenery.fbx').read_bytes())[0];bindings=actual_diffuse_bindings(nodes);objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']};links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
 fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
 for b in bindings['bindings']:
  name=b['texture'];assert Path(name).name==name
  if not (P/name).is_file():
   video=next(objects[v[1]] for v in links if v[2]==b['texture_id'] and objects.get(v[1],{}).get('name')==b'Video');content=child(video,b'Content')['props'];assert content[:1]==b'R' and struct.unpack_from('<I',content,1)[0]==len(content)-5;(P/name).write_bytes(content[5:])
  shutil.copy2(P/name,fbm/name)
 names=set(bindings['actual_diffuse_textures']);normals=[]
 for name in list(names):
  shader=P/(Path(name).stem+'.shd')
  if shader.is_file():
   for m in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):
    assert (P/m).is_file();names.add(m)
    if m!=MATTE:normals.append(m)
   shutil.copy2(shader,fbm/shader.name)
 for name in names:
  bitmap_signature(P/name)
  if not (fbm/name).is_file():shutil.copy2(P/name,fbm/name)
 for name in ['track.hmf','track.tht']:
  for reference in re.findall(r'(?m)^\s*(?:map|mask|data|name)\s*=\s*(\S+)',(P/name).read_text()):
   if reference=='scenery.edf':continue
   assert Path(reference).name==reference and (P/reference).is_file(),(name,reference)
 for row in read(O/'surface_validation.json')['changed_images']:assert sha(P/row['file'])==row['sha256']
 for row in read(O/'surface_validation.json')['retained_tiles']:assert sha(P/row['file'])==row['sha256']
 assert Image.open(P/MATTE).getchannel('A').getextrema()==(0,0)
 save(O/'native_staging_validation.json',dict(checks_pass=True,reviewed_source_restored_exact=True,layer_count=14,physical_declarations_exact_v052=True,dirt_tiles_and_shaders_exact_v052=True,all_active_textures_resolved=True,terrain_sha256=sha(P/'terrain.raw'),scenery_sha256=sha(P/'scenery.fbx'),textures=list(sorted(names))))
 return [P/n for n in sorted(names)],[P/n for n in sorted(set(normals))]

def package():
 for p in [DEST/'code.txt',P/'code.txt']:
  if p.is_file():
   shutil.copy2(p,LOG/'v054_track_code.txt')
   if p.parent==DEST:p.unlink()
 pkz=R/'12_RELEASE/OrlandoMX_2026_v054.pkz';temp=pkz.with_suffix('.pkz.tmp')
 with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(DEST.iterdir()):
   if p.is_file():z.write(p,NAME+'/'+p.name)
 with zipfile.ZipFile(temp) as z:
  assert z.testzip() is None and len(z.infolist())==13
  assert all(n.startswith(NAME+'/') for n in z.namelist())
 temp.replace(pkz);pkz.with_suffix('.pkz.sha256').write_text(sha(pkz)+'  '+pkz.name+'\n');return pkz

def validate(textures,normals,native,pkz):
 edf=P/'scenery.edf';mappath=DEST/(NAME+'.map');trh=DEST/(NAME+'.trh')
 objects=verify_files(edf,mappath,[p for p in textures if p.name!=MATTE],LOG/'v054_native_object_texture_validation.json',legacy_materials=legacy_materials(P/'scenery.fbx',textures),normal_maps=normals)
 with edf.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:edf_spec=specular_records(raw,P/MATTE,minimum_records=2)
 with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:map_spec=specular_records(raw,P/MATTE)
 objects['textures'].append(dict(texture=MATTE,width=edf_spec['width'],height=edf_spec['height'],native_record_kind='alpha_only_specular_map',alpha_pixel_md5=edf_spec['alpha_pixel_md5'],edf_records=edf_spec['records'],map_records=map_spec['records'],checks_pass=True,source_sha256=sha(P/MATTE)))
 objects['texture_count']+=1;objects['native_bitmap_texture_count']+=1
 objects['method']+=' Alpha-only specular records use exact source alpha MD5 and bounded raw-deflate decoding in both EDF and MAP, as in v052.'
 save(LOG/'v054_native_object_texture_validation.json',objects)
 assert objects['checks_pass'];signatures=[];retained_tiles=[];baseline=read(R/'BUILD/v048_inputs/v052_validation.json');probes=read(O/'native_probes.json');points=probes['retained_geometry']+probes['changed_geometry']
 with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  assert raw[:2]==b'MP'
  for row in baseline['terrain_texture_payloads']:
   if row['texture'] in ['v044_route_detail.tga','v044_route_detail_n.tga']:continue
   offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']));assert offset>=0,('Retained v052 terrain bitmap changed/missing',row['texture']);retained_tiles.append(dict(row,v054_map_signature_offset=offset))
  for name in ['v044_route_detail.tga','v044_route_detail_n.tga']:
   w,h,d=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+d);assert offset>=0,('Missing transported native atlas',name);signatures.append(dict(file=name,size=[w,h],source_sha256=sha(P/name),pixel_md5=d.hex(),native_offset=offset))
  errors=scan_points(raw,[p['expected_xyz_m'] for p in points]);assert all(e is not None for e in errors),[p for p,e in zip(points,errors) if e is None][:10]
 with edf.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  grass=texture_record(raw,P/TEXTURE);foliage=specular_records(raw,P/MATTE,minimum_records=2)
 assert sha(trh)!='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
 assert sha(trh)!=native['unmerged_trh_sha256'],'TrackEd did not merge the changed centreline'
 growth=(pkz.stat().st_size/baseline['pkz_bytes']-1)*100;assert growth<=5 and pkz.stat().st_size<=964987509
 for suffix in ['.amb','.tsc','.tga']:assert sha(DEST/(NAME+suffix))==sha(R/'BUILD/v054_baseline_game'/('orlandomx_2026_v052'+suffix))
 source={n:read(O/(n+'.json')) for n in ['terrain_validation','surface_validation','scenery_validation','race_validation','independent_validation','native_route_validation','native_staging_validation']}
 recovery=read(R/'BUILD/v054_recovery.json')
 report=dict(version='v054',baseline='v052',compiled=True,source_checks=True,centerline_merged=True,native_collision_updated=True,source_validation=source,source_commit=recovery['descriptor']['source_commit'],native_build_commit=os.environ['GITHUB_SHA'],native_build_run=int(os.environ['GITHUB_RUN_ID']),reviewed_source_recovered_exact=True,native_compile=native,native_object_textures=objects,terrain_atlas_signatures=signatures,native_vegetation_bitmap=grass,native_matte_foliage=foliage,native_coordinate_validation=dict(checks_pass=True,retained_probes=len(probes['retained_geometry']),changed_probes=len(probes['changed_geometry']),max_error_m=max(errors)),map_sha256=sha(mappath),trh_sha256=sha(trh),pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),package_integrity_passed=True,package_size_budget_passed=True,package_growth_percent=growth,original_soil_photographs_and_colour_exact=True,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,pending=['MX Bikes load and gate-drop/first-lap timing','Start bank opening and A/C corner riding','Eight rollers, reset lines and FPS'])
 report.update(native_build_commit=os.environ.get('V054_NATIVE_COMPILE_COMMIT',os.environ['GITHUB_SHA']),native_build_run=int(os.environ.get('V054_NATIVE_COMPILE_RUN',os.environ['GITHUB_RUN_ID'])),native_validation_commit=os.environ['GITHUB_SHA'],native_validation_run=int(os.environ['GITHUB_RUN_ID']),retained_terrain_texture_payloads=retained_tiles,native_matte_foliage_MAP=map_spec)
 if (R/'BUILD/v054_native_reuse.json').is_file():report['saved_native_outputs_reused_exact']=read(R/'BUILD/v054_native_reuse.json')
 save(R/'12_RELEASE/OrlandoMX_v054_Validation.json',report)
 (R/'12_RELEASE/Install_v054.txt').write_text('Orlando MX 2026 v054\n\nCopy OrlandoMX_2026_v054.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v054 and reset the track. Keep v052 for comparison.\n\nA/B/C revision from the user\'s annotated v052 map. A extends the approach/return and moves the corner outward. B reroutes the start into the new space with a smooth bank opening and later merge. C broadens the sweep into the eight rollers. Native race/start lines, checkpoints, sectors, reset references and UI map follow the new paths. Starting gates and pit stall world positions are preserved.\n\nv052 soil palette, photographic tiles, normal tiles, matte tree/grass materials, scenery outside the revised paths, road courses, existing signs and pit displays remain. R09 retains its 50 m jump profile; R17 retains eight rollers and 10 m crest spacing.\n\nSource grade/geometry/race/scenery checks, matched source previews, official MAP/TRH compilation, native centreline merge, bitmap/coordinate and archive checks passed. Final in-game load, starts, timing, resets, riding and FPS require a ride test.\n',encoding='utf-8')
 print('V054_NATIVE_PACKAGE_VALIDATED',pkz.stat().st_size,sha(pkz),flush=True)

def main():
 assert os.name=='nt','Run native compilers on the Windows workflow'
 textures,normals=stage();edfexe,terrainexe=native_tools();tracked=edfexe.parents[1]/'tracked/tracked.exe';assert tracked.is_file()
 import build_windows_v047 as helper
 helper.P=P;helper.LOG=LOG
 native={'scenery':run_native(edfexe,['scenery.fbx','scenery.edf','edf_params.ini','-q'],'fbx2edf_v054',7200)}
 assert (P/'scenery.edf').read_bytes()[:4]==b'EDF\0'
 # Preserve the official scenery export and check source coordinates before
 # the slower MAP stage. A validator correction can resume from these files.
 rel=api('/releases/'+os.environ['V054_RELEASE_ID']);assert rel['draft']
 scene_archive=R/'BUILD/OrlandoMX-v054-native-scenery.zip'
 with zipfile.ZipFile(scene_archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:z.write(P/'scenery.edf','scenery.edf');z.write(LOG/'fbx2edf_v054.log','fbx2edf_v054.log')
 upload(rel,scene_archive)
 points=read(O/'native_probes.json');points=points['retained_geometry']+points['changed_geometry']
 with (P/'scenery.edf').open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
  specular_records(raw,P/MATTE,minimum_records=2);texture_record(raw,P/TEXTURE)
  errors=scan_points(raw,[p['expected_xyz_m'] for p in points])
  save(O/'native_scenery_preflight.json',dict(checks_pass=all(e is not None for e in errors),probe_count=len(points),missing=[p for p,e in zip(points,errors) if e is None]))
  assert all(e is not None for e in errors),('Scenery source coordinates missing from official EDF',[p for p,e in zip(points,errors) if e is None][:8])
 trh=DEST/(NAME+'.trh');mappath=DEST/(NAME+'.map')
 for p in [trh,mappath]:p.unlink(missing_ok=True)
 native['collision']=run_native(terrainexe,['track.tht',trh,'trh_params.ini'],'terrained_trh_v054',7200)
 assert trh.stat().st_size>2049*2049*2 and trh.read_bytes()[:3]==b'TRH';native['unmerged_trh_sha256']=sha(trh)
 native['centreline']=run_native(tracked,['-merge',trh,'cl',P/'main.tcl','sa',P/'start.tcl'],'tracked_merge_v054',1800)
 assert sha(trh)!=native['unmerged_trh_sha256']
 native['terrain']=run_native(terrainexe,['track.hmf',mappath,'map_params.ini'],'terrained_map_v054',9000)
 assert 'Map File Write' in (LOG/'terrained_map_v054.log').read_text() and mappath.is_file()
 save(O/'native_compile_results.json',native);pkz=package()
 for p in [pkz,pkz.with_suffix('.pkz.sha256'),O/'native_compile_results.json']:upload(rel,p)
 validate(textures,normals,native,pkz)
if __name__=='__main__':main()
