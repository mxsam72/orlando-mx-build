"""Save reproducible source and verified native outputs to private GitHub assets."""
import urllib.request,urllib.parse,sys,zipfile,os
from v044_common import *
from v044_source import api,HEADERS,blob

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

def upload(release,p):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as data:
        req=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as r:a=json.load(r)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p)
    print('Verified private asset saved:',p.name,a['size'],flush=True);return a

def deliver():
    assert api('')['private'];qa=read(R/'12_RELEASE/OrlandoMX_v044_Validation.json');assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v043']
    commit=os.environ['GITHUB_SHA'];run=os.environ['GITHUB_RUN_ID'];assert qa['source_commit']==commit
    rel=api('/releases',dict(tag_name='v044-private-build-'+run,target_commitish=commit,name='Orlando MX v044 standard-weather realism',draft=True,prerelease=False,make_latest='false',body='Standard-weather visual upgrade on the authenticated delivered v043. Continuous 8K route-following grooming/wheel-path diffuse and normal maps; photographic dirt, bark, timber and concrete; scan-derived near-view trees and botanical Bermuda grass; native alpha-tested foliage; improved clear daylight and higher-quality compiled shadows. Accepted MX heightfield, race inputs and complete native collision TRH remain byte-identical to v043. All signs, flag faces, personalized vehicles, seating and road-gap repairs preserved. No package size cap. Official Windows source/native/texture/archive validation passed. User in-game visual, riding and performance confirmation pending. Source commit '+commit+'.'))
    paths=[R/'12_RELEASE'/n for n in ['OrlandoMX_2026_v044.pkz','OrlandoMX_2026_v044.pkz.sha256','OrlandoMX_v044_Validation.json','Install_v044.txt']]
    paths += [O/'v044_source_validation.json',O/'v044_surface_validation.json',O/'v044_scenery_validation.json',O/'v044_asset_provenance.json',R/'BUILD/v044_checkpoint_descriptor.json']
    cp=R/'BUILD/OrlandoMX-v044-source-checkpoint.zip'
    if cp.stat().st_size>=1900000000:
        with cp.open('rb') as stream:
            j=1
            while b:=stream.read(1900000000):p=cp.with_suffix('.zip.part'+str(j));atomic(p,b);paths.append(p);j+=1
    else:paths.append(cp)
    checks=R/'12_RELEASE/OrlandoMX_v044_SHA256SUMS.txt';atomic(checks,(''.join(sha(p)+'  '+p.name+'\n' for p in paths)).encode());paths.append(checks)
    assets=[upload(rel,p) for p in paths]
    descriptor=dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=commit,build_run=int(run),pkz_bytes=qa['pkz_bytes'],pkz_sha256=qa['pkz_sha256'],assets=[dict(name=a['name'],id=a['id'],bytes=a['size'],digest=a['digest'],url=a['browser_download_url']) for a in assets])
    print('CODEX_V044_DELIVERY_BLOB '+blob(json.dumps(descriptor)),flush=True)
    assert api('/releases/'+str(rel['id']))['draft']
    print('Complete playable v044 PKZ and editable checkpoint saved privately.',flush=True)
if __name__=='__main__':{'checkpoint':checkpoint,'restore':restore,'deliver':deliver}[sys.argv[1]]()
