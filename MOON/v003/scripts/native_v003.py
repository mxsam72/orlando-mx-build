"""Checkpointed v003 source, native conversions, validation and canonical PKZ."""
from pathlib import Path,PurePosixPath
import argparse,configparser,hashlib,json,mmap,os,re,shutil,struct,sys,zipfile
import numpy as np
from PIL import Image
V=Path(__file__).resolve().parents[1];R=V.parents[1];B=V/'build';G=B/'game';P=V/'previews'
NAME='taurus_littrow_mx_v003';INPUT=R/'Moon_v003_Native_Inputs.zip'
sys.path.insert(0,str(R/'MOON/scripts'))
import native_test as n
n.M=V;n.B=B;n.G=G;n.NAME=NAME;n.LOG=V/'native_logs';n.LOG.mkdir(exist_ok=True)
ASSETS={'sky':[G/'moon_v003_sky.edf'],'scenery':[B/'scenery.edf'],'collision':[G/(NAME+'.trh')]}
PACKAGE=[V/(NAME+'.pkz'),V/(NAME+'.pkz.sha256'),V/'Moon_v003_Validation.json',V/'Moon_v003_Previews.zip',V/'Install_Moon_v003.txt']
TEXTURES=['v003_terrain_color.tga','v002_regolith.tga','v002_regolith_n.tga','v002_route.tga','v002_route_n.tga','v002_fine.tga','v002_fine_n.tga','v003_shadow_tile.tga']

def relative(path):return path.relative_to(R).as_posix()
def safe_name(name,prefixes):
    p=PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name and name.startswith(prefixes)
def context():
    digest=os.environ.get('SOURCE_INPUT_SHA256')
    assert digest and re.fullmatch('[0-9a-f]{64}',digest),'Missing source archive SHA256'
    return dict(schema=1,source_archive_sha256=digest,source_commit=os.environ.get('GITHUB_SHA','local'),run_id=os.environ.get('GITHUB_RUN_ID','local'))
def file_manifest(paths):
    return {relative(p):dict(bytes=p.stat().st_size,sha256=n.sha(p)) for p in sorted(paths)}
def verify_archive(z,manifest,prefixes):
    names=z.namelist();assert len(names)==len(set(names)),'Duplicate ZIP members'
    assert z.testzip() is None,'Archive CRC failure'
    assert set(names)==set(manifest['files'])|{'manifest.json'},'Unexpected archive members'
    for name,expected in manifest['files'].items():
        assert safe_name(name,prefixes),('Unsafe archive path',name)
        data=z.read(name)
        assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],('Archive content mismatch',name)
def extract(z,manifest):
    for name in manifest['files']:
        path=R/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
def checkpoint(stage,paths,details):
    folder=V/'checkpoints';folder.mkdir(exist_ok=True)
    manifest=context()|dict(stage=stage,files=file_manifest(paths),details=details)
    path=folder/(stage+'.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
        for p in paths:z.write(p,relative(p))
    n.save(folder/(stage+'_manifest.json'),manifest)
    print('V003_CHECKPOINT_SAVED',stage,path.stat().st_size,n.sha(path),flush=True)
def restore(stage,paths):
    path=V/'checkpoint_downloads'/(stage+'.zip')
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert all(manifest[k]==v for k,v in context().items()),'Checkpoint provenance mismatch'
        assert manifest['stage']==stage and manifest['details']['checks_pass'] is True
        assert set(manifest['files'])==set(map(relative,paths)),'Unexpected checkpoint file set'
        verify_archive(z,manifest,('MOON/v003/',));extract(z,manifest)
    return manifest['details']
def preflight():
    source=json.loads((B/'source_validation.json').read_text());scene=json.loads((B/'scenery_validation.json').read_text());sky=json.loads((B/'sky_validation.json').read_text())
    assert all(x['checks_pass'] for x in [source,scene,sky])
    assert source['half_gravity_m_s2']==4.905 and source['legacy_rollers_removed'] and source['source_baked_terrain_shadow_mask']
    assert len(source['features'])==6 and source['optional_transfer']['gap']==220
    assert n.sha(B/'terrain.raw')==source['source_raw_sha256'] and (B/'terrain.raw').stat().st_size==2049**2*2
    assert n.sha(B/'scenery.fbx')==scene['native_fbx_sha256'] and scene['triangles']<150000
    assert n.sha(B/'moon_v003_sky.fbx')==sky['native_fbx_sha256']
    cfg=configparser.ConfigParser();cfg.read(B/'map_params.ini');params=cfg['params']
    assert all(params.getint(k)==0 for k in ['shadowmaps_create','shadowvolumes_create','shadowmaps_terraincast'])
    amb=(G/(NAME+'.amb')).read_text();assert amb.count('sky = moon_v003_sky.edf')==3 and amb.count('density = 0')==3 and '*' not in amb
    for axis in ['x','y','z']:
        runtime=float(re.search(r'\b'+axis+r'\s*=\s*([-\d.]+)',amb)[1]);assert runtime==float(params['lightdir_'+axis])
    for path in list(B.glob('*.hmf'))+list(B.glob('*.tht'))+list(B.glob('*.shd')):
        for ref in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',path.read_text()):
            assert Path(ref).name==ref and (B/ref).is_file(),(path.name,ref)
    for path in B.glob('*.tga'):
        w,h,_=n.bitmap_signature(path);assert w&(w-1)==0 and h&(h-1)==0,(path,w,h)
    for name in ['scenery','moon_v003_sky']:
        dest=B/(name+'.fbm');dest.mkdir(exist_ok=True)
        for pattern in ['*.tga','*.shd','*.flg']:
            for file in B.glob(pattern):shutil.copy2(file,dest/file.name)
    return source,scene,sky
def source_bundle():
    for file,render in [(NAME+'.tga','01_crater_arena.png'),(NAME+'_map.tga','05_layout.png')]:
        with Image.open(P/render) as im:im.convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS).save(G/file)
    preflight()
    # Only root source inputs and game/preview files; .fbm staging duplicates are regenerated.
    paths=[p for folder in [B,G,P] for p in folder.iterdir() if p.is_file()]
    manifest=dict(schema=1,source_commit=os.environ.get('GITHUB_SHA','local'),run_id=os.environ.get('GITHUB_RUN_ID','local'),files=file_manifest(paths))
    with zipfile.ZipFile(INPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
        for p in paths:z.write(p,relative(p))
    with zipfile.ZipFile(INPUT) as z:verify_archive(z,manifest,('MOON/v003/build/','MOON/v003/previews/'))
    digest=n.sha(INPUT);n.save(INPUT.with_suffix('.json'),dict(sha256=digest,bytes=INPUT.stat().st_size,source_commit=manifest['source_commit'],run_id=manifest['run_id']))
    INPUT.with_suffix('.zip.sha256').write_text(digest+'  '+INPUT.name+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('input_sha256='+digest+'\n')
    print('V003_SOURCE_ARCHIVE_PASS',digest,INPUT.stat().st_size,flush=True)
def unpack():
    expected=context();assert n.sha(INPUT)==expected['source_archive_sha256'],'Source archive hash mismatch'
    with zipfile.ZipFile(INPUT) as z:
        manifest=json.loads(z.read('manifest.json'));assert manifest['source_commit']==expected['source_commit'] and manifest['run_id']==expected['run_id']
        verify_archive(z,manifest,('MOON/v003/build/','MOON/v003/previews/'));extract(z,manifest)
    preflight();print('V003_SOURCE_RESTORED',flush=True)
def collision_check(path):
    expected=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049)
    with path.open('rb') as f:assert f.read(4)==b'TRH\0' and struct.unpack('<2I',f.read(8))==(2049,2049)
    encoded=np.memmap(path,mode='r',dtype='<u2',offset=12,shape=(2049,2049))
    got=((encoded.astype(np.uint32)-32768)&65535).astype('<u2')[::-1];assert np.array_equal(got,expected)
    return dict(checks_pass=True,samples=int(expected.size))
def texture_check(path,names):
    records=[]
    with path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        for name in names:
            w,h,digest=n.bitmap_signature(B/name);pos=data.find(struct.pack('<2I',w,h)+digest)
            assert pos>=0,('Native bitmap missing',name)
            records.append(dict(file=name,width=w,height=h,pixel_md5=digest.hex(),native_offset=pos))
    return records
def asset(stage):
    assert os.name=='nt','Official converters require Windows'
    source,scene,sky=preflight();edf,terrain,tracked=n.tools();paths=ASSETS[stage]
    for p in paths:p.unlink(missing_ok=True)
    details=dict(checks_pass=False)
    try:
        if stage=='sky':details['compiler']=n.run(edf,['moon_v003_sky.fbx',paths[0],'edf_params.ini','-q'],'v003_sky',300)
        elif stage=='scenery':details['compiler']=n.run(edf,['scenery.fbx',paths[0],'edf_params.ini','-q'],'v003_scenery',1800)
        else:
            details['compiler']=n.run(terrain,['track.tht',paths[0],'trh_params.ini'],'v003_collision',300)
            before=n.sha(paths[0]);details['centerline']=n.run(tracked,['-merge',paths[0],'cl',B/'main.tcl'],'v003_centerline',300)
            assert n.sha(paths[0])!=before,'Centerline merge did not alter TRH';details['centerline_merged']=True
    finally:
        existing=[p for p in paths if p.is_file()]
        if existing:checkpoint(stage+'-raw',existing,details)
    if stage in ['sky','scenery']:
        with paths[0].open('rb') as f:assert f.read(4)==b'EDF\0'
    if stage=='sky':details['textures']=texture_check(paths[0],[sky['stars_texture'],sky['earth_texture']])
    elif stage=='scenery':
        with paths[0].open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
            errors=n.scan_points(data,scene['native_probe_local_xyz_m'],tolerance=.001)
        assert len(errors)>=20 and all(e is not None for e in errors),('Native scenery placement mismatch',errors)
        details['native_coordinate_probes']=len(errors)
    else:details['collision_grid']=collision_check(paths[0])
    details['checks_pass']=True;checkpoint(stage,paths,details)
def package_identity(filename,names):
    assert filename==NAME+'.pkz','PKZ filename must exactly match internal track directory'
    assert names and all(safe_name(name,(NAME+'/')) for name in names),'Unexpected PKZ root'
    required=[NAME+s for s in ['.map','.trh','.rdf','.ini','.amb','.tga','_map.tga']]+['moon_v003_sky.edf','gfx.cfg','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']
    assert set(names)=={NAME+'/'+name for name in required},'Missing or unexpected game files'
def package(source,scene,details):
    trh=G/(NAME+'.trh');mp=G/(NAME+'.map');height=n.validate_heights(mp,trh)
    with mp.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        errors=n.scan_points(data,[[p[0]+800,p[1],p[2]+800] for p in scene['native_probe_local_xyz_m']],tolerance=.001)
    assert len(errors)>=20 and all(e is not None for e in errors),('MAP coordinate mismatch',errors)
    bitmaps=texture_check(mp,TEXTURES)
    for p in G.glob('*.tl'):
        data=p.read_bytes();assert data[:4]==b'TL \0';count=struct.unpack_from('<I',data,4)[0]
        assert len(data)==8+count*8 and np.isfinite(np.frombuffer(data[8:],'<f4')).all()
    required=[NAME+s for s in ['.map','.trh','.rdf','.ini','.amb','.tga','_map.tga']]+['moon_v003_sky.edf','gfx.cfg','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']
    pkz=V/(NAME+'.pkz')
    with zipfile.ZipFile(pkz,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(required):z.write(G/name,NAME+'/'+name)
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None;package_identity(pkz.name,z.namelist())
    assert pkz.stat().st_size<500_000_000,'Test package exceeds 500 MB target'
    pkz.with_suffix('.pkz.sha256').write_text(n.sha(pkz)+'  '+pkz.name+'\n')
    with zipfile.ZipFile(V/'Moon_v003_Previews.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(P.iterdir()):
            if p.is_file():z.write(p,p.name)
    shutil.copy2(V/'INSTALL.txt',V/'Install_Moon_v003.txt')
    report=context()|dict(version='moon-v003',compiled=True,checks_pass=True,native_height_validation=height,
        native_coordinate_probe_count=len(errors),native_material_signatures=bitmaps,native_compilers=details,
        source_validation=source,pkz_sha256=n.sha(pkz),pkz_bytes=pkz.stat().st_size,canonical_pkz_name=pkz.name,
        source_baked_terrain_shadows=True,native_shadowmaps=False,centerline_merged=details['collision']['centerline_merged'],
        in_game_load_test=False,in_game_riding_test=False,in_game_visual_check=False,multiplayer_supported=False,
        pending=['Load in Testing with the separately installed compatible Quiet Gravity plugin, preset=half.',
                 'Ride each crater at the suggested lip speed, check landings, bike pitch, grip and FPS.',
                 'Check Earth/stars, reset positions, pit entry, finish and lap timing in game.'])
    n.save(V/'Moon_v003_Validation.json',report);checkpoint('package',PACKAGE,dict(checks_pass=True,pkz_sha256=n.sha(pkz)))
    print('V003_NATIVE_PACKAGE_PASS',pkz.stat().st_size,n.sha(pkz),flush=True)
def graphics():
    assert os.name=='nt','Official converters require Windows'
    details={stage:restore(stage,paths) for stage,paths in ASSETS.items()}
    source,scene,_=preflight();_,terrain,_=n.tools();mp=G/(NAME+'.map');mp.unlink(missing_ok=True)
    try:details['graphics']=n.run(terrain,['track.hmf',mp,'map_params.ini'],'v003_graphics',900)
    finally:
        if mp.is_file():checkpoint('graphics-raw',[mp],dict(checks_pass=False,details=details))
    package(source,scene,details)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['source','unpack','preflight','sky','scenery','collision','graphics','publish-restore'])
    stage=parser.parse_args().stage
    if stage=='source':source_bundle()
    elif stage=='unpack':unpack()
    elif stage=='preflight':preflight();print('V003_PREFLIGHT_PASS',flush=True)
    elif stage in ASSETS:asset(stage)
    elif stage=='graphics':graphics()
    else:restore('package',PACKAGE)
if __name__=='__main__':main()
