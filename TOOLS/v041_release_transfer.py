"""Restore immutable v040 and preserve verified v041 as an unpublished draft."""
import hashlib,json,os,sys,urllib.request,urllib.parse,urllib.error,zipfile
from pathlib import Path
from v041_common import *
API='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
TOKEN=os.environ['V041_RELEASE_TOKEN']
HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v041-private-delivery'}

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
    asset=found['OrlandoMX-v040-source-checkpoint.zip']
    assert asset['size']==cfg['baseline_checkpoint_bytes'] and asset['digest']=='sha256:'+cfg['baseline_checkpoint_sha256']
    path=R/'BUILD/v041-v040-baseline.zip';download(asset,path)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for info in z.infolist():
            name=info.filename
            if info.is_dir():continue
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            if name.startswith(('V040_OUTPUT/','V040_SOURCE/','V039_OUTPUT/','V039_SOURCE/','V024_OUTPUT/')) or (name.startswith('12_RELEASE/orlandomx_2026_v040/') and not name.endswith('.map')):atomic(R/name,z.read(info))
    path.unlink()
    a=found['OrlandoMX_v040_Validation.json'];assert a['digest']=='sha256:'+cfg['baseline_validation_sha256']
    p=R/'BUILD/v041_baseline_native_validation.json';download(a,p);qa=read(p)
    assert qa['compiled'] and qa['centerline_merged'] and qa['source_checks']
    assert qa['pkz_bytes']==cfg['baseline_pkz_bytes'] and qa['pkz_sha256']==cfg['baseline_pkz_sha256']
    assert sha(BASE/'scenery.fbx')==cfg['baseline_scenery_sha256'] and sha(BASE/'terrain.raw')==cfg['baseline_terrain_sha256']
    print('Pinned v040 source and actual native validation restored and authenticated before editing.',flush=True)

def upload(release,path):
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':path.name})
    with path.open('rb') as data:
        req=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as response:asset=json.load(response)
    assert asset['state']=='uploaded' and asset['size']==path.stat().st_size
    print('Private verified file saved:',path.name,asset['size'],flush=True);return asset

def deliver():
    assert api('')['private'];run=os.environ['GITHUB_RUN_ID'];commit=os.environ['GITHUB_SHA']
    qa=read(R/'12_RELEASE/OrlandoMX_v041_Validation.json');assert qa['compiled'] and qa['source_checks'] and qa['pkz_bytes']<500000000
    checkpoint=R/'OrlandoMX-v041-source-checkpoint.zip'
    # Include the complete v040 authoring baseline, v041 output, scripts and
    # pinned native-tool/build inputs so this is a reproducible editable source.
    with zipfile.ZipFile(checkpoint,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('V041_OUTPUT','V041_SOURCE','V040_OUTPUT','V040_SOURCE','V039_OUTPUT','V039_SOURCE','V024_OUTPUT','V009_SOURCE',
                       'TOOLS','.github','BUILD_INPUTS','BUILD_V007','BUILD_V008','12_RELEASE/orlandomx_2026_v040','12_RELEASE/orlandomx_2026_v041'):
            for p in sorted((R/folder).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':z.write(p,p.relative_to(R).as_posix())
        for name in ('track.tht','track.hmf','map_params.ini','trh_params.ini','edf_params.ini','tool_versions.json','native_coordinate_probes.json','v041_baseline_native_validation.json'):
            p=R/'BUILD'/name;z.write(p,p.relative_to(R).as_posix())
        for p in [R/'requirements-v009.txt',R/'README.md',R/'DOCUMENTATION/v041_native_validation.json',R/'12_RELEASE/OrlandoMX_v041_Validation.json']:
            z.write(p,p.relative_to(R).as_posix())
    assert checkpoint.stat().st_size<2*1024**3
    paths=[R/'12_RELEASE'/n for n in ('OrlandoMX_2026_v041.pkz','OrlandoMX_2026_v041.pkz.sha256','OrlandoMX_v041_Validation.json','Install_v041.txt')]
    paths += [O/'v041_asset_validation.json',O/'v041_independent_validation.json',O/'v041_gap_validation.json',O/'v041_seating_validation.json',O/'v041_vehicle_validation.json',O/'v041_crocodile_validation.json',checkpoint]
    checks=R/'12_RELEASE/OrlandoMX_v041_SHA256SUMS.txt';atomic(checks,(''.join(sha(p)+'  '+p.name+'\n' for p in paths)).encode());paths.append(checks)
    release=api('/releases',dict(tag_name='v041-private-build-'+run,target_commitish=commit,name='Orlando MX v041 private verified build',draft=True,prerelease=False,make_latest='false',body='Unpublished v041 build from pinned delivered v040. Native asphalt collision infill closes the pavement-to-wall slot without changing the accepted road. Ten-row metal stadium seating faces the course opposite the entrance. Three generic red pit pickups replaced with blue, purple and green Cybertrucks. Twelve-metre generated photographic crocodile silhouette in the existing water section. Delivered v040 freestyle double and entrance placement retained. User-confirmed Qwikchute fixes, accepted MX layout, oval pavement and walls, all original artwork/color textures and optimized normals retained. Official Windows native compilation and independent source/native validation passed. PKZ '+str(qa['pkz_bytes'])+' bytes. User in-game validation pending. Source commit '+commit+'.'))
    assets=[upload(release,p) for p in paths]
    descriptor=dict(release_id=release['id'],release_url=release['html_url'],source_commit=commit,build_run=int(run),assets=[record(a) for a in assets])
    blob=api('/git/blobs',dict(content=json.dumps(descriptor),encoding='utf-8'))
    print('CODEX_V041_DELIVERY_BLOB '+blob['sha'],flush=True)
    assert api('/releases/'+str(release['id']))['draft']
    print('All verified v041 files and complete source preserved in a private unpublished draft.',flush=True)

if __name__=='__main__':{'source':source,'deliver':deliver}[sys.argv[1]]()
