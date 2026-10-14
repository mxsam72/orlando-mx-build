"""Official terrain-graphics compilation; exact v047 scenery and collision."""
import json,mmap,os,queue,re,shutil,struct,subprocess,threading,time,urllib.request,zipfile
from pathlib import Path
from v049_surface import R,BASE,DIRT,O,M,SPEC,sha,save
from native_coordinate_scan_v044 import scan_points
from validate_native_textures_v024 import bitmap_signature

NAME='orlandomx_2026_v049';P=R/'BUILD/v049_stage';DEST=R/'12_RELEASE'/NAME;LOG=R/'DOCUMENTATION'
def stage():
    qa=json.loads((O/'v049_surface_validation.json').read_text());assert qa['checks_pass'] and qa['pixels_changed_outside_sample']==0
    for name,row in qa['files'].items():assert sha(O/name)==row['sha256'],name
    for name,digest in qa['baseline_dirt_files'].items():assert sha(DIRT/name)==digest,name
    baseline=json.loads((R/'BUILD/v048_inputs/v047_validation.json').read_text());assert baseline['compiled']
    assert sha(P/'scenery.edf')==baseline['scenery_edf_sha256']
    spec=json.loads(SPEC.read_text());assert sha(BASE/'terrain.raw')==spec['baseline_terrain_sha256']
    P.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
    for folder in [BASE/'materials',DIRT/'materials',M]:
        for f in folder.iterdir():
            if f.suffix in ['.tga','.shd']:shutil.copy2(f,P/f.name)
    for f in (BASE/'masks').glob('*.tga'):shutil.copy2(f,P/('mask_'+f.name))
    for name in ['terrain.raw','v024_pit_gravel.tga','grass_n.tga','basemap.tga']:shutil.copy2(BASE/name,P/name)
    shutil.copy2(O/'compiled_track.hmf',P/'track.hmf');text=(P/'track.hmf').read_text()
    assert 'num_layers = 14' in text
    for i in [11,12,13]:
        block=re.search(r'(?m)^layer'+str(i)+r'\s*\{([^{}]*)\}',text)
        assert block and float(re.search(r'thickness\s*=\s*([0-9.]+)',block[1])[1])==4.,('visual depth',i)
    for name in re.findall(r'(?m)^\s*(?:map|mask|data|name)\s*=\s*(\S+)',text):assert Path(name).name==name and (P/name).is_file(),name
    for shader in P.glob('*.shd'):
        for name in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shader.read_text()):assert Path(name).name==name and (P/name).is_file(),(shader.name,name)
    params=(R/'BUILD/map_params.ini').read_text()
    for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
        params,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',params);assert count==1
    params,count=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',params);assert count==1
    (P/'map_params.ini').write_text(params)
    game=R/'BUILD/v049_baseline_game'
    for f in game.iterdir():shutil.copy2(f,DEST/f.name.replace('orlandomx_2026_v047',NAME))
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v047','v049'))
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    return qa,baseline
def compiler():
    version=json.loads((R/'BUILD/tool_versions.json').read_text())['tt.zip'];tools=R/'BUILD/v049_native_tools';tools.mkdir(parents=True,exist_ok=True)
    archive=tools/'tt.zip'
    with urllib.request.urlopen(version['url'],timeout=120) as src,archive.open('wb') as out:shutil.copyfileobj(src,out)
    assert sha(archive)==version['sha256'] and archive.stat().st_size==version['bytes']
    with zipfile.ZipFile(archive) as z:
        for n in z.namelist():assert not Path(n).is_absolute() and '..' not in Path(n).parts
        z.extractall(tools)
    exe=tools/'terrained/terrained.exe';assert exe.is_file();return exe
def run_native(exe,out,timeout=7200):
    started=time.monotonic();last=started;q=queue.Queue();tail='';has_error=False
    proc=subprocess.Popen([str(exe),'track.hmf',str(out),'map_params.ini'],cwd=P,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
    def reader():
        for line in proc.stdout:q.put(line)
        q.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    try:
        with (LOG/'terrained_v049.log').open('w',encoding='utf-8') as log:
            while True:
                now=time.monotonic()
                if now-started>timeout:raise TimeoutError('v049 native terrain compilation timed out')
                try:line=q.get(timeout=1)
                except queue.Empty:line=''
                if line is None:break
                if line:log.write(line);log.flush();tail=(tail+line)[-6000:];has_error|='ERROR:' in line.upper()
                if now-last>=60:print('Native v049 terrain compiler active, minutes',int((now-started)/60),flush=True);last=now
        code=proc.wait(timeout=60);print(tail,flush=True)
        assert code==0 and not has_error,'Official terrain compiler reported an error'
        assert 'Map File Write' in (LOG/'terrained_v049.log').read_text()
        return dict(returncode=code,seconds=round(time.monotonic()-started,2),log='terrained_v049.log',tool_archive_sha256='3e874eeeec5297fc04d7dbcfbed75ff497a5fb464833c1f2693034f1d7f91aa0')
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        thread.join(timeout=5);proc.stdout.close()
def package():
    p=R/'12_RELEASE/OrlandoMX_2026_v049.pkz'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(DEST.iterdir()):
            if f.is_file():z.write(f,NAME+'/'+f.name)
    with zipfile.ZipFile(p) as z:assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    p.with_suffix('.pkz.sha256').write_text(sha(p)+'  '+p.name+'\n');return p
def validate(qa,baseline,native,pkz):
    mappath=DEST/(NAME+'.map');signatures=[];objects=[]
    points=[row['expected_xyz_m'] for row in baseline['native_coordinate_validation']['MAP_probes']]
    with mappath.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as raw:
        assert raw[:2]==b'MP'
        for row in baseline['terrain_texture_payloads']:
            if row['texture'] in qa['overridden_baseline_atlas_files']:continue
            offset=raw.find(struct.pack('<2I',*row['size'])+bytes.fromhex(row['pixel_md5']))
            assert offset>=0,('Missing retained terrain bitmap',row['texture']);signatures.append(dict(row,map_signature_offset=offset))
        for name in qa['overridden_baseline_atlas_files']:
            w,h,d=bitmap_signature(P/name);offset=raw.find(struct.pack('<2I',w,h)+d)
            assert offset>=0,('Missing authored native terrain bitmap',name)
            signatures.append(dict(texture=name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset,source_sha256=sha(P/name)))
        for row in baseline['object_texture_validation']['textures']:
            if row.get('representation')=='legacy_uniform_diffuse_material':
                for material in row['native_material_colors']:assert raw.find(struct.pack('<6f',*(material['diffuse_rgb']*2)))>=0,('Missing retained native material',row['texture'])
            else:assert raw.find(struct.pack('<2I',row['width'],row['height'])+bytes.fromhex(row['pixel_md5']))>=0,('Missing exact v047 object bitmap',row['texture'])
            objects.append(dict(texture=row['texture'],checks_pass=True,baseline_source_sha256=row['source_sha256'],native_record_kind=row.get('native_record_kind'),baseline_named_record_verified=True))
        errors=scan_points(raw,points);assert all(e is not None for e in errors),'Retained scenery vertex missing'
    retained=[]
    for f in (R/'BUILD/v049_baseline_game').iterdir():
        target=DEST/f.name.replace('orlandomx_2026_v047',NAME)
        if f.suffix=='.ini':
            assert target.read_text()==f.read_text().replace('v047','v049');continue
        assert sha(f)==sha(target),('Retained game payload changed',f.name)
        retained.append(dict(file=target.name,sha256=sha(target)))
    assert sha(P/'scenery.edf')==baseline['scenery_edf_sha256']
    assert sha(DEST/(NAME+'.trh'))=='a5abd307bd50580ad512fd163d899b05dd61d3ad239bbc5626f2427516d44be9'
    result=dict(status='Compiled with official PiBoSo TerrainEd Windows tool; exact delivered v047 scenery and collision reused',version='v049',baseline_version='v047',compiled=True,source_checks=True,
        source_commit=os.environ['GITHUB_SHA'],build_run=int(os.environ['GITHUB_RUN_ID']),native_terrain_compile=native,surface_validation=qa,
        native_trh_identical_to_v047=True,native_scenery_identical_to_v047=True,scenery_edf_sha256=sha(P/'scenery.edf'),
        race_data_and_lighting_identical_to_v047=True,retained_game_files=retained,terrain_texture_payloads=signatures,
        object_texture_validation=dict(checks_pass=True,count=len(objects),textures=objects,method='Authenticated exact v047 EDF, including previously verified named diffuse/normal records; every retained bitmap/material signature verified in the new MAP'),
        native_coordinate_validation=dict(checks_pass=True,probes=len(points),max_error_m=max(errors)),
        tree_style_counts_retained=baseline['tree_validation']['style_counts'],pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),map_bytes=mappath.stat().st_size,map_sha256=sha(mappath),
        v047_pkz_bytes=baseline['pkz_bytes'],pkz_size_delta_percent=(pkz.stat().st_size/baseline['pkz_bytes']-1)*100,
        v048_pkz_bytes=1086826029,pkz_reduction_vs_v048_percent=(1-pkz.stat().st_size/1086826029)*100,
        accepted_albedo_and_matte_specular_preserved=True,layer_count=14,added_layers=0,
        in_game_visual_check=False,in_game_riding_test=False,performance_test=False,
        pending=['Matched in-game v048/v049 finish-through-triple colour and glare comparison','Repeated-lap confirmation with deformation enabled','User FPS/performance check'])
    assert result['pkz_size_delta_percent']<=5.,'Exceeded size budget versus v047'
    assert result['pkz_reduction_vs_v048_percent']>=10.,'Insufficient package reduction versus v048'
    assert qa['all_accepted_albedo_textures_identical'] and qa['normal_specular_channel_identical'] and qa['layer_count']==14
    save(R/'12_RELEASE/OrlandoMX_v049_Validation.json',result)
    (R/'12_RELEASE/Install_v049.txt').write_text('Orlando MX 2026 v049 — matte accepted-colour dirt through the triple\n\nCopy OrlandoMX_2026_v049.pkz into Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v049, reset the track and compare the finish tabletop and complete triple against v048 in matching dry weather/camera. Ride several laps with your usual deformation setting.\n\nEvery accepted v046 colour map, photographic soil tile and shader is exact. Normal-map specular alpha is the accepted 2/255; the full-strength RGB clod normal and two added v048 layers are removed. Improved furrows, compact crests, worn landing paths and bank erosion use only the existing normal atlas/wear mask, across R01, the connector and all three R02 crests, ending at station 190 m. The original 14-layer HMF, 4 m visual depths, collision, race/reset files, lighting and v047 realistic trees are preserved.\n\nNative compilation, bitmap/coordinate/collision/archive checks and package-size limits passed. Source previews include an approximate specular lighting stress test; they are not game footage. In-game appearance, ridden persistence and FPS require your test.\n',encoding='utf-8')
    print('v049 verified:',len(signatures),'terrain bitmaps,',len(objects),'object records,',len(points),'scenery probes; exact collision/race/lighting.',flush=True)
def main():
    assert os.name=='nt','Run the official Windows workflow'
    qa,baseline=stage();exe=compiler();out=DEST/(NAME+'.map')
    if out.exists():out.unlink()
    native=run_native(exe,out);assert out.is_file() and out.stat().st_size>1000000000
    pkz=package()
    from v049_transfer import preserve_native
    preserve_native();validate(qa,baseline,native,pkz)
if __name__=='__main__':main()
