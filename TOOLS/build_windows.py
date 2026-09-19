#!/usr/bin/env python3
"""Compile the actual MX Bikes files on Windows, validate, then create a PKZ.

Only Python's standard library is required. No admin rights, security setting
changes, game installation, or game license are needed by the authoring tools.
"""
from pathlib import Path
import sys,os,shutil,json,hashlib,zipfile,urllib.request,subprocess,time,struct
ROOT=Path(__file__).resolve().parents[1]
NAME='orlandomx_2026_v005'
LOG=ROOT/'DOCUMENTATION';STAGE=ROOT/'BUILD/stage';OUT=ROOT/'12_RELEASE'/NAME
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def run(exe,args,label,timeout=1800):
    print('Running',label,flush=True)
    started=time.time();p=subprocess.run([str(exe),*map(str,args)],cwd=STAGE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',timeout=timeout)
    text=p.stdout; (LOG/f'{label}.log').write_text(text,encoding='utf-8')
    print(text[-5000:],flush=True)
    if p.returncode:raise RuntimeError(f'{label} returned {p.returncode}; see DOCUMENTATION/{label}.log')
    # These native tools can return zero despite an import problem.
    if 'ERROR:' in text.upper():raise RuntimeError(f'{label} reported an error; see its log')
    return dict(returncode=p.returncode,seconds=round(time.time()-started,2),log=f'{label}.log')
def required(path,min_size=16,magic=None):
    if not path.is_file() or path.stat().st_size<min_size:raise RuntimeError(f'Missing or incomplete output: {path}')
    if magic:
        with path.open('rb') as f:head=f.read(len(magic))
        if head!=magic:raise RuntimeError(f'Incorrect native header in {path.name}: {head!r}')
def stage():
    STAGE.mkdir(parents=True,exist_ok=True);LOG.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    for f in (ROOT/'04_TEXTURES').glob('*.tga'):copy(f,STAGE/f.name)
    for f in (ROOT/'05_NORMALS').glob('*.tga'):copy(f,STAGE/f.name)
    for f in (ROOT/'06_SHADERS').glob('*.shd'):copy(f,STAGE/f.name)
    for f in (ROOT/'03_MASKS').glob('*.tga'):copy(f,STAGE/('mask_'+f.name))
    for f in (ROOT/'BUILD').glob('*.ini'):copy(f,STAGE/f.name)
    for f in (ROOT/'BUILD').glob('*.hmf'):copy(f,STAGE/f.name)
    for f in (ROOT/'BUILD').glob('*.tht'):copy(f,STAGE/f.name)
    copy(ROOT/'02_HEIGHTMAP/terrain.raw',STAGE/'terrain.raw')
    copy(ROOT/'07_OBJECTS_SOURCE/scenery.fbx',STAGE/'scenery.fbx')
    for f in (ROOT/'09_TRACKED').glob('*.tcl'):copy(f,STAGE/f.name)
    if (ROOT/'07_OBJECTS_SOURCE/scenery.fbm').is_dir():shutil.copytree(ROOT/'07_OBJECTS_SOURCE/scenery.fbm',STAGE/'scenery.fbm',dirs_exist_ok=True)
    if (STAGE/'terrain.raw').stat().st_size!=2049*2049*2:raise RuntimeError('Heightmap byte count mismatch')
    import re
    for filename in ['track.hmf','track.tht']:
        text=(STAGE/filename).read_text()
        for key,path in re.findall(r'^\s*(map|mask|data)\s*=\s*([^\n\r]+)',text,re.M):
            if not (STAGE/path.strip()).is_file():raise RuntimeError(f'{filename}: missing {key} file {path}')
    print('All native input files staged and references resolved.',flush=True)
def main():
    if os.name!='nt':raise SystemExit('Run this script on Windows. Native compilation has not been performed on this machine.')
    stage();tools=ROOT/'BUILD/native_tools';tools.mkdir(parents=True,exist_ok=True)
    versions=json.loads((ROOT/'BUILD/tool_versions.json').read_text())
    for name,v in versions.items():
        path=tools/name
        if not path.is_file() or digest(path)!=v['sha256']:
            print('Downloading official PiBoSo',name,flush=True)
            with urllib.request.urlopen(v['url'],timeout=60) as response,path.open('wb') as f:shutil.copyfileobj(response,f)
        if digest(path)!=v['sha256']:raise RuntimeError(f'{name}: official download changed; review and update tool_versions.json before building.')
        with zipfile.ZipFile(path) as z:z.extractall(tools)
    edf=tools/'fbx2edf/fbx2edf_x64.exe';terrain=tools/'terrained/terrained.exe';tracked=tools/'tracked/tracked.exe'
    results={};results['edf']=run(edf,['scenery.fbx','scenery.edf','edf_params.ini','-q'],'fbx2edf',900);required(STAGE/'scenery.edf',1024);copy(STAGE/'scenery.edf',ROOT/'08_OBJECTS_GAME/scenery.edf')
    mappath=OUT/(NAME+'.map');trhpath=OUT/(NAME+'.trh')
    # Remove only the known outputs of this version so stale files cannot pass.
    for p in [mappath,trhpath,STAGE/'code.txt']:
        if p.exists():p.unlink()
    results['map']=run(terrain,['track.hmf',mappath,'map_params.ini'],'terrained_map',2400);required(mappath,100000,b'MP')
    results['trh']=run(terrain,['track.tht',trhpath,'trh_params.ini'],'terrained_trh',1200);required(trhpath,2049*2049*2,b'TRH')
    unmerged=digest(trhpath)
    results['centerline']=run(tracked,['-merge',trhpath,'cl',STAGE/'main.tcl','sa',STAGE/'start.tcl'],'tracked_merge',900)
    required(trhpath,2049*2049*2,b'TRH')
    if digest(trhpath)==unmerged:raise RuntimeError('TrackEd did not modify TRH. The centerline merge must succeed before packaging.')
    for suffix in ['.rdf','.ini','.amb','.tsc','.tga','_map.tga']:required(OUT/(NAME+suffix))
    for fn in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
        p=OUT/fn;required(p,100,b'TL \0');b=p.read_bytes();count=struct.unpack_from('<I',b,4)[0]
        if len(b)!=8+count*8:raise RuntimeError('Invalid reset boundary '+fn)
    required(OUT/'marshals.cfg')
    codes=list(STAGE.glob('code.txt'))+list(OUT.glob('code.txt'))
    if codes:copy(codes[0],LOG/'track_code.txt')
    native=dict(status='Compiled with official PiBoSo Windows tools',compiled=True,centerline_merged=True,results=results,outputs={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in OUT.iterdir() if p.is_file()},mapview_visual_check=False,in_game_riding_test=False,multiplayer_test=False,game_version_target='Current MX Bikes authoring workflow; shared start gate introduced in beta15')
    (LOG/'native_build_validation.json').write_text(json.dumps(native,indent=2)+'\n')
    destination=ROOT/'12_RELEASE/OrlandoMX_2026_v005.pkz';temporary=destination.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,NAME+'/'+p.name)
    with zipfile.ZipFile(temporary) as z:
        error=z.testzip()
        if error:raise RuntimeError('Archive CRC failure: '+error)
        if any(not n.startswith(NAME+'/') for n in z.namelist()):raise RuntimeError('Incorrect PKZ root folder')
    temporary.replace(destination)
    (destination.with_suffix('.pkz.sha256')).write_text(digest(destination)+'  '+destination.name+'\n')
    print('COMPLETED PKZ:',destination,'bytes:',destination.stat().st_size,'SHA256:',digest(destination),flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        LOG.mkdir(exist_ok=True);(LOG/'native_build_failure.txt').write_text(str(e)+'\n');raise

