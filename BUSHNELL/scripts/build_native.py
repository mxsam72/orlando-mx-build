"""Authenticate source inputs, run official Windows compilers and package Bushnell."""
from pathlib import Path
import argparse, hashlib, json, mmap, os, queue, re, shutil, struct, subprocess, threading, time, urllib.request, zipfile
import numpy as np
from PIL import Image
from native_validation import valid_member,point_checks,height_checks,texture_checks,package_identity,game_filenames
R=Path(__file__).resolve().parents[1];B=R/'build/v001';G=B/'game';LOG=R/'native_logs';OUT=R/'release';INPUT=R/'build/BushnellMX_v001_native_inputs.zip';NAME='BushnellMX_v001'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def relative(path):return path.relative_to(R).as_posix()


def preflight():
    c=json.loads((R/'project.json').read_text());v=json.loads((B/'validation.json').read_text());s=json.loads((B/'scenery_validation.json').read_text());race=json.loads((B/'race_validation.json').read_text())
    if c['game_track_id']!=NAME or c['physics_profile']!='standard_game':raise ValueError('Project identity / physics mismatch')
    if sha(R/c['approved_layout'])!=c['approved_layout_sha256'] or v['approved_layout_sha256']!=c['approved_layout_sha256']:raise ValueError('Approved route changed')
    if not all(d['checks_pass'] for d in [v,s,race]):raise ValueError('Source validation failed')
    if sha(B/'terrain.raw')!=v['source_raw_sha256'] or sha(B/'scenery.fbx')!=s['native_fbx_sha256']:raise ValueError('Source changed after review')
    if (B/'terrain.raw').stat().st_size!=2049**2*2:raise ValueError('Invalid source RAW size')
    for file in list(B.glob('*.hmf'))+list(B.glob('*.tht'))+list(B.glob('*.shd')):
        for ref in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',file.read_text()):
            if Path(ref).name!=ref or not (B/ref).is_file():raise ValueError('Unresolved source reference: '+ref)
    dest=B/'scenery.fbm';dest.mkdir(exist_ok=True)
    for pattern in ['*.tga','*.shd']:
        for path in B.glob(pattern):shutil.copy2(path,dest/path.name)
    return c,v,s,race


def bundle():
    c,v,s,race=preflight()
    # Use the reviewed overview as the track-selection image, with its aspect preserved.
    overview=R/'previews/BushnellMX_v001_03_overview.png'
    if not overview.exists():raise ValueError('Reviewed source overview is missing')
    with Image.open(overview) as im:
        im=im.convert('RGB');im.thumbnail((1024,1024));canvas=Image.new('RGB',(1024,1024),(55,67,55));canvas.paste(im,((1024-im.width)//2,(1024-im.height)//2));canvas.save(G/(NAME+'.tga'))
    extensions={'.raw','.png','.tga','.npz','.npy','.json','.csv','.tcl','.hmf','.tht','.shd','.ini','.fbx','.txt','.svg','.flg','.tl','.rdf','.amb','.tsc','.cfg'}
    paths=[p for folder in [B,G,R/'previews'] for p in folder.iterdir() if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith('.') and p.name!='manifest.json']
    manifest=dict(schema=1,project_id='bushnell-mx',source_commit=os.environ.get('GITHUB_SHA','local'),run_id=os.environ.get('GITHUB_RUN_ID','local'),files={relative(p):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in paths})
    with zipfile.ZipFile(INPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
        for p in paths:z.write(p,relative(p))
    digest=sha(INPUT);save(INPUT.with_suffix('.json'),dict(sha256=digest,bytes=INPUT.stat().st_size,source_commit=manifest['source_commit']))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('input_sha256='+digest+'\n')
    print('BUSHNELL_SOURCE_BUNDLE',digest,INPUT.stat().st_size,flush=True)


def unpack():
    expected=os.environ.get('SOURCE_INPUT_SHA256')
    if not expected or sha(INPUT)!=expected:raise ValueError('Source input archive hash mismatch')
    with zipfile.ZipFile(INPUT) as z:
        manifest=json.loads(z.read('manifest.json'))
        if manifest['source_commit']!=os.environ.get('GITHUB_SHA') or manifest['run_id']!=os.environ.get('GITHUB_RUN_ID'):raise ValueError('Source provenance mismatch')
        if z.testzip() or len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(manifest['files'])|{'manifest.json'}:raise ValueError('Invalid input ZIP')
        for name,entry in manifest['files'].items():
            if not valid_member(name,('build/v001/','previews/')):raise ValueError('Unsafe input archive path')
            data=z.read(name)
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Input file hash mismatch')
            p=R/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    preflight();print('BUSHNELL_INPUTS_AUTHENTICATED',flush=True)


def tools():
    folder=R/'native_tools';folder.mkdir(exist_ok=True)
    for name,entry in json.loads((R/'source/native_tools.json').read_text()).items():
        p=folder/name
        if not p.exists():
            with urllib.request.urlopen(entry['url'],timeout=120) as src,p.open('wb') as out:shutil.copyfileobj(src,out)
        if p.stat().st_size!=entry['bytes'] or sha(p)!=entry['sha256']:raise ValueError('Official compiler download changed; review pin before continuing')
        with zipfile.ZipFile(p) as z:
            if not all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist()):raise ValueError('Invalid tool archive')
            z.extractall(folder)
    return folder/'fbx2edf/fbx2edf_x64.exe',folder/'terrained/terrained.exe',folder/'tracked/tracked.exe'


def run(exe,args,label,timeout):
    LOG.mkdir(exist_ok=True);started=time.monotonic();last=started;chunks=queue.Queue();tail='';error=False
    p=subprocess.Popen([str(exe),*map(str,args)],cwd=B,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
    def reader():
        while True:
            b=os.read(p.stdout.fileno(),4096)
            if not b:break
            chunks.put(b.decode('utf-8',errors='replace'))
        chunks.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start();print('BUSHNELL_NATIVE_START',label,flush=True)
    try:
        with (LOG/(label+'.log')).open('w',encoding='utf-8') as log:
            while True:
                if time.monotonic()-started>timeout:raise TimeoutError(label)
                try:chunk=chunks.get(timeout=1)
                except queue.Empty:chunk=''
                if chunk is None:break
                if chunk:
                    log.write(chunk);log.flush();tail=(tail+chunk)[-6000:];error|='ERROR:' in tail.upper();print(chunk,end='',flush=True)
                if time.monotonic()-last>40:
                    print('BUSHNELL_NATIVE_HEARTBEAT',label,round(time.monotonic()-started),{p.name:p.stat().st_size for p in list(B.glob('*.edf'))+list(G.glob('*.map'))+list(G.glob('*.trh'))},flush=True);last=time.monotonic()
        code=p.wait(timeout=30)
        if code or error:raise RuntimeError(f'{label} failed ({code}): {tail}')
        return dict(returncode=code,seconds=round(time.monotonic()-started,2))
    finally:
        if p.poll() is None:p.kill();p.wait()
        thread.join(timeout=5);p.stdout.close()


def required(path,minimum,magic=None):
    if not path.is_file() or path.stat().st_size<minimum:raise ValueError('Missing or incomplete output: '+str(path))
    if magic:
        with path.open('rb') as f:
            if f.read(len(magic))!=magic:raise ValueError('Incorrect native output header: '+path.name)


def compile_all():
    if os.name!='nt':raise RuntimeError('Native PiBoSo compilation requires Windows')
    c,source,scene,race=preflight();edf,terrain,tracked=tools();results={};OUT.mkdir(exist_ok=True)
    for p in [B/'scenery.edf',G/(NAME+'.map'),G/(NAME+'.trh')]:p.unlink(missing_ok=True)
    results['scenery']=run(edf,['scenery.fbx','scenery.edf','edf_params.ini','-q'],'BushnellMX_scenery',1200);required(B/'scenery.edf',1024,b'EDF\0')
    with (B/'scenery.edf').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:scene_probes=point_checks(data,scene['native_probe_xyz_m'])
    results['collision']=run(terrain,['track.tht',G/(NAME+'.trh'),'trh_params.ini'],'BushnellMX_collision',600);required(G/(NAME+'.trh'),2049**2*2,b'TRH\0')
    before=sha(G/(NAME+'.trh'));results['centerline']=run(tracked,['-merge',G/(NAME+'.trh'),'cl',B/'main.tcl'],'BushnellMX_centerline',300)
    if sha(G/(NAME+'.trh'))==before:raise ValueError('Native centerline merge left TRH unchanged')
    results['graphics']=run(terrain,['track.hmf',G/(NAME+'.map'),'map_params.ini'],'BushnellMX_graphics',1500);required(G/(NAME+'.map'),100000,b'MP2\0')
    heights=height_checks(B/'terrain.raw',G/(NAME+'.map'),G/(NAME+'.trh'))
    with (G/(NAME+'.map')).open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:map_probes=point_checks(data,scene['native_probe_xyz_m'])
    textures=texture_checks(G/(NAME+'.map'),[B/n for n in ['basemap.tga','prepared.tga','prepared_n.tga','soil.tga','grass.tga','BushnellMX_bark.tga','BushnellMX_wood.tga','BushnellMX_white.tga']])
    for file in G.glob('*.tl'):
        b=file.read_bytes()
        if b[:4]!=b'TL \0' or len(b)!=8+struct.unpack_from('<I',b,4)[0]*8 or not np.isfinite(np.frombuffer(b[8:],'<f4')).all():raise ValueError('Invalid native reset boundary')
    for suffix in ['.rdf','.ini','.amb','.tsc','.tga','_map.tga']:required(G/(NAME+suffix),16)
    required(G/'marshals.cfg',16)
    package=OUT/(NAME+'.pkz');temporary=package.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for filename in sorted(game_filenames(NAME)):
            path=G/filename;required(path,16);z.write(path,NAME+'/'+path.name)
    with zipfile.ZipFile(temporary) as z:
        if z.testzip():raise ValueError('Package CRC check failed')
        package_identity(package.name,z.namelist(),NAME)
    temporary.replace(package)
    (OUT/(NAME+'.pkz.sha256')).write_text(sha(package)+'  '+package.name+'\n')
    with zipfile.ZipFile(OUT/'BushnellMX_v001_Previews.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted((R/'previews').glob('BushnellMX_v001*')):z.write(p,p.name)
    install='Bushnell Motocross v001 — first ride test\n\nCopy BushnellMX_v001.pkz into your active MX Bikes mods/tracks folder.\nThe default Windows location is Documents/PiBoSo/MX Bikes/mods/tracks.\nKeep the filename BushnellMX_v001.pkz unchanged. Restart the game and select Bushnell Motocross v001 in Testing.\n\nThis is a native-compiled first pass from the eight supplied GoPro clips.\nStandard game physics; no additional plugin or preset is required.\nThe approved route is retained. Jump heights, lengths, berm heights, widths and landmark positions are estimates. The test grid and pits are provisional.\n\nThe package has passed source/native height, texture, coordinate, centerline and ZIP checks. An in-game load, ride and FPS check remains pending.\nPlease ride the full lap slowly first, then check jump spacing and landings at normal pace.\n'
    (OUT/'BushnellMX_v001_Install.txt').write_text(install,encoding='utf-8')
    shutil.copy2(R/'previews/BushnellMX_v001_03_overview.png',OUT/'BushnellMX_v001_Overview.png')
    report=dict(schema=1,project_id='bushnell-mx',version='v001',source_commit=os.environ.get('GITHUB_SHA','local'),run_id=os.environ.get('GITHUB_RUN_ID','local'),source_input_sha256=os.environ.get('SOURCE_INPUT_SHA256'),native_compiled=True,installable=True,checks_pass=True,physics_profile='standard_game',centerline_merged=True,height_validation=heights,scenery_coordinate_validation=scene_probes,map_coordinate_validation=map_probes,material_payloads=textures,compilers=results,source_validation=source,race_validation=race,pkz_name=package.name,pkz_bytes=package.stat().st_size,pkz_sha256=sha(package),in_game_load_test=False,in_game_riding_test=False,in_game_visual_check=False,multiplayer_test=False,remaining='In-game load, riding, jump tuning, timing and performance verification',outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in G.iterdir() if p.is_file()})
    save(OUT/'BushnellMX_v001_Validation.json',report);print('BUSHNELL_NATIVE_PACKAGE_PASS',package.stat().st_size,sha(package),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['bundle','unpack','compile']);stage=parser.parse_args().stage
    try: {'bundle':bundle,'unpack':unpack,'compile':compile_all}[stage]()
    except Exception as error:
        save(LOG/'BushnellMX_failure.json',dict(error=repr(error)));raise


if __name__=='__main__':main()
