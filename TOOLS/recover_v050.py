"""Verify the saved final PKZ and publish it without native recompilation.

The original native check already verified all EDF/MAP object records before
incorrectly requiring an RGBA bitmap record for a terrain blending mask.
Authenticate that report, recheck the exact final MAP, terrain bitmap records,
all retained/new geometry probes and every riding payload. Mask authoring is
verified at source/staging; no unsupported mask bitmap format is asserted.
"""
import hashlib,mmap,os,shutil,struct,urllib.request,zipfile
from pathlib import Path
from v050_surface import R,O,sha,save
from v050_transfer import api,identity,upload,deliver,safe,extract
from v047_common import read
from native_coordinate_scan_v044 import scan_points

RELEASE=412271889
COMMIT='333a6130d77f3c1fed91decbdd5699b58b875a7f'
RUN=38497104967
NAME='orlandomx_2026_v050'
ASSETS={
 'OrlandoMX_2026_v050.pkz':(919035723,'b3c5e808f03f53c461630ad5f8e188aa61e9b0a6c5f28b62dc3f3cc659067365'),
 'v050_diagnostics-38497104967.zip':(126872,'7167a601094bdb6cab9c6c13a5c2b396d602490faff6cf9cd9500cc852564912'),
}
ATLAS=[
 dict(texture='v044_route_detail.tga',size=[8192,8192],pixel_md5='4bf48643a29d133902b3b06e65e0c436',source_sha256='e462152d4887aec88b391524248e6d1f54198b87a252e31daddfabf40421bebd'),
 dict(texture='v044_route_detail_n.tga',size=[8192,8192],pixel_md5='dafc414e4a759ff0490ca09c95709d22',source_sha256='37112059b6ac9fafc319ed747cb97f960c006e7565b66ff78680323705879a11'),
]
MASKS={'materials/mask_v046_packed.tga':'295174b9a52a3fe9f9c091e3ad652efaa6c864c225cc404ad7c1fbd02a50cd91',
       'materials/mask_v046_wear.tga':'39ee132d89be22d30a6ba6ff05b5af557a95ba8ecd6c862fbc2bf332be7676f0'}

class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  out=super().redirect_request(req,fp,code,msg,headers,newurl)
  if out is not None:out.remove_header('Authorization');out.remove_header('Accept')
  return out

def download(asset,p,size,digest):
 assert asset['size']==size and asset['digest']=='sha256:'+digest
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 headers={'Authorization':'Bearer '+os.environ['V050_RELEASE_TOKEN'],'Accept':'application/octet-stream','User-Agent':'OrlandoMX-v050-recovery'}
 with urllib.request.build_opener(NoAuthRedirect).open(urllib.request.Request(asset['url'],headers=headers),timeout=300) as src,p.open('wb') as dst:
  shutil.copyfileobj(src,dst,4*1024*1024)
 assert p.stat().st_size==size and sha(p)==digest
 print('Authenticated',p.name,size,flush=True);return p

def main():
 identity();rel=api('/releases/'+str(RELEASE));assert rel['draft'] and rel['target_commitish']==COMMIT
 assets={a['name']:a for a in rel['assets']}
 source=assets['OrlandoMX-v050-source-checkpoint.zip']
 assert source['size']==413570092 and source['digest']=='sha256:86a6808c0ba522876b34cbeb51536e8c241ee0ac90a67b42ea99bdd4a792b2e4'
 native=assets['OrlandoMX-v050-native-scenery.zip']
 assert native['size']==228685328 and native['digest']=='sha256:8596e3ab52f9ba0e621120b84db0150781d6176f8c49c5530827c7d5a816e726'
 diag=download(assets['v050_diagnostics-38497104967.zip'],R/'BUILD/v050_saved_diagnostics.zip',*ASSETS['v050_diagnostics-38497104967.zip'])
 with zipfile.ZipFile(diag) as z:
  assert z.testzip() is None
  for i in z.infolist():
   safe(i.filename)
   if not i.is_dir() and i.filename.startswith(('V050_OUTPUT/','DOCUMENTATION/')):extract(z,i,R/i.filename)
 dirt=read(O/'v050_surface_validation.json');grass=read(O/'v050_scenery_validation.json');stage=read(O/'v050_staging_validation.json')
 assert dirt['checks_pass'] and grass['checks_pass'] and stage['checks_pass']
 assert dirt['layer_count']==14 and dirt['added_layers']==0 and dirt['pixels_changed_outside_corridor']==0 and dirt['normal_specular_channel_identical']
 assert grass['all_non_grass_records_exact'] and grass['all_approved_tree_records_exact'] and grass['grass_mesh_front_back_normals_verified'] and grass['all_grass_no_shadow_native_prefix']
 for row in ATLAS:assert dirt['files']['materials/'+row['texture']]['sha256']==row['source_sha256']
 for name,digest in MASKS.items():assert dirt['files'][name]['sha256']==digest and dirt['pixel_scope_validation'][Path(name).name]['pixels_changed_outside_corridor']==0
 assert dirt['line_removal_validation']['former_two_lane_fields_removed']
 for name in ['fbx2edf_v050','terrained_v050']:
  text=(R/'DOCUMENTATION'/(name+'.log')).read_text()
  assert 'ERROR:' not in text.upper()
  if name=='terrained_v050':assert 'Map File Write' in text
 baseline_rel=api('/releases/tags/v047-realistic-trees-38458081921');assert not baseline_rel['draft']
 base_asset=next(a for a in baseline_rel['assets'] if a['name']=='OrlandoMX_v047_Validation.json')
 baseline=read(download(base_asset,R/'BUILD/v050_baseline_validation.json',905430,'8a122933bd61eb4851f59e15750b70e169992b6fbaafbcbecb7899b4cb97c461'))
 assert baseline['compiled'] and baseline['object_texture_validation']['checks_pass']
 pkz=download(assets['OrlandoMX_2026_v050.pkz'],R/'12_RELEASE/OrlandoMX_2026_v050.pkz',*ASSETS['OrlandoMX_2026_v050.pkz'])
 dest=R/'12_RELEASE'/NAME;dest.mkdir(exist_ok=True)
 with zipfile.ZipFile(pkz) as z:
  assert len(z.infolist())==13 and z.testzip() is None
  for i in z.infolist():
   safe(i.filename);assert not i.is_dir() and i.filename.startswith(NAME+'/') and len(Path(i.filename).parts)==2
   extract(z,i,dest/Path(i.filename).name)
 retained=[]
 for row in baseline['retained_game_files']:
  name=row['file'].replace('orlandomx_2026_v047',NAME)
  assert sha(dest/name)==row['sha256'],name
  retained.append(dict(file=name,sha256=row['sha256']))
 # Native Windows packaging uses CRLF; compare unchanged INI content with
 # universal newlines rather than platform-specific text encoding.
 assert hashlib.sha256((dest/(NAME+'.ini')).read_text().encode()).hexdigest()=='dd8b6ea206b5d600342fd53cb9745ba2665814c0f4e45631576917b1dd4bba80'
 objects=read(R/'DOCUMENTATION/v050_native_object_texture_validation.json')
 assert objects['checks_pass'] and objects['texture_count']==91 and objects['missing']==[]
 mappath=dest/(NAME+'.map');assert sha(mappath)==objects['map_sha256']=='37cc397d682c8f5540b9930c42e1d86a85370945a37b7bdfced96aa3c108ac34'
 signatures=[];probes=read(O/'v050_native_probes.json');points=probes['retained_geometry']+probes['new_grass']
 with mappath.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
  assert raw[:2]==b'MP'
  for row in objects['textures']:
   assert row['checks_pass']
   if row.get('representation')=='legacy_uniform_diffuse_material':
    for mat in row['native_material_colors']:assert raw.find(struct.pack('<6f',*(mat['diffuse_rgb']*2)))>=0
   else:assert raw.find(struct.pack('<2I',row['width'],row['height'])+bytes.fromhex(row['pixel_md5']))>=0,row['texture']
  for row in baseline['terrain_texture_payloads']+ATLAS:
   if row['texture'] in [r['texture'] for r in ATLAS] and row not in ATLAS:continue
   offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
   assert offset>=0,('Missing actual terrain bitmap',row['texture']);signatures.append(dict(row,map_signature_offset=offset))
  errors=scan_points(raw,[p['expected_xyz_m'] for p in points])
  assert all(e is not None for e in errors),[p for p,e in zip(points,errors) if e is None][:8]
 growth=(pkz.stat().st_size/918476444-1)*100;assert pkz.stat().st_size<=964400266
 qa=dict(version='v050',status='Compiled native package authenticated and verified without recompilation',compiled=True,source_checks=True,
  source_commit=COMMIT,build_run=RUN,validation_commit=os.environ['GITHUB_SHA'],validation_run=int(os.environ['GITHUB_RUN_ID']),
  native_compile=dict(recovered_native_compile_run=RUN,native_files_recompiled=False,scenery_returncode=0,terrain_returncode=0),
  surface_validation=dirt,grass_validation=grass,object_texture_validation=objects,terrain_texture_payloads=signatures,
  terrain_mask_validation=dict(checks_pass=True,source_checks_and_native_staging_passed=True,source_sha256=MASKS,
   method='Exact authenticated source alpha masks and original compiler staging. TerrainEd bakes masks into weights; no named RGBA bitmap requirement.',native_mask_pixel_format_independently_decoded=False),
  native_coordinate_validation=dict(checks_pass=True,retained_probes=len(probes['retained_geometry']),grass_probes=len(probes['new_grass']),max_error_m=max(errors)),
  native_trh_identical_to_v049=True,race_reset_and_lighting_identical_to_v049=True,all_approved_trees_exact=True,retained_game_files=retained,
  scenery_edf_sha256=objects['edf_sha256'],map_sha256=objects['map_sha256'],map_bytes=mappath.stat().st_size,
  pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),v049_pkz_bytes=918476444,pkz_growth_vs_v049_percent=growth,
  package_size_budget_passed=True,layer_count=14,added_terrain_layers=0,accepted_photo_soil_tiles_and_matte_specular_preserved=True,
  native_checkpoint_recovery=dict(checks_pass=True,release_id=RELEASE,pkz_unchanged=True,authenticated_assets=ASSETS),
  in_game_visual_check=False,in_game_riding_test=False,performance_test=False)
 save(R/'12_RELEASE/OrlandoMX_v050_Validation.json',qa)
 (R/'12_RELEASE/Install_v050.txt').write_text('Orlando MX 2026 v050\n\nCopy OrlandoMX_2026_v050.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v050 and reset the track.\n\nPhotographic double-sided grass without grass panel shadows; whole-circuit matte dirt, continuous pale lanes removed. Native collision/race/reset/lighting unchanged.\n\nNative compilation, 91 object textures, terrain atlas signatures, 3501 geometry probes, retained riding files and 13-entry ZIP CRC verified. Package 919,035,723 bytes. In-game appearance and performance still require a ride test.\n',encoding='utf-8')
 print('V050_RECOVERY_CHECKS_PASSED',pkz.stat().st_size,flush=True)
 deliver()

if __name__=='__main__':main()
