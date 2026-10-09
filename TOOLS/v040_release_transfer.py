"""Restore immutable v039 and preserve verified v040 as an unpublished draft."""
import hashlib,json,os,sys,urllib.request,urllib.parse,urllib.error,zipfile
from pathlib import Path
from v040_common import *
API='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
TOKEN=os.environ['V040_RELEASE_TOKEN']
HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v040-private-delivery'}

def api(path,data=None):
    payload=None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(API+path,data=payload,headers=HEADERS|({'Content-Type':'application/json'} if payload else {})),timeout=150) as response:return json.load(response)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def record(asset):
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
        raise RuntimeError('Expected private file redirect')
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        location=e.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
    return dict(name=asset['name'],asset_id=asset['id'],bytes=asset['size'],digest=asset['digest'],download_url=location)

def download(asset,path):
    r=record(asset);path.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();count=0
    with urllib.request.urlopen(r['download_url'],timeout=180) as response,path.open('wb') as output:
        while b:=response.read(4*1024*1024):output.write(b);h.update(b);count+=len(b)
    assert count==r['bytes'] and h.hexdigest()==r['digest'].removeprefix('sha256:')

def source():
    assert api('')['private'];cfg=read(S/'update.json');release=api('/releases/'+str(cfg['baseline_release_id']));assert release['draft']
    found={a['name']:a for a in release['assets']}
    asset=found['OrlandoMX-v039-source-checkpoint.zip']
    assert asset['size']==cfg['baseline_checkpoint_bytes'] and asset['digest']=='sha256:'+cfg['baseline_checkpoint_sha256']
    path=R/'BUILD/v040-v039-baseline.zip';download(asset,path)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for info in z.infolist():
            name=info.filename
            if info.is_dir():continue
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            if name.startswith(('V039_OUTPUT/','V039_SOURCE/','V024_OUTPUT/')) or (name.startswith('12_RELEASE/orlandomx_2026_v039/') and not name.endswith('.map')):atomic(R/name,z.read(info))
    path.unlink()
    a=found['OrlandoMX_v039_Validation.json'];assert a['digest']=='sha256:659e6a6b8d44a20509ce1e932665b01c7ea8ce325f72538fbd77c73dc97b6acb'
    p=R/'BUILD/v040_baseline_native_validation.json';download(a,p);qa=read(p)
    assert qa['compiled'] and qa['centerline_merged'] and qa['source_checks']
    assert qa['pkz_bytes']==423041686 and qa['pkz_sha256']=='dc09a98cfa76785a10a95ea4cc5ae5d6d4e53dcc02a6023db5ecc42246336d1a'
    assert sha(BASE/'scenery.fbx')==cfg['baseline_scenery_sha256'] and sha(BASE/'terrain.raw')==cfg['baseline_terrain_sha256']
    print('Pinned v039 source and actual native validation restored and authenticated before editing.',flush=True)

def upload(release,path):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':path.name})
    with path.open('rb') as data:
        req=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as response:asset=json.load(response)
    assert asset['state']=='uploaded' and asset['size']==path.stat().st_size
    print('Private verified file saved:',path.name,asset['size'],flush=True);return asset

def deliver():
    assert api('')['private'];run=os.environ['GITHUB_RUN_ID'];commit=os.environ['GITHUB_SHA']
    qa=read(R/'12_RELEASE/OrlandoMX_v040_Validation.json');assert qa['compiled'] and qa['source_checks'] and qa['pkz_bytes']<500000000
    checkpoint=R/'OrlandoMX-v040-source-checkpoint.zip'
    # Include the complete v039 authoring baseline, v040 output, scripts and
    # pinned native-tool/build inputs so this is a reproducible editable source.
    with zipfile.ZipFile(checkpoint,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('V040_OUTPUT','V040_SOURCE','V039_OUTPUT','V039_SOURCE','V024_OUTPUT','V009_SOURCE',
                       'TOOLS','.github','BUILD_INPUTS','BUILD_V007','BUILD_V008','12_RELEASE/orlandomx_2026_v039','12_RELEASE/orlandomx_2026_v040'):
            for p in sorted((R/folder).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':z.write(p,p.relative_to(R).as_posix())
        for name in ('track.tht','track.hmf','map_params.ini','trh_params.ini','edf_params.ini','tool_versions.json','native_coordinate_probes.json','v040_baseline_native_validation.json'):
            p=R/'BUILD'/name;z.write(p,p.relative_to(R).as_posix())
        for p in [R/'requirements-v009.txt',R/'README.md',R/'DOCUMENTATION/v040_native_validation.json',R/'12_RELEASE/OrlandoMX_v040_Validation.json']:
            z.write(p,p.relative_to(R).as_posix())
    assert checkpoint.stat().st_size<2*1024**3
    paths=[R/'12_RELEASE'/n for n in ('OrlandoMX_2026_v040.pkz','OrlandoMX_2026_v040.pkz.sha256','OrlandoMX_v040_Validation.json','Install_v040.txt')]
    paths += [O/'v040_asset_validation.json',O/'v040_independent_validation.json',O/'v040_freestyle_validation.json',checkpoint]
    checks=R/'12_RELEASE/OrlandoMX_v040_SHA256SUMS.txt';atomic(checks,(''.join(sha(p)+'  '+p.name+'\n' for p in paths)).encode());paths.append(checks)
    release=api('/releases',dict(tag_name='v040-private-build-'+run,target_commitish=commit,name='Orlando MX v040 private verified build',draft=True,prerelease=False,make_latest='false',body='Unpublished v040 build from pinned delivered v039. Memorial/flag/door/vehicle surface conflict repairs; 8.5 m freestyle takeoff and 44 m lip-to-landing double within the two grass islands; Speed World sign relocated across the figure-eight entrance. User-confirmed Qwikchute fixes, accepted MX layout, oval pavement and walls, all original artwork/color textures and optimized normals retained. Official Windows native compilation and independent source/native validation passed. PKZ '+str(qa['pkz_bytes'])+' bytes. User in-game validation pending. Source commit '+commit+'.'))
    assets=[upload(release,p) for p in paths]
    descriptor=dict(release_id=release['id'],release_url=release['html_url'],source_commit=commit,build_run=int(run),assets=[record(a) for a in assets])
    blob=api('/git/blobs',dict(content=json.dumps(descriptor),encoding='utf-8'))
    print('CODEX_V040_DELIVERY_BLOB '+blob['sha'],flush=True)
    assert api('/releases/'+str(release['id']))['draft']
    print('All verified v040 files and complete source preserved in a private unpublished draft.',flush=True)

if __name__=='__main__':{'source':source,'deliver':deliver}[sys.argv[1]]()
