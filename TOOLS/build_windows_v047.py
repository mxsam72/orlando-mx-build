"""Compile approved tree scenery and v046 graphics; retain native collision."""
import mmap,os,queue,re,shutil,struct,subprocess,threading,time,urllib.request,zipfile
from v047_common import *
from v027_scenery import parse,values,child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature,verify_files
from native_coordinate_scan_v044 import scan_points
from v046_surface import check_visual_depths

LOG=R/'DOCUMENTATION'

def run_native(exe,args,label,timeout=9000):
    print('Running',label,flush=True);started=time.monotonic();last=started;q=queue.Queue();tail='';has_error=False
    proc=subprocess.Popen([str(exe),*map(str,args)],cwd=P,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
    def reader():
        try:
            for line in proc.stdout:q.put(line)
        finally:q.put(None)
    t=threading.Thread(target=reader,daemon=True);t.start()
    try:
        with (LOG/(label+'.log')).open('w',encoding='utf-8') as log:
            while True:
                now=time.monotonic()
                if now-started>timeout:raise TimeoutError(label+' exceeded '+str(timeout)+' seconds')
                try:line=q.get(timeout=1)
                except queue.Empty:line=''
                if line is None:break
                if line:log.write(line);log.flush();tail=(tail+line)[-6000:];has_error|='ERROR:' in line.upper()
                if now-last>=60:print(label+': compiler active, minutes '+str(int((now-started)/60)),flush=True);last=now
        code=proc.wait(timeout=60);print(tail,flush=True)
        assert code==0 and not has_error,'Official compiler failed: '+label
        return dict(returncode=code,seconds=round(time.monotonic()-started,2),log=label+'.log')
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        t.join(timeout=5);proc.stdout.close()

def stage():
    q=read(O/'v047_scenery_validation.json');baseline=read(R/'BUILD/OrlandoMX_v046_Validation.json')
    assert q['checks_pass'] and q['scenery_sha256']==sha(O/'scenery.fbx')
    dirt=baseline['surface_validation'];assert dirt['checks_pass'] and dirt['full_route']
    for name,item in dirt['new_files'].items():assert sha(DIRT/name)==item['sha256'],name
    for name,digest in dirt['baseline_files'].items():assert sha(BASE/name)==digest,name
    assert check_visual_depths((DIRT/'compiled_track.hmf').read_text(),read(R/'V046_SOURCE/visual_spec.json'))=={'11':4.0,'12':4.0,'13':4.0}
    P.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
    for folder in [BASE/'materials',DIRT/'materials',BASE/'facility_textures',F]:
        for p in folder.iterdir():
            if p.suffix in ['.tga','.shd']:shutil.copy2(p,P/p.name)
    for p in (BASE/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
    for name in ['terrain.raw','v024_pit_gravel.tga','grass_n.tga','basemap.tga']:shutil.copy2(BASE/name,P/name)
    for source,target in [(DIRT/'compiled_track.hmf',P/'track.hmf'),(O/'scenery.fbx',P/'scenery.fbx'),(R/'BUILD/edf_params.ini',P/'edf_params.ini')]:shutil.copy2(source,target)
    assert 'use_normals=1' in (P/'edf_params.ini').read_text()
    params=(R/'BUILD/map_params.ini').read_text()
    for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
        params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
    params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
    (P/'map_params.ini').write_text(params)
    assert sha(P/'track.hmf')==dirt['new_files']['compiled_track.hmf']['sha256']
    for name in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',(P/'track.hmf').read_text()):
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
    texture_names=set(bindings['actual_diffuse_textures'])
    for name in list(texture_names):
        shader=P/(Path(name).stem+'.shd')
        if shader.is_file():
            for m in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):
                assert Path(m).name==m and (P/m).is_file(),(name,m);texture_names.add(m)
            shutil.copy2(shader,fbm/shader.name)
    for name in texture_names:
        bitmap_signature(P/name)
        if not (fbm/name).is_file():shutil.copy2(P/name,fbm/name)
    for shader in P.glob('*.shd'):
        for name in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):assert Path(name).name==name and (P/name).is_file(),(shader.name,name)
    for row in q['new_tree_textures']:
        assert sha(P/row['file'])==row['sha256']==sha(TREES/'textures'/row['approved_source_file'])
    save(O/'v047_staging_validation.json',dict(checks_pass=True,v046_dirt_preserved_exact=True,visual_layer_depths_m={'11':4.0,'12':4.0,'13':4.0},physical_terrain_exact=True,
        shade_normals_preserved=True,shadow_supersampling=4,shadowmap_scale=.1,terrain_self_shadowing=True,all_active_texture_references_resolved=True,
        textures=[dict(file=name,sha256=sha(P/name)) for name in sorted(texture_names)],active_scenery_textures=bindings['actual_diffuse_textures']))
    print('Staged approved tree scenery and exact v046 dirt;',len(texture_names),'active object color/normal bitmaps resolved.',flush=True)
    return q,baseline,[P/n for n in sorted(texture_names)]

def stage_game(baseline):
    game=R/'BUILD/v047_baseline_game'
    assert len(list(game.iterdir()))==12
    for p in game.iterdir():shutil.copy2(p,DEST/p.name.replace('orlandomx_2026_v046',NAME))
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v046','v047'))
    for row in baseline['retained_game_files']:assert sha(DEST/row['file'].replace('orlandomx_2026_v046',NAME))==row['sha256']

def native_tools():
    versions=read(R/'BUILD/tool_versions.json');tools=R/'BUILD/v047_native_tools';tools.mkdir(parents=True,exist_ok=True)
    for name,v in versions.items():
        p=tools/name
        if not p.is_file() or sha(p)!=v['sha256']:
            req=urllib.request.Request(v['url'],headers={'User-Agent':'OrlandoMX-v047-build'})
            with urllib.request.urlopen(req,timeout=120) as src,p.open('wb') as out:shutil.copyfileobj(src,out)
        assert sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts
            z.extractall(tools)
    edf=tools/'fbx2edf/fbx2edf_x64.exe';terrain=tools/'terrained/terrained.exe'
    assert edf.is_file() and terrain.is_file();return edf,terrain

def package():
    pkz=R/'12_RELEASE/OrlandoMX_2026_v047.pkz';temp=pkz.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(DEST.iterdir()):
            if p.is_file():z.write(p,NAME+'/'+p.name)
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    temp.replace(pkz);pkz.with_suffix('.pkz.sha256').write_text(sha(pkz)+'  '+pkz.name+'\n');return pkz

def validate(q,baseline,textures,native,pkz):
    mappath=DEST/(NAME+'.map');legacy=legacy_materials(P/'scenery.fbx',textures)
    objects=verify_files(P/'scenery.edf',mappath,textures,LOG/'v047_native_object_texture_validation.json',legacy_materials=legacy)
    assert all(any(t['texture']==name and t['checks_pass'] for t in objects['textures']) for name in ['CK_TREE_v047_pine.tga','CK_TREE_v047_woodland.tga','pine_bark.tga','pine_bark_n.tga'])
    signatures=[];coords=[];probes=read(O/'v047_native_probes.json');points=probes['retained_geometry']+probes['new_trees']
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
        assert raw[:2]==b'MP'
        for row in baseline['terrain_texture_payloads']:
            offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
            assert offset>=0,('Delivered v046 terrain bitmap changed/missing',row['texture'])
            signatures.append(dict(row,map_signature_offset=offset))
        errors=scan_points(raw,[p['expected_xyz_m'] for p in points])
        assert all(e is not None for e in errors),('Missing native scenery vertices',[p for p,e in zip(points,errors) if e is None][:10])
        coords=[dict(p,error_m=e) for p,e in zip(points,errors)]
    assert sha(P/'track.hmf')==baseline['surface_validation']['new_files']['compiled_track.hmf']['sha256']
    unchanged=[]
    for row in baseline['retained_game_files']:
        name=row['file'].replace('orlandomx_2026_v046',NAME);assert sha(DEST/name)==row['sha256'];unchanged.append(dict(file=name,sha256=row['sha256']))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    delta=100*(pkz.stat().st_size/baseline['pkz_bytes']-1)
    qa=dict(status='Compiled with official PiBoSo FBX2EDF and TerrainEd; exact delivered collision reused',version='v047',baseline_version='v046',compiled=True,source_checks=True,centerline_merged=True,
        source_commit=os.environ['GITHUB_SHA'],build_run=int(os.environ['GITHUB_RUN_ID']),native_compile=native,tree_validation=q,
        v046_dirt_preserved_exact=True,v046_surface_validation=baseline['surface_validation'],native_trh_identical_to_v046=True,physical_riding_layout_and_rut_physics_preserved=True,
        race_data_and_lighting_identical_to_v046=True,retained_game_files=unchanged,terrain_texture_payloads=signatures,object_texture_validation=objects,
        native_coordinate_validation=dict(checks_pass=True,retained_geometry_probes=len(probes['retained_geometry']),new_tree_probes=len(probes['new_trees']),max_error_m=max(errors),MAP_probes=coords),
        scenery_edf_bytes=(P/'scenery.edf').stat().st_size,scenery_edf_sha256=sha(P/'scenery.edf'),map_bytes=mappath.stat().st_size,map_sha256=sha(mappath),
        pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),v046_pkz_bytes=baseline['pkz_bytes'],pkz_size_delta_percent=delta,in_game_visual_check=False,in_game_riding_test=False,performance_test=False,
        pending=['User MX Bikes load and foliage appearance/motion check','User FPS and load-time comparison','User ridden dirt-persistence confirmation'])
    save(R/'12_RELEASE/OrlandoMX_v047_Validation.json',qa)
    notes=f'''Orlando MX 2026 v047 — Approved realistic trees

Copy OrlandoMX_2026_v047.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v047. Keep v046 installed for comparison. Use the same standard dry weather and graphics settings.

Replaces all 369 previous generic, scan and facility trees. Retains {q['tree_count_after']} new trees: {q['style_counts']['A']} A airy pines and {q['style_counts']['B']} B dense woodland trees. All 201 near-course/facility placements remain. 72 distant placements removed; this is static thinning, not dynamic LOD or pop-in. All foliage uses the approved true-alpha photographic-style atlases, with individual leaf/needle sprays, real branches, varied height/width/yaw, front/back geometry, transformed approved normals, native color-key transparency and native tree shading.

Whole-track v046 dirt, masks and 4 m cosmetic visual-layer depths remain byte-identical. Native collision, MX jumps and riding layout, race/reset data, rut physics and lighting are retained. Grass, scrub, buildings, signs, vehicles and flag geometry remain exact. Only graphics and the version display name changed.

Official source/native bitmap, geometry, collision and PKZ archive checks passed. Actual in-game appearance and FPS remain pending your test. Multiplayer server and clients must use the same version.

Download size: {pkz.stat().st_size:,} bytes ({delta:+.2f}% from v046).
'''
    (R/'12_RELEASE/Install_v047.txt').write_text(notes,encoding='utf-8')
    print('V047_NATIVE_VALIDATION_PASSED',pkz.stat().st_size,'bytes; change',round(delta,2),'percent;',q['style_counts'],flush=True)

def main():
    assert os.name=='nt','Use the official Windows workflow'
    q,baseline,textures=stage();stage_game(baseline);edf,terrain=native_tools()
    from v047_transfer import preserve_edf,preserve_native
    native={};native['scenery']=run_native(edf,['scenery.fbx','scenery.edf','edf_params.ini','-q'],'fbx2edf_v047')
    assert (P/'scenery.edf').is_file() and (P/'scenery.edf').stat().st_size>10000000
    with (P/'scenery.edf').open('rb') as f:assert f.read(4)==b'EDF\0'
    preserve_edf()
    out=DEST/(NAME+'.map')
    if out.exists():out.unlink()
    native['terrain']=run_native(terrain,['track.hmf',out,'map_params.ini'],'terrained_v047',10800)
    assert out.is_file() and out.stat().st_size>500000000
    pkz=package();preserve_native();validate(q,baseline,textures,native,pkz)

if __name__=='__main__':main()
