"""Native grass/scenery and whole-track dirt, with exact riding collision."""
import json,mmap,os,re,shutil,struct,zipfile
from pathlib import Path
from v050_surface import R,BASE,DIRT,O,M,SPEC,sha,save,OVERRIDES
from v050_scenery import F,TEXTURE
from v047_common import read
from v027_scenery import parse,values,child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature,verify_files
from native_coordinate_scan_v044 import scan_points
from build_windows_v047 import run_native,native_tools

P=R/'BUILD/v050_stage';DEST=R/'12_RELEASE/orlandomx_2026_v050';NAME=DEST.name;LOG=R/'DOCUMENTATION'
def stage():
    dirt=read(O/'v050_surface_validation.json');grass=read(O/'v050_scenery_validation.json')
    assert dirt['checks_pass'] and grass['checks_pass'] and grass['all_non_grass_records_exact']
    assert sha(O/'scenery.fbx')==grass['scenery_sha256']
    for name,row in dirt['files'].items():assert sha(O/name)==row['sha256'],name
    for name,digest in dirt['baseline_dirt_files'].items():assert sha(DIRT/name)==digest,name
    P.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
    for folder in [BASE/'materials',DIRT/'materials',M,BASE/'facility_textures',R/'V047_OUTPUT/facility_textures',F]:
        for p in folder.iterdir():
            if p.suffix in ['.tga','.shd','.flg']:shutil.copy2(p,P/p.name)
    for p in (BASE/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
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
                assert Path(m).name==m and (P/m).is_file(),(name,m);names.add(m);normal_maps.append(m)
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
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v047','v050'))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    save(O/'v050_staging_validation.json',dict(checks_pass=True,layer_count=14,all_active_textures_resolved=True,normal_maps=normal_maps,
        active_scenery_textures=bindings['actual_diffuse_textures'],shadow_supersampling=4,shadowmap_scale=.1,
        grass_shadow_casting_disabled=True,physical_terrain_sha256=sha(P/'terrain.raw')))
    return dirt,grass,baseline,[P/n for n in sorted(names)],normal_maps

def package():
    p=R/'12_RELEASE/OrlandoMX_2026_v050.pkz';temp=p.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(DEST.iterdir()):
            if f.is_file():z.write(f,NAME+'/'+f.name)
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    temp.replace(p);p.with_suffix('.pkz.sha256').write_text(sha(p)+'  '+p.name+'\n');return p

def validate(dirt,grass,baseline,textures,normals,native,pkz):
    edf=P/'scenery.edf';mappath=DEST/(NAME+'.map')
    objects=verify_files(edf,mappath,textures,LOG/'v050_native_object_texture_validation.json',
        legacy_materials=legacy_materials(P/'scenery.fbx',textures),normal_maps=[P/n for n in normals])
    assert any(t['texture']==TEXTURE and t['checks_pass'] and t.get('native_record_kind')=='diffuse' for t in objects['textures'])
    signatures=[];probes=read(O/'v050_native_probes.json');points=probes['retained_geometry']+probes['new_grass']
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
        assert raw[:2]==b'MP'
        for row in baseline['terrain_texture_payloads']:
            if row['texture'] in OVERRIDES:continue
            offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
            assert offset>=0,('Missing retained terrain bitmap',row['texture']);signatures.append(dict(row,map_signature_offset=offset))
        for name in OVERRIDES:
            w,h,d=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+d)
            assert offset>=0,('Missing whole-track authored terrain bitmap',name)
            signatures.append(dict(texture=name,size=[w,h],pixel_md5=d.hex(),source_sha256=sha(P/name),map_signature_offset=offset))
        errors=scan_points(raw,[p['expected_xyz_m'] for p in points]);assert all(e is not None for e in errors),[p for p,e in zip(points,errors) if e is None][:8]
    retained=[]
    for f in (R/'BUILD/v049_baseline_game').iterdir():
        target=DEST/f.name.replace('orlandomx_2026_v047',NAME)
        if f.suffix=='.ini':assert target.read_text()==f.read_text().replace('v047','v050');continue
        assert sha(target)==sha(f),('Retained riding/scenery payload changed',f.name);retained.append(dict(file=target.name,sha256=sha(target)))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    spec=read(SPEC);growth=(pkz.stat().st_size/spec['baseline_v049_pkz_bytes']-1)*100
    assert pkz.stat().st_size<=spec['maximum_pkz_bytes'] and growth<=spec['maximum_pkz_growth_percent'],'Package exceeded fixed size budget'
    assert dirt['layer_count']==14 and dirt['normal_specular_channel_identical'] and dirt['pixels_changed_outside_corridor']==0
    qa=dict(version='v050',status='Compiled and verified with official PiBoSo FBX2EDF and TerrainEd',compiled=True,source_checks=True,
        source_commit=os.environ['GITHUB_SHA'],build_run=int(os.environ['GITHUB_RUN_ID']),native_compile=native,
        surface_validation=dirt,grass_validation=grass,object_texture_validation=objects,terrain_texture_payloads=signatures,
        native_coordinate_validation=dict(checks_pass=True,retained_probes=len(probes['retained_geometry']),grass_probes=len(probes['new_grass']),max_error_m=max(errors)),
        native_trh_identical_to_v049=True,race_reset_and_lighting_identical_to_v049=True,all_approved_trees_exact=True,
        retained_game_files=retained,scenery_edf_sha256=sha(edf),map_sha256=sha(mappath),map_bytes=mappath.stat().st_size,
        pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),v049_pkz_bytes=spec['baseline_v049_pkz_bytes'],pkz_growth_vs_v049_percent=growth,
        package_size_budget_passed=True,layer_count=14,added_terrain_layers=0,accepted_photo_soil_tiles_and_matte_specular_preserved=True,
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False,
        pending=['In-game grass from both sides and absence of detached panel shadows','Whole-lap no bright paired lanes','Repeated-lap dirt persistence and FPS'])
    save(R/'12_RELEASE/OrlandoMX_v050_Validation.json',qa)
    (R/'12_RELEASE/Install_v050.txt').write_text(f'''Orlando MX 2026 v050 — whole-track natural dirt and photographic grass

Copy OrlandoMX_2026_v050.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v050 and reset the track. Keep v049 for comparison.

All MX jumps, both roller sections and connecting corners use the v049-style visual treatment, adapted to face, crest, landing and shoulder. Removes the two continuous pale compaction bands from the mask and colour atlas. Dirt remains the approved photographic loose/packed palette with specular alpha 2/255 and 4 m cosmetic depths. Uses the same 14 layers and shared atlas pair.

Replaces all 53 legacy solid-green scrub clusters and all 10 old botanical grass batches with {grass['grass_clumps']} photographic Bermuda clumps in {grass['grass_batches']} small spatial batches. Natural 15–42 cm blades, front/back triangles and verified normals, alpha-tested transparency and softer native foliage shading. Grass is visual-only and excluded from shadow casting to remove detached rectangular card shadows. All approved A/B trees, signs, vehicles, facilities, road circuits, collision, race/reset files and lighting are exact.

Official native bitmap, coordinate, collision and archive checks passed. Package {pkz.stat().st_size:,} bytes ({growth:+.2f}% vs v049); fixed size gate passed. In-game appearance, shadow behavior, persistence under deformation and performance still need your ride test.
''',encoding='utf-8')
    print('V050_NATIVE_VALIDATION_PASSED',pkz.stat().st_size,'bytes;',round(growth,2),'percent from v049.',flush=True)

def main():
    assert os.name=='nt','Use the official Windows runner'
    dirt,grass,baseline,textures,normals=stage();edfexe,terrainexe=native_tools()
    # Reused run helper derives its working directory from the v047 module.
    import build_windows_v047 as native_helper
    native_helper.P=P
    for p in [P/'scenery.edf',DEST/(NAME+'.map')]:
        if p.exists():p.unlink()
    native=dict(scenery=run_native(edfexe,[P/'scenery.fbx',P/'scenery.edf',P/'edf_params.ini','-q'],'fbx2edf_v050',timeout=7200))
    assert (P/'scenery.edf').is_file()
    with (P/'scenery.edf').open('rb') as f:assert f.read(4)==b'EDF\0'
    from v050_transfer import preserve_edf,preserve_native
    preserve_edf()
    native['terrain']=run_native(terrainexe,['track.hmf',DEST/(NAME+'.map'),'map_params.ini'],'terrained_v050',timeout=9000)
    assert 'Map File Write' in (LOG/'terrained_v050.log').read_text() and (DEST/(NAME+'.map')).is_file()
    pkz=package();preserve_native();validate(dirt,grass,baseline,textures,normals,native,pkz)
if __name__=='__main__':main()
