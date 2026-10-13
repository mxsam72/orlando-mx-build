"""Compile only terrain graphics; reuse the exact delivered v044 EDF and TRH."""
import hashlib,json,mmap,os,queue,re,shutil,struct,subprocess,sys,threading,time,urllib.request,zipfile
from pathlib import Path
from v046_surface import R,BASE,O,M,SPEC,sha,save_json,check_visual_depths
from native_coordinate_scan_v044 import scan_points
from validate_native_textures_v024 import bitmap_signature

NAME='orlandomx_2026_v046';P=R/'BUILD/v046_stage';DEST=R/'12_RELEASE'/NAME;LOG=R/'DOCUMENTATION'

def run_native(exe,args,timeout=7200):
    started=time.monotonic();last=started;q=queue.Queue();tail='';has_error=False
    proc=subprocess.Popen([str(exe),*map(str,args)],cwd=P,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
    def reader():
        for line in proc.stdout:q.put(line)
        q.put(None)
    t=threading.Thread(target=reader,daemon=True);t.start()
    try:
        with (LOG/'terrained_v046.log').open('w',encoding='utf-8') as log:
            while True:
                now=time.monotonic()
                if now-started>timeout:raise TimeoutError('v046 terrain compilation exceeded '+str(timeout)+' seconds')
                try:line=q.get(timeout=1)
                except queue.Empty:line=''
                if line is None:break
                if line:log.write(line);log.flush();tail=(tail+line)[-5000:];has_error|='ERROR:' in line.upper()
                if now-last>=60:print('v046 native terrain compiler active, minutes',int((now-started)/60),flush=True);last=now
        code=proc.wait(timeout=60);print(tail,flush=True)
        assert code==0 and not has_error,'Official terrain compiler returned an error'
        return dict(returncode=code,seconds=round(time.monotonic()-started,2),log='terrained_v046.log')
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        t.join(timeout=5);proc.stdout.close()

def stage():
    qa=json.loads((O/'v046_surface_validation.json').read_text());assert qa['checks_pass']
    assert qa['full_route'] and qa['accepted_v045_materials_identical']
    spec=json.loads(SPEC.read_text());assert check_visual_depths((O/'compiled_track.hmf').read_text(),spec)==qa['visual_layer_depths_m']
    for name,entry in qa['new_files'].items():assert sha(O/name)==entry['sha256'],name
    for name,digest in qa['baseline_files'].items():assert sha(BASE/name)==digest,name
    P.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
    baseline=json.loads((R/'BUILD/v046_baseline_validation.json').read_text())
    assert sha(P/'scenery.edf')==baseline['object_texture_validation']['edf_sha256']
    for p in (BASE/'materials').iterdir():
        if p.suffix in ['.tga','.shd']:shutil.copy2(p,P/p.name)
    for p in (BASE/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
    for p in M.iterdir():
        if p.suffix in ['.tga','.shd']:shutil.copy2(p,P/p.name)
    for name in ['terrain.raw','v024_pit_gravel.tga','grass_n.tga','basemap.tga']:shutil.copy2(BASE/name,P/name)
    shutil.copy2(O/'compiled_track.hmf',P/'track.hmf')
    params=(R/'BUILD/map_params.ini').read_text()
    for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
        params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
    params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
    (P/'map_params.ini').write_text(params)
    for name in re.findall(r'(?m)^\s*(?:map|mask|data|name)\s*=\s*(\S+)',(P/'track.hmf').read_text()):
        assert Path(name).name==name and (P/name).is_file(),name
    for shader in P.glob('*.shd'):
        for name in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):
            assert Path(name).name==name and (P/name).is_file(),(shader.name,name)
    game=R/'BUILD/v046_baseline_game'
    for p in game.iterdir():
        name=p.name.replace('orlandomx_2026_v044',NAME);shutil.copy2(p,DEST/name)
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v044','v046'))
    assert sha(DEST/(NAME+'.trh'))==sha(game/'orlandomx_2026_v044.trh')
    versions=json.loads((R/'BUILD/tool_versions.json').read_text())
    tools=R/'BUILD/v046_native_tools';tools.mkdir(parents=True,exist_ok=True)
    for name,version in versions.items():
        archive=tools/name
        with urllib.request.urlopen(version['url'],timeout=120) as src,archive.open('wb') as out:shutil.copyfileobj(src,out)
        assert sha(archive)==version['sha256'] and archive.stat().st_size==version['bytes']
        with zipfile.ZipFile(archive) as z:
            for entry in z.namelist():assert not Path(entry).is_absolute() and '..' not in Path(entry).parts
            z.extractall(tools)
    exe=tools/'terrained/terrained.exe';assert exe.is_file()
    return qa,baseline,exe

def package():
    pkz=R/'12_RELEASE/OrlandoMX_2026_v046.pkz'
    with zipfile.ZipFile(pkz,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(DEST.iterdir()):
            if p.is_file():z.write(p,NAME+'/'+p.name)
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    pkz.with_suffix('.pkz.sha256').write_text(sha(pkz)+'  '+pkz.name+'\n')
    return pkz

def validate(qa,baseline,native,pkz):
    mappath=DEST/(NAME+'.map');signatures=[];objects=[]
    points=[p['expected_xyz_m'] for p in baseline['native_coordinate_validation']['MAP_probes']]
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
        assert raw[:2]==b'MP'
        # Existing source textures are immutable and their native payload digests
        # must be present along with every new colour and normal map.
        for row in baseline['terrain_texture_payloads']:
            if row['texture'] in qa['overridden_baseline_atlas_files']:continue
            offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
            assert offset>=0,('Missing baseline terrain texture',row['texture'])
            signatures.append(dict(row,map_signature_offset=offset))
        for name in ['v045_loose.tga','v045_loose_n.tga','v045_packed.tga','v045_packed_n.tga','v044_route_detail.tga','v044_route_detail_n.tga']:
            w,h,d=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+d)
            assert offset>=0,('Missing new native terrain bitmap',name)
            signatures.append(dict(texture=name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset,source_sha256=sha(P/name)))
        for row in baseline['object_texture_validation']['textures']:
            if row.get('representation')=='legacy_uniform_diffuse_material':
                for material in row['native_material_colors']:
                    assert raw.find(struct.pack('<6f',*(material['diffuse_rgb']*2)))>=0,('Missing retained native material',row['texture'])
            else:
                assert raw.find(struct.pack('<2I',row['width'],row['height'])+bytes.fromhex(row['pixel_md5']))>=0,('Missing retained object bitmap',row['texture'])
            objects.append(dict(texture=row['texture'],checks_pass=True))
        errors=scan_points(raw,points);assert all(e is not None for e in errors),'Retained scenery vertex missing'
    game=R/'BUILD/v046_baseline_game';unchanged=[]
    for p in game.iterdir():
        target=DEST/p.name.replace('orlandomx_2026_v044',NAME)
        if p.suffix=='.ini':continue
        assert sha(p)==sha(target),('Retained game payload changed',p.name)
        unchanged.append(dict(file=target.name,sha256=sha(target)))
    assert sha(P/'scenery.edf')==baseline['object_texture_validation']['edf_sha256']
    assert sha(DEST/(NAME+'.trh'))==baseline['outputs']['orlandomx_2026_v044.trh']['sha256']
    result=dict(status='Compiled with official PiBoSo TerrainEd Windows tool; delivered native v044 scenery and collision reused unchanged',version='v046',baseline_version='v044',compiled=True,centerline_merged=True,source_checks=True,
        source_commit=os.environ['GITHUB_SHA'],build_run=int(os.environ['GITHUB_RUN_ID']),native_terrain_compile=native,surface_validation=qa,
        native_trh_identical_to_v044=True,native_scenery_identical_to_v044=True,scenery_edf_sha256=sha(P/'scenery.edf'),
        race_data_and_lighting_identical_to_v044=True,retained_game_files=unchanged,terrain_texture_payloads=signatures,
        object_texture_validation=dict(checks_pass=True,count=len(objects),textures=objects),
        native_coordinate_validation=dict(checks_pass=True,probes=len(points),max_error_m=max(errors)),
        pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),map_sha256=sha(mappath),in_game_visual_check=False,performance_test=False,
        pending=['Ridden confirmation that the new dirt survives repeated laps with track deformation enabled','User whole-track appearance and performance check'])
    save_json(R/'12_RELEASE/OrlandoMX_v046_Validation.json',result)
    (R/'12_RELEASE/Install_v046.txt').write_text('Orlando MX 2026 v046 — persistent dirt across the whole circuit\n\nCopy OrlandoMX_2026_v046.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v046 and reset the track before the first comparison. Test several laps with your usual track-deformation setting enabled.\n\nThe accepted v045 4K photographic dirt and paired normal maps now cover the whole riding circuit, including the rollers before the finish and beyond the table-single. All three new visual layers have explicit 4 m depths so ridden deformation does not immediately strip the new material away. Physical terrain, rut physics, race data, scenery and lighting are retained from the delivered track.\n\nOfficial native terrain compilation and source, bitmap, scenery-coordinate, collision and archive checks passed. In-game ridden persistence and performance confirmation remain pending your test.\n',encoding='utf-8')
    print('v046 complete: all new bitmaps, 772 retained scenery probes and unchanged TRH/race/weather verified.',flush=True)

def main():
    assert os.name=='nt','Use official Windows workflow'
    qa,baseline,exe=stage();out=DEST/(NAME+'.map')
    if out.exists():out.unlink()
    print('Compiling terrain only with the authenticated v044 native scenery; no FBX export or collision rebuild.',flush=True)
    native=run_native(exe,['track.hmf',out,'map_params.ini'])
    assert out.is_file() and out.stat().st_size>900000000
    pkz=package()
    # Preserve the costly native result before extended bitmap / vertex checks.
    from v046_transfer import preserve_native
    preserve_native();validate(qa,baseline,native,pkz)

if __name__=='__main__':main()
