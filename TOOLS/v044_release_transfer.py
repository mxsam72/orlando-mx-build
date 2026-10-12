"""Save reproducible source and verified native outputs to private GitHub assets."""
import urllib.request,urllib.parse,sys,zipfile,os
from v044_common import *
from v044_source import api,HEADERS,blob,API,download

def checkpoint():
    dest=R/'BUILD/OrlandoMX-v044-source-checkpoint.zip'
    folders=['V044_OUTPUT','V044_SOURCE','V043_OUTPUT','V043_SOURCE','V024_OUTPUT','V009_SOURCE','TOOLS','.github','BUILD_INPUTS','BUILD_V007','BUILD_V008','12_RELEASE/orlandomx_2026_v043','BUILD/v044_assets']
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in folders:
            for p in sorted((R/folder).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.map']:z.write(p,p.relative_to(R).as_posix())
        for name in ['track.tht','track.hmf','map_params.ini','trh_params.ini','edf_params.ini','tool_versions.json','native_coordinate_probes.json','v044_baseline_native_validation.json']:
            p=R/'BUILD'/name;z.write(p,p.relative_to(R).as_posix())
        z.write(R/'requirements-v009.txt','requirements-v009.txt')
    with zipfile.ZipFile(dest) as z:assert z.testzip() is None
    save(R/'BUILD/v044_checkpoint_descriptor.json',dict(file=dest.name,bytes=dest.stat().st_size,sha256=sha(dest)))
    print('Editable v044 checkpoint',dest.stat().st_size,'bytes',sha(dest),flush=True)

def restore():
    d=read(R/'BUILD/v044_checkpoint_descriptor.json');p=R/'BUILD'/d['file'];assert p.stat().st_size==d['bytes'] and sha(p)==d['sha256']
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        for i in z.infolist():
            assert not Path(i.filename).is_absolute() and '..' not in Path(i.filename).parts
            # Repository scripts remain the exact checkout, source/baseline payloads are restored.
            if not i.is_dir() and i.filename.startswith(('V044_OUTPUT/','V043_OUTPUT/','V024_OUTPUT/','12_RELEASE/orlandomx_2026_v043/','BUILD/v044_baseline_native_validation.json')):atomic(R/i.filename,z.read(i))
    assert read(O/'v044_source_validation.json')['checks_pass']
    print('Windows source restored from checksum-verified authoring checkpoint.',flush=True)


def resume_saved_source():
    """Restore the authenticated v044 checkpoint without regenerating visuals."""
    release=api('/releases/410990934')
    assert api('')['private'] and release['draft']
    assert release['target_commitish']=='b093ba4fa965202e5c88b6f315167e321c4960f7'
    assets={a['name']:a for a in release['assets']}
    source=assets['OrlandoMX-v044-source-checkpoint.zip']
    assert source['size']==1599713927 and source['digest']=='sha256:1c45844424b0f8e9384a9344f0563b6f108e5003f699c71430dc499166bff881'
    descriptor=assets['v044_checkpoint_descriptor.json']
    assert descriptor['digest']=='sha256:38b29297ea5bd495a3299419da1f44a7ebf381e28a76d2e95e5a6bf6b891ca83'
    download(descriptor,R/'BUILD/v044_checkpoint_descriptor.json')
    download(source,R/'BUILD/OrlandoMX-v044-source-checkpoint.zip')
    with zipfile.ZipFile(R/'BUILD/OrlandoMX-v044-source-checkpoint.zip') as z:
        # Authoring changes must not be silently bypassed by a source restore.
        for name in ['V044_SOURCE/visual_spec.json','TOOLS/build_v044.py','TOOLS/v044_assets.py','TOOLS/v044_scenery.py','TOOLS/v044_surface_detail.py']:
            assert z.read(name)==(R/name).read_bytes(),('Authored source changed; regenerate instead of resuming',name)
    restore()
    print('Saved v044 authoring source restored; native compilation uses the current checkout.',flush=True)

def save_native_checkpoint():
    """Preserve costly compiled outputs before extended validation can fail."""
    release=api('/releases/'+os.environ['V044_SOURCE_RELEASE_ID'])
    assert api('')['private'] and release['draft']
    assert release['target_commitish']==os.environ['GITHUB_SHA']
    qa=read(R/'DOCUMENTATION/native_build_validation.json')
    assert qa['compiled'] and qa['centerline_merged']
    path=R/'BUILD'/('v044-native-candidate-'+os.environ['GITHUB_RUN_ID']+'.zip')
    files=[R/'12_RELEASE/OrlandoMX_2026_v044.pkz',R/'12_RELEASE/OrlandoMX_2026_v044.pkz.sha256',R/'BUILD/v009_work/08_OBJECTS_GAME/scenery.edf',R/'V044_OUTPUT/v044_staging_validation.json',R/'DOCUMENTATION/native_build_validation.json']
    files += [p for p in (R/'DOCUMENTATION').glob('*.log') if p.name in ['fbx2edf.log','terrained_map.log','terrained_trh.log','tracked_merge.log']]
    assert all(p.is_file() for p in files)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in files:z.write(p,p.relative_to(R).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix=='.pkz' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    info=dict(file=path.name,bytes=path.stat().st_size,sha256=sha(path),source_commit=os.environ['GITHUB_SHA'],source_release_id=release['id'],extended_validation_pending=True)
    descriptor=R/'BUILD/v044_native_candidate_descriptor.json';save(descriptor,info)
    assert path.stat().st_size<2000000000,'Native checkpoint needs release splitting'
    upload(release,path);upload(release,descriptor)
    print('CODEX_V044_NATIVE_CANDIDATE_BLOB '+blob(json.dumps(info)),flush=True)

def save_diagnostics():
    """Keep failure evidence in the private source release without Actions quota."""
    release_id=os.environ.get('V044_SOURCE_RELEASE_ID')
    if not release_id:
        print('No source release was created; failure evidence remains in workflow logs.',flush=True);return
    release=api('/releases/'+release_id);assert api('')['private'] and release['draft']
    path=R/'BUILD'/('v044-native-diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    candidates=list((R/'DOCUMENTATION').glob('*.log'))+list((R/'DOCUMENTATION').glob('*failure*.txt'))
    candidates += [O/'v044_staging_validation.json',R/'BUILD/v044_stage/map_params.ini',R/'BUILD/v044_stage/edf_params.ini',R/'BUILD/v044_stage/trh_params.ini']
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in candidates:
            if p.is_file() and p.stat().st_size<50000000:z.write(p,p.relative_to(R).as_posix())
    upload(release,path)
    print('Native failure logs preserved privately.',flush=True)

def upload(release,p):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as data:
        req=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as r:a=json.load(r)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p)
    print('Verified private asset saved:',p.name,a['size'],flush=True);return a

def hold():
    assert api('')['private']
    commit=os.environ['GITHUB_SHA'];run=os.environ['GITHUB_RUN_ID']
    rel=api('/releases',dict(tag_name='v044-private-build-'+run,target_commitish=commit,name='Orlando MX v044 editable source — native compilation pending',draft=True,prerelease=False,make_latest='false',body='Authenticated dry-weather visual source passed independent preservation checks. Native playable PKZ compilation is pending. This private checkpoint preserves editable assets without GitHub Actions artifact storage.'))
    for p in [R/'BUILD/OrlandoMX-v044-source-checkpoint.zip',R/'BUILD/v044_checkpoint_descriptor.json']:upload(rel,p)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as env:env.write('V044_SOURCE_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V044_SOURCE_RELEASE_ID',rel['id'],flush=True)


def deliver():
    assert api('')['private'];qa=read(R/'12_RELEASE/OrlandoMX_v044_Validation.json');assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v043']
    commit=os.environ['GITHUB_SHA'];run=os.environ['GITHUB_RUN_ID'];assert qa['source_commit']==commit
    rel=api('/releases/'+os.environ['V044_SOURCE_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==commit
    payload=dict(name='Orlando MX v044 standard-weather realism',body='Standard-weather visual upgrade on the authenticated delivered v043. Continuous 8K route-following grooming/wheel-path diffuse and normal maps; photographic dirt, bark, timber and concrete; scan-derived near-view trees and botanical Bermuda grass; native alpha-tested foliage; improved clear daylight and higher-quality compiled shadows. Accepted MX heightfield, race inputs and complete native collision TRH remain byte-identical to v043. All signs, flag faces, personalized vehicles, seating and road-gap repairs preserved. No package size cap. Official Windows source/native/texture/archive validation passed. User in-game visual, riding and performance confirmation pending. Source commit '+commit+'.')
    req=urllib.request.Request(API+'/releases/'+str(rel['id']),data=json.dumps(payload).encode(),method='PATCH',headers=HEADERS|{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=150) as response:rel=json.load(response)
    paths=[R/'12_RELEASE'/n for n in ['OrlandoMX_2026_v044.pkz','OrlandoMX_2026_v044.pkz.sha256','OrlandoMX_v044_Validation.json','Install_v044.txt']]
    paths += [O/'v044_source_validation.json',O/'v044_surface_validation.json',O/'v044_scenery_validation.json',O/'v044_asset_provenance.json',R/'BUILD/v044_checkpoint_descriptor.json']
    cp=R/'BUILD/OrlandoMX-v044-source-checkpoint.zip'
    if cp.stat().st_size>=1900000000:
        with cp.open('rb') as stream:
            j=1
            while b:=stream.read(1900000000):p=cp.with_suffix('.zip.part'+str(j));atomic(p,b);paths.append(p);j+=1
    else:paths.append(cp)
    checks=R/'12_RELEASE/OrlandoMX_v044_SHA256SUMS.txt';atomic(checks,(''.join(sha(p)+'  '+p.name+'\n' for p in paths)).encode());paths.append(checks)
    existing={a['name']:a for a in api('/releases/'+str(rel['id']))['assets']}
    assets=[]
    for p in paths:
        if p.name in existing:
            a=existing[p.name];assert a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p);assets.append(a)
        else:assets.append(upload(rel,p))
    descriptor=dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=commit,build_run=int(run),pkz_bytes=qa['pkz_bytes'],pkz_sha256=qa['pkz_sha256'],assets=[dict(name=a['name'],id=a['id'],bytes=a['size'],digest=a['digest'],url=a['browser_download_url']) for a in assets])
    print('CODEX_V044_DELIVERY_BLOB '+blob(json.dumps(descriptor)),flush=True)
    assert api('/releases/'+str(rel['id']))['draft']
    print('Complete playable v044 PKZ and editable checkpoint saved privately.',flush=True)
if __name__=='__main__':{'checkpoint':checkpoint,'restore':restore,'hold':hold,'resume':resume_saved_source,'diagnostics':save_diagnostics,'deliver':deliver}[sys.argv[1]]()
