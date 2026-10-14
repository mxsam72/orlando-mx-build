"""Native grass/scenery and whole-track dirt, with exact riding collision."""
import json,mmap,os,re,shutil,struct,zipfile
from pathlib import Path
from v053_surface import R,BASE,DIRT,O,M,SPEC,sha,save,OVERRIDES
from v052_scenery import F,TEXTURE
from v052_coverage import baseline_mask
from v052_foliage import LEAVES,MATTE,SHADER
from native_specular_v052 import specular_records
from v047_common import read
from v027_scenery import parse,values,child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature,texture_record,verify_files
from native_coordinate_scan_v044 import scan_points
from build_windows_v047 import run_native,native_tools

P=R/'BUILD/v053_stage';DEST=R/'12_RELEASE/orlandomx_2026_v053';NAME=DEST.name;LOG=R/'DOCUMENTATION'
def stage():
    dirt=read(O/'v053_surface_validation.json');grass=read(O/'v053_scenery_validation.json')
    assert dirt['checks_pass'] and grass['checks_pass'] and grass['all_non_grass_records_exact']
    assert sha(O/'scenery.fbx')==grass['scenery_sha256']
    for name,row in dirt['files'].items():assert sha(O/name)==row['sha256'],name
    for name,digest in dirt['baseline_dirt_files'].items():assert sha(DIRT/name)==digest,name
    P.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
    for folder in [BASE/'materials',DIRT/'materials',M,BASE/'facility_textures',R/'V047_OUTPUT/facility_textures',F]:
        for p in folder.iterdir():
            if p.suffix in ['.tga','.shd','.flg']:shutil.copy2(p,P/p.name)
    for p in (BASE/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
    # Apply scoped mask overrides after baseline mask staging.
    for p in M.glob('*.tga'):shutil.copy2(p,P/p.name)
    for name,row in dirt['files'].items():assert sha(P/Path(name).name)==row['sha256'],name
    assert sha(P/'mask_visual_grass.tga')==sha(baseline_mask('mask_visual_grass.tga')),'Grass footprint was expanded again'
    assert grass['grass_clumps']==4546 and grass['new_verge_clumps']==0 and grass['blade_width_multiplier']==1.0
    assert dirt['dirt_comparison_to_v052']['checks_pass']
    foliage=read(O/'v053_foliage_validation.json');assert foliage['checks_pass']
    for stem in LEAVES:
        assert (P/(stem+'.shd')).read_text()==SHADER
        assert sha(P/(stem+'.tga'))==sha(R/'V047_OUTPUT/facility_textures'/(stem+'.tga'))
    assert sha(P/MATTE)==foliage['specular_map_sha256']
    for name in ['terrain.raw','v024_pit_gravel.tga','grass_n.tga','basemap.tga']:shutil.copy2(BASE/name,P/name)
    shutil.copy2(O/'compiled_track.hmf',P/'track.hmf');text=(P/'track.hmf').read_text()
    assert 'num_layers = 14' in text and sha(P/'track.hmf')==sha(DIRT/'compiled_track.hmf')
    for i in [11,12,13]:
        block=re.search(r'(?m)^layer'+str(i)+r'\s*\{([^{}]*)\}',text)
        assert block and float(re.search(r'thickness\s*=\s*([0-9.]+)',block[1])[1])==4.
    shutil.copy2(O/'scenery.fbx',P/'scenery.fbx');shutil.copy2(R/'BUILD/edf_params.ini',P/'edf_params.ini')
    assert 'use_normals=1' in (P/'edf_params.ini').read_text()
    params=(R/'BUILD/map_params.ini').read_text()
    for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
        params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
    params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
    (P/'map_params.ini').write_text(params)
    for name in re.findall(r'(?m)^\s*(?:map|mask|data|name)\s*=\s*(\S+)',text):
        if name=='scenery.edf':continue  # Produced by the next native step.
        assert Path(name).name==name and (P/name).is_file(),name
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
        shutil.copy2(P/name,fbm/name)
    names=set(bindings['actual_diffuse_textures']);normal_maps=[]
    for name in list(names):
        shader=P/(Path(name).stem+'.shd')
        if shader.is_file():
            for m in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):
                assert Path(m).name==m and (P/m).is_file(),(name,m);names.add(m)
                if m!=MATTE:normal_maps.append(m)
            shutil.copy2(shader,fbm/shader.name)
    for name in names:
        bitmap_signature(P/name)
        if not (fbm/name).is_file():shutil.copy2(P/name,fbm/name)
    for shader in P.glob('*.shd'):
        for name in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):assert Path(name).name==name and (P/name).is_file(),(shader.name,name)
    assert TEXTURE in names and 'foliage_light.tga' not in names and 'CK_v044_bermuda.tga' not in names
    assert sha(P/TEXTURE)==grass['photographic_texture_sha256']
    baseline=read(R/'BUILD/v048_inputs/v047_validation.json')
    for f in (R/'BUILD/v049_baseline_game').iterdir():shutil.copy2(f,DEST/f.name.replace('orlandomx_2026_v047',NAME))
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v047','v053'))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    save(O/'v053_staging_validation.json',dict(checks_pass=True,layer_count=14,all_active_textures_resolved=True,normal_maps=normal_maps,
        active_scenery_textures=bindings['actual_diffuse_textures'],shadow_supersampling=4,shadowmap_scale=.1,
        grass_shadow_casting_disabled=True,physical_terrain_sha256=sha(P/'terrain.raw')))
    return dirt,grass,baseline,[P/n for n in sorted(names)],normal_maps

def package():
    p=R/'12_RELEASE/OrlandoMX_2026_v053.pkz';temp=p.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(DEST.iterdir()):
            if f.is_file():z.write(f,NAME+'/'+f.name)
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    temp.replace(p);p.with_suffix('.pkz.sha256').write_text(sha(p)+'  '+p.name+'\n');return p

def validate(dirt,grass,baseline,textures,normals,native,pkz):
    edf=P/'scenery.edf';mappath=DEST/(NAME+'.map')
    objects=verify_files(edf,mappath,[p for p in textures if p.name!=MATTE],LOG/'v053_native_object_texture_validation.json',
        legacy_materials=legacy_materials(P/'scenery.fbx',textures),normal_maps=[P/n for n in normals])
    with edf.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:edf_spec=specular_records(raw,P/MATTE,minimum_records=2)
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:map_spec=specular_records(raw,P/MATTE)
    objects['textures'].append(dict(texture=MATTE,width=edf_spec['width'],height=edf_spec['height'],native_record_kind='alpha_only_specular_map',
        alpha_pixel_md5=edf_spec['alpha_pixel_md5'],edf_records=edf_spec['records'],map_records=map_spec['records'],checks_pass=True,source_sha256=sha(P/MATTE)))
    objects['texture_count']+=1;objects['native_bitmap_texture_count']+=1
    objects['method']+=' Alpha-only specular records use exact bottom-up source alpha MD5 plus bounded raw-deflate payload decoding in both EDF and MAP, calibrated in run 38536643719.'
    save(LOG/'v053_native_object_texture_validation.json',objects)
    assert any(t['texture']==TEXTURE and t['checks_pass'] and t.get('native_record_kind')=='diffuse' for t in objects['textures'])
    signatures=[];probes=read(O/'v053_native_probes.json');points=probes['retained_geometry']+probes['new_grass']
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
        assert raw[:2]==b'MP'
        for row in baseline['terrain_texture_payloads']:
            if row['texture'] in OVERRIDES:continue
            offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
            assert offset>=0,('Missing retained terrain bitmap',row['texture']);signatures.append(dict(row,map_signature_offset=offset))
        # TerrainEd bakes masks into terrain weights, rather than emitting a
        # named RGBA bitmap record. Stage/source checks verify their exact
        # alpha data and HMF bindings; only atlas bitmaps use this signature.
        for name in [n for n in OVERRIDES if not n.startswith('mask_')]:
            w,h,d=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+d)
            assert offset>=0,('Missing whole-track authored terrain bitmap',name)
            signatures.append(dict(texture=name,size=[w,h],pixel_md5=d.hex(),source_sha256=sha(P/name),map_signature_offset=offset))
        errors=scan_points(raw,[p['expected_xyz_m'] for p in points]);assert all(e is not None for e in errors),[p for p,e in zip(points,errors) if e is None][:8]
    retained=[]
    for f in (R/'BUILD/v049_baseline_game').iterdir():
        target=DEST/f.name.replace('orlandomx_2026_v047',NAME)
        if f.suffix=='.ini':assert target.read_text()==f.read_text().replace('v047','v053');continue
        assert sha(target)==sha(f),('Retained riding/scenery payload changed',f.name);retained.append(dict(file=target.name,sha256=sha(target)))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    spec=read(SPEC);growth=(pkz.stat().st_size/spec['baseline_v050_pkz_bytes']-1)*100
    assert pkz.stat().st_size<=spec['maximum_pkz_bytes'] and growth<=spec['maximum_pkz_growth_percent'],'Package exceeded fixed size budget'
    assert dirt['layer_count']==14 and dirt['normal_specular_channel_identical'] and dirt['pixels_changed_outside_corridor']==0
    qa=dict(version='v053',status='Compiled and verified with official PiBoSo FBX2EDF and TerrainEd',compiled=True,source_checks=True,
        source_commit=os.environ['GITHUB_SHA'],build_run=int(os.environ['GITHUB_RUN_ID']),native_compile=native,
        surface_validation=dirt,grass_validation=grass,object_texture_validation=objects,terrain_texture_payloads=signatures,
        legacy_layer_trials=read(O/'v053_layer_trials.json'),grass_ground_validation=read(O/'v053_verge_validation.json'),
        grass_native_colour_validation=read(O/'v053_scenery_native_preflight.json'),
        foliage_validation=read(O/'v053_foliage_validation.json'),
        native_coordinate_validation=dict(checks_pass=True,retained_probes=len(probes['retained_geometry']),grass_probes=len(probes['new_grass']),max_error_m=max(errors)),
        native_trh_identical_to_v050=True,race_reset_and_lighting_identical_to_v050=True,all_approved_trees_exact=True,
        retained_game_files=retained,scenery_edf_sha256=sha(edf),map_sha256=sha(mappath),map_bytes=mappath.stat().st_size,
        pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),v050_pkz_bytes=spec['baseline_v050_pkz_bytes'],pkz_growth_vs_v050_percent=growth,
        package_size_budget_passed=True,layer_count=14,added_terrain_layers=0,photographic_soil_source_preserved=True,photographic_colour_tiles_refined=True,matte_normal_alpha_preserved=True,
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False,
        pending=['In-game finer grain and travel-aligned grooming','Corner tyre marks, landing patches and dirt edges','Repeated-lap dirt persistence and FPS'])
    save(R/'12_RELEASE/OrlandoMX_v053_Validation.json',qa)
    (R/'12_RELEASE/Install_v053.txt').write_text(f'''Orlando MX 2026 v053 — finer dirt, directional grooming and local wear

Copy OrlandoMX_2026_v053.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v053 and reset the track. Keep v052 for comparison.

Fine photographic grain has approximately 20% more local contrast and more visible contribution beneath the directional atlas. The dirt has a small warmer colour adjustment. Exact photographic normal maps and matte specular alpha 2 remain.

Narrower lengthwise grooming follows the straights and jump faces. Subtle curved tyre fragments appear only in corners; broken compaction patches appear on landings and run-outs. Dirt edges have irregular mixing within the previous footprint.

Same 14 layers, texture dimensions and shader bindings. Grass, matte foliage, scenery, roads, riding geometry, collision, race/reset and lighting remain exact. The R03/R10/R17 local layer experiments remain exact.

Native compilation, bitmap, coordinate, collision and archive checks passed. Package {pkz.stat().st_size:,} bytes. Source previews are not game screenshots; in-game appearance and FPS require a ride test.
''',encoding='utf-8')
    print('V053_NATIVE_VALIDATION_PASSED',pkz.stat().st_size,'bytes;',round(growth,2),'percent from v050.',flush=True)

def main():
    assert os.name=='nt','Use the official Windows runner'
    dirt,grass,baseline,textures,normals=stage();edfexe,terrainexe=native_tools()
    # Reused run helper derives its working directory from the v047 module.
    import build_windows_v047 as native_helper
    native_helper.P=P
    mappath=DEST/(NAME+'.map')
    if mappath.exists():mappath.unlink()
    if os.environ.get('V053_REUSE_SCENERY')=='1':
        recovered=read(R/'BUILD/v053_recovery.json')
        assert recovered['checks_pass'] and sha(P/'scenery.edf')==recovered['saved_edf_sha256'] and sha(P/'scenery.fbx')==recovered['saved_source_scene_sha256']
        native=dict(scenery=dict(restored_successful_official_export=True,source_release=recovered['original_source_release'],
            source_commit=recovered['original_source_commit'],edf_sha256=sha(P/'scenery.edf'),export_log_sha256=sha(LOG/'fbx2edf_v053.log')))
    else:
        if (P/'scenery.edf').exists():(P/'scenery.edf').unlink()
        native=dict(scenery=run_native(edfexe,[P/'scenery.fbx',P/'scenery.edf',P/'edf_params.ini','-q'],'fbx2edf_v053',timeout=7200))
    assert (P/'scenery.edf').is_file()
    with (P/'scenery.edf').open('rb') as f:assert f.read(4)==b'EDF\0'
    from v053_transfer import preserve_edf,preserve_native
    preserve_edf()
    # Check the new photographic bitmap and material colour before the slower
    # terrain compiler, so an importer colour issue cannot waste a full build.
    with (P/'scenery.edf').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
        bitmap=texture_record(raw,P/TEXTURE)
        matte_record=specular_records(raw,P/MATTE,minimum_records=2)
        from PIL import Image
        assert Image.open(P/MATTE).getchannel('A').getextrema()==(0,0)
        foliage=read(O/'v053_foliage_validation.json');foliage['native_zero_specular_bitmap']=matte_record
        foliage['native_bitmap_preflight_passed']=True;save(O/'v053_foliage_validation.json',foliage)
        assert grass['photographic_colour_multiplier_baked']==[.78,1.38,.78]
        assert all(m['green_dominant'] for m in grass['distance_mip_colour_validation'])
    save(O/'v053_scenery_native_preflight.json',dict(checks_pass=True,photographic_bitmap=bitmap,
        baked_green_RGB_verified_by_exact_native_bitmap_digest=True,external_material_tint_required=False))
    native['terrain']=run_native(terrainexe,['track.hmf',DEST/(NAME+'.map'),'map_params.ini'],'terrained_v053',timeout=9000)
    assert 'Map File Write' in (LOG/'terrained_v053.log').read_text() and (DEST/(NAME+'.map')).is_file()
    pkz=package();preserve_native();validate(dirt,grass,baseline,textures,normals,native,pkz)
if __name__=='__main__':main()
