"""Authenticated baseline, exact accepted v045 dirt, and durable v046 checkpoints."""
import io, json, os, shutil, sys, urllib.parse, urllib.request, zipfile
from pathlib import Path
from v046_surface import R,BASE,O,sha,save_json

REPOSITORY='mxsam72/orlando-mx-build';API='https://api.github.com/repos/'+REPOSITORY
HEADERS={'Authorization':'Bearer '+os.environ.get('V046_RELEASE_TOKEN',''),'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v046-build'}
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
    save_json(R/'BUILD/v046_baseline_validation.json',qa)
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
        for name,target in [('BUILD/v009_work/08_OBJECTS_GAME/scenery.edf',R/'BUILD/v046_stage/scenery.edf'),('12_RELEASE/OrlandoMX_2026_v044.pkz',R/'BUILD/v046_baseline.pkz')]:
            extract(z,z.getinfo(name),target)
    assert sha(R/'BUILD/v046_stage/scenery.edf')==qa['object_texture_validation']['edf_sha256']
    assert sha(R/'BUILD/v046_baseline.pkz')==qa['pkz_sha256']=='899fb2e574fc1e0063dc001f6e2be96076b82e7d793a929f28b42fe42d3f59b0'
    with zipfile.ZipFile(R/'BUILD/v046_baseline.pkz') as z:
        assert len(z.infolist())==13
        for i in z.infolist():
            safe_name(i.filename);assert i.filename.startswith('orlandomx_2026_v044/')
            if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,R/'BUILD/v046_baseline_game'/Path(i.filename).name)
    assert sha(BASE/'terrain.raw')==qa['source_validation']['terrain_sha256']
    for p in paths.values():p.unlink()
    accepted=api('/releases/411270095')
    assert not accepted['draft'] and accepted['tag_name']=='untagged-7321ac758a26e6678cac'
    asset=next(a for a in accepted['assets'] if a['name']=='OrlandoMX-v045-dirt-source-checkpoint.zip')
    EXPECTED[asset['name']]=(362743168,'5028cc4c05034404f52bd02e95ffa4097ad6933bf3c5496957270159416e4611')
    saved=R/'BUILD/accepted-v045-dirt-source.zip';download(asset,saved)
    with zipfile.ZipFile(saved) as z:
        for i in z.infolist():
            safe_name(i.filename)
            if not i.is_dir() and i.filename.startswith('V045_OUTPUT/'):extract(z,i,R/i.filename)
    saved.unlink()
    print('Published physical baseline and accepted v045 dirt authenticated.',flush=True)

def upload(release,p):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as r:a=json.load(r)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p)
    print('Saved release asset',p.name,p.stat().st_size,flush=True)
    return a

def checkpoint():
    identity();qa=json.loads((O/'v046_surface_validation.json').read_text());assert qa['checks_pass'] and qa['full_route'] and qa['accepted_v045_materials_identical']
    p=R/'BUILD/OrlandoMX-v046-dirt-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V046_OUTPUT','V046_SOURCE']:
            for f in sorted((R/folder).rglob('*')):
                if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in sorted((R/'TOOLS').glob('*v046*.py')):z.write(f,f.relative_to(R).as_posix())
        z.write(R/'BUILD/v046_baseline_validation.json','BUILD/v046_baseline_validation.json')
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    desc=dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),baseline_release_id=411058375,baseline_assets={n:dict(bytes=size,sha256=d) for n,(size,d) in EXPECTED.items()})
    descriptor=R/'BUILD/v046_checkpoint_descriptor.json';save_json(descriptor,desc)
    rel=api('/releases',dict(tag_name='v046-persistent-dirt-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX v046 whole-track persistent dirt — compilation pending',draft=True,prerelease=True,make_latest='false',body='Accepted v045 photographic dirt across the entire riding circuit. Corrected visual deformation depths; retained physical terrain, native scenery, race data and lighting. Native terrain compilation pending.'))
    for f in [p,descriptor]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as e:e.write('V046_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V046_RELEASE_ID',rel['id'],flush=True)

def preserve_native():
    rel=api('/releases/'+os.environ['V046_RELEASE_ID']);assert rel['draft']
    for name in ['OrlandoMX_2026_v046.pkz','OrlandoMX_2026_v046.pkz.sha256']:
        upload(rel,R/'12_RELEASE'/name)

def deliver():
    identity();qa=json.loads((R/'12_RELEASE/OrlandoMX_v046_Validation.json').read_text())
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v044'] and qa['native_scenery_identical_to_v044']
    assert qa['surface_validation']['full_route'] and qa['surface_validation']['accepted_v045_materials_identical']
    assert qa['surface_validation']['visual_layer_depths_m']=={'11':4.0,'12':4.0,'13':4.0}
    rel=api('/releases/'+os.environ['V046_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==os.environ['GITHUB_SHA']
    for p in [R/'12_RELEASE/OrlandoMX_v046_Validation.json',R/'12_RELEASE/Install_v046.txt',O/'v046_surface_validation.json',O/'v046_asset_provenance.json',R/'BUILD/v046_scope_preview.png',R/'BUILD/v046_soil_material_preview.jpg']:
        if p.exists():upload(rel,p)
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v046 — persistent dirt across the whole track',draft=False,prerelease=True,make_latest='false',body='The same accepted v045 4K photographic loose and packed dirt and matched normal maps now cover the entire riding circuit, including the pre-finish rollers, finish tabletop, triple and table-single. Fixed missing visual layer thickness: all three added HMF layers now have explicit 4 m cosmetic depths so deformation does not immediately reveal old dirt. Riding physics and rut deformation remain enabled and unchanged. Delivered collision TRH, race files, scenery EDF, lighting, signs, vehicles and vegetation are retained. Official native terrain compilation plus source, bitmap, coordinate, collision and archive checks passed. Ridden persistence and performance confirmation remain pending user testing. Reset the track before comparing and ride several laps with your usual deformation setting.'),method='PATCH')
    assets=api('/releases/'+str(rel['id']))['assets'];save_json(R/'BUILD/v046_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=os.environ['GITHUB_SHA'],pkz_sha256=qa['pkz_sha256'],pkz_bytes=qa['pkz_bytes'],assets=[dict(name=a['name'],url=a['browser_download_url'],size=a['size'],digest=a['digest']) for a in assets]))
    print('V046_DOWNLOAD',next(a['browser_download_url'] for a in assets if a['name']=='OrlandoMX_2026_v046.pkz'),flush=True)

def diagnostics():
    rid=os.environ.get('V046_RELEASE_ID')
    if not rid:return
    rel=api('/releases/'+rid);assert rel['draft']
    p=R/'BUILD'/('v046_failure_diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in list((R/'DOCUMENTATION').glob('*v046*'))+list(O.glob('*.json')):
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(rel,p)

if __name__=='__main__':{'restore':restore,'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
