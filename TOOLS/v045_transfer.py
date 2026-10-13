"""Authenticated public v044 baseline and durable v045 release checkpoints."""
import io, json, os, shutil, sys, urllib.parse, urllib.request, zipfile
from pathlib import Path
from v045_surface import R,BASE,O,sha,save_json

REPOSITORY='mxsam72/orlando-mx-build';API='https://api.github.com/repos/'+REPOSITORY
HEADERS={'Authorization':'Bearer '+os.environ.get('V045_RELEASE_TOKEN',''),'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v045-build'}
EXPECTED={
 'OrlandoMX-v044-source-checkpoint.zip':(1599713927,'1c45844424b0f8e9384a9344f0563b6f108e5003f699c71430dc499166bff881'),
 'v044-native-candidate-38319134828.zip':(843801281,'d67e66e3f233a8148dffa3ba1ca25ef08f05c4f535de3529bda9c700c527d37b'),
 'OrlandoMX_v044_Validation.json':(322165,'31f7aea94045e71752a6fbabee70724db83eafd6c53a51951b619ca2a1cf2714')}

def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers=HEADERS|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)

def identity():
    j=api('');assert j['id']==1368050549 and j['full_name']==REPOSITORY
    assert j['visibility']=='public' and not j['private']

def download(a,p):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    size,digest=EXPECTED[a['name']];assert a['size']==size and a['digest']=='sha256:'+digest
    if p.is_file() and p.stat().st_size==size and sha(p)==digest:return
    # Published, anonymous URLs avoid exporting credentials to asset hosts.
    with urllib.request.urlopen(a['browser_download_url'],timeout=300) as r,p.open('wb') as out:
        shutil.copyfileobj(r,out,4*1024*1024)
    assert p.stat().st_size==size and sha(p)==digest
    print('Authenticated baseline asset',a['name'],size,flush=True)

def safe_name(name):
    p=Path(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    return p

def extract(z,i,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(i) as src,p.open('wb') as out:shutil.copyfileobj(src,out,4*1024*1024)

def restore():
    identity();release=api('/releases/411058375')
    assert not release['draft'] and release['tag_name']=='untagged-281f90b2ce09d3a57800'
    assets={a['name']:a for a in release['assets']}
    paths={}
    for name in EXPECTED:
        p=R/'BUILD'/('baseline_'+name);download(assets[name],p);paths[name]=p
    qa=json.loads(paths['OrlandoMX_v044_Validation.json'].read_text())
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v043']
    save_json(R/'BUILD/v045_baseline_validation.json',qa)
    with zipfile.ZipFile(paths['OrlandoMX-v044-source-checkpoint.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            keep=i.filename.startswith(('V044_OUTPUT/materials/','V044_OUTPUT/masks/'))
            keep|=i.filename in ['V044_OUTPUT/terrain.raw','V044_OUTPUT/route.npz','V044_OUTPUT/compiled_track.hmf','V044_OUTPUT/geometry_spec.json','V044_OUTPUT/v024_pit_gravel.tga','BUILD/tool_versions.json','BUILD/map_params.ini']
            if keep and not i.is_dir():extract(z,i,R/i.filename)
        # The legacy grass normal is inherited from the nested original inputs,
        # not duplicated in V044_OUTPUT/materials. Restore its exact bytes.
        parts=sorted(n for n in z.namelist() if n.startswith('BUILD_INPUTS/native_inputs.zip.part'))
        with zipfile.ZipFile(io.BytesIO(b''.join(z.read(n) for n in parts))) as inner:
            extract(inner,inner.getinfo('05_NORMALS/grass_n.tga'),BASE/'grass_n.tga')
            extract(inner,inner.getinfo('04_TEXTURES/basemap.tga'),BASE/'basemap.tga')
        assert sha(BASE/'grass_n.tga')=='4de81532bf419efdc60fee0ca3f377b89168371f6bf858ab4f2e7a773a6cf881'
        assert sha(BASE/'basemap.tga')=='75fc72427f37e57c711c9d73c002d7bdba10e8501ae25e9c0a60c79e08fdc5b1'
    with zipfile.ZipFile(paths['v044-native-candidate-38319134828.zip']) as z:
        for name,target in [('BUILD/v009_work/08_OBJECTS_GAME/scenery.edf',R/'BUILD/v045_stage/scenery.edf'),('12_RELEASE/OrlandoMX_2026_v044.pkz',R/'BUILD/v045_baseline.pkz')]:
            extract(z,z.getinfo(name),target)
    assert sha(R/'BUILD/v045_stage/scenery.edf')==qa['object_texture_validation']['edf_sha256']
    assert sha(R/'BUILD/v045_baseline.pkz')==qa['pkz_sha256']=='899fb2e574fc1e0063dc001f6e2be96076b82e7d793a929f28b42fe42d3f59b0'
    with zipfile.ZipFile(R/'BUILD/v045_baseline.pkz') as z:
        assert len(z.infolist())==13
        for i in z.infolist():
            safe_name(i.filename);assert i.filename.startswith('orlandomx_2026_v044/')
            if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,R/'BUILD/v045_baseline_game'/Path(i.filename).name)
    assert sha(BASE/'terrain.raw')==qa['source_validation']['terrain_sha256']
    for p in paths.values():p.unlink()
    print('Published v044 source, native scenery, collision and race files authenticated.',flush=True)

def upload(release,p):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as r:a=json.load(r)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p)
    print('Saved release asset',p.name,p.stat().st_size,flush=True)
    return a

def checkpoint():
    identity();qa=json.loads((O/'v045_surface_validation.json').read_text());assert qa['checks_pass']
    p=R/'BUILD/OrlandoMX-v045-dirt-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V045_OUTPUT','V045_SOURCE','BUILD/v045_assets']:
            for f in sorted((R/folder).rglob('*')):
                if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in sorted((R/'TOOLS').glob('*v045*.py')):z.write(f,f.relative_to(R).as_posix())
        z.write(R/'BUILD/v045_baseline_validation.json','BUILD/v045_baseline_validation.json')
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    desc=dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),baseline_release_id=411058375,baseline_assets={n:dict(bytes=size,sha256=d) for n,(size,d) in EXPECTED.items()})
    descriptor=R/'BUILD/v045_checkpoint_descriptor.json';save_json(descriptor,desc)
    rel=api('/releases',dict(tag_name='v045-finish-dirt-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX v045 finish dirt sample — compilation pending',draft=True,prerelease=True,make_latest='false',body='Dirt-only R01 finish tabletop through R02 triple sample. Authenticated v044 physical track and scenery retained. Native terrain compilation pending.'))
    for f in [p,descriptor]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as e:e.write('V045_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V045_RELEASE_ID',rel['id'],flush=True)

def preserve_native():
    rel=api('/releases/'+os.environ['V045_RELEASE_ID']);assert rel['draft']
    for name in ['OrlandoMX_2026_v045.pkz','OrlandoMX_2026_v045.pkz.sha256']:
        upload(rel,R/'12_RELEASE'/name)

def deliver():
    identity();qa=json.loads((R/'12_RELEASE/OrlandoMX_v045_Validation.json').read_text())
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v044'] and qa['native_scenery_identical_to_v044']
    rel=api('/releases/'+os.environ['V045_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==os.environ['GITHUB_SHA']
    for p in [R/'12_RELEASE/OrlandoMX_v045_Validation.json',R/'12_RELEASE/Install_v045.txt',O/'v045_surface_validation.json',O/'v045_asset_provenance.json',R/'BUILD/v045_scope_preview.png',R/'BUILD/v045_soil_material_preview.jpg']:
        if p.exists():upload(rel,p)
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v045 — finish tabletop and triple dirt sample',draft=False,prerelease=True,make_latest='false',body='Dirt-only comparison sample: finish-line tabletop R01, connecting turn, R02 triple and landing run-out. New dominant 4K photographic clod and packed-soil materials with matched normals at 2 m tile scale; route-following wheel grooves, grooming and shoulder wear. New layers are last in the stack and masks are zero outside the sample. Collision TRH, race files, scenery EDF, lighting, signs, vehicles and vegetation are retained from delivered v044. Official native terrain compilation and bitmap/coordinate/source/archive checks passed. Actual in-game appearance and performance require the user riding comparison. Install the PKZ alongside v044 and select v045 in clear/dry weather.'),method='PATCH')
    assets=api('/releases/'+str(rel['id']))['assets'];save_json(R/'BUILD/v045_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=os.environ['GITHUB_SHA'],pkz_sha256=qa['pkz_sha256'],pkz_bytes=qa['pkz_bytes'],assets=[dict(name=a['name'],url=a['browser_download_url'],size=a['size'],digest=a['digest']) for a in assets]))
    print('V045_DOWNLOAD',next(a['browser_download_url'] for a in assets if a['name']=='OrlandoMX_2026_v045.pkz'),flush=True)

def diagnostics():
    rid=os.environ.get('V045_RELEASE_ID')
    if not rid:return
    rel=api('/releases/'+rid);assert rel['draft']
    p=R/'BUILD/v045_failure_diagnostics.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in list((R/'DOCUMENTATION').glob('*v045*'))+list(O.glob('*.json')):
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(rel,p)

if __name__=='__main__':{'restore':restore,'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
