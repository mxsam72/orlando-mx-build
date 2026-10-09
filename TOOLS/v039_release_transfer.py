"""Preserve the verified native delivery in a private unpublished build."""
import hashlib,json,os,sys,urllib.request,urllib.parse,urllib.error,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=os.environ['GITHUB_REPOSITORY'];TOKEN=os.environ['V039_RELEASE_TOKEN']
API='https://api.github.com/repos/'+REPO
HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v039-native-delivery'}

def api(path,data=None):
    payload=None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(API+path,data=payload,headers=HEADERS|({'Content-Type':'application/json'} if payload else {})),timeout=150) as response:return json.load(response)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def source():
    assert api('')['private']
    release=api('/releases/407667173');assert release['draft']
    assets=[a for a in release['assets'] if a['name']=='OrlandoMX-v038-source-checkpoint.zip']
    assert len(assets)==1;asset=assets[0]
    assert asset['size']==843560247 and asset['digest']=='sha256:e3c09bf5e6e742686e93f4add25e4ec3693ee637cc482e869deb36fe43e7bf2e'
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
        raise RuntimeError('Expected private source redirect')
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        location=e.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
    checkpoint=ROOT/'BUILD/v039-tested-v038.zip';checkpoint.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256();total=0
    with urllib.request.urlopen(location,timeout=180) as response,checkpoint.open('wb') as output:
        while b:=response.read(1024*1024):output.write(b);h.update(b);total+=len(b)
    assert total==asset['size'] and h.hexdigest()==asset['digest'].removeprefix('sha256:')
    from v039_common import atomic
    with zipfile.ZipFile(checkpoint) as z:
        for info in z.infolist():
            name=info.filename
            wanted=name.startswith(('V038_OUTPUT/','V038_SOURCE/','V024_OUTPUT/')) or (name.startswith('12_RELEASE/orlandomx_2026_v038/') and not name.endswith('.map'))
            if not wanted or info.is_dir():continue
            assert '..' not in Path(name).parts
            atomic(ROOT/name,z.read(info))
    checkpoint.unlink()
    print('Immutable tested v038 source and native menu/race template restored.',flush=True)

def upload(release,path,name=None):
    name=name or path.name
    url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':name})
    with path.open('rb') as data:
        request=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
        with urllib.request.urlopen(request,timeout=1200) as response:asset=json.load(response)
    assert asset['state']=='uploaded' and asset['size']==path.stat().st_size
    print('Private verified file uploaded:',name,asset['size'],flush=True)
    return asset

def deliver():
    repo=api('');assert repo['private']
    run=os.environ['GITHUB_RUN_ID'];sha=os.environ['GITHUB_SHA']
    release=api('/releases',dict(tag_name='v039-private-build-'+run,target_commitish=sha,name='Orlando MX v039 private verified build',draft=True,prerelease=False,make_latest='false',body='Unpublished native build delivery. Source commit: '+sha+'. Sign-only correction from user-tested v038: fix horizontal Orlando Speed World UVs on both faces; remove both Qwikchute black backboards, retain flat opaque logo faces with at least 18 cm support clearance. All textures, road, geometry, red/black grass parking and other scenery preserved. PKZ verified under 500,000,000 bytes. In-game tests pending.'))
    paths=[ROOT/'12_RELEASE'/n for n in ('OrlandoMX_2026_v039.pkz','OrlandoMX_v039_Validation.json','Install_v039.txt','OrlandoMX_2026_v039.pkz.sha256')]
    paths+=[ROOT/'V039_OUTPUT'/n for n in ('v039_sign_validation.json','v039_independent_validation.json')]
    assets=[upload(release,p) for p in paths]
    checkpoint=ROOT/'OrlandoMX-v039-source-checkpoint.zip'
    with zipfile.ZipFile(checkpoint,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('V039_OUTPUT','V039_SOURCE','12_RELEASE/orlandomx_2026_v039'):
            for p in sorted((ROOT/folder).rglob('*')):
                if p.is_file():z.write(p,p.relative_to(ROOT).as_posix())
        for name in ('facility_meshes.json','vehicle_meshes.json','sign_graphic_meshes.json'):
            p=ROOT/'V024_OUTPUT'/name;z.write(p,p.relative_to(ROOT).as_posix())
    assert checkpoint.stat().st_size<2*1024**3,'Source checkpoint exceeds native release file limit'
    upload(release,checkpoint)
    records=[]
    for asset in assets:
        try:
            urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
            raise RuntimeError('Expected temporary file redirect')
        except urllib.error.HTTPError as e:
            if e.code not in (301,302,303,307,308):raise
            location=e.headers['Location']
        assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
        records.append(dict(name=asset['name'],asset_id=asset['id'],bytes=asset['size'],digest=asset['digest'],download_url=location))
    descriptor=dict(release_id=release['id'],build_run=int(run),source_commit=sha,assets=records)
    blob=api('/git/blobs',dict(content=json.dumps(descriptor),encoding='utf-8'))
    print('CODEX_V039_DELIVERY_BLOB '+blob['sha'],flush=True)
    print('Verified v039 package, validation and complete source preserved privately.',flush=True)

def diagnostic():
    assert api('')['private']
    run=os.environ['GITHUB_RUN_ID'];sha=os.environ['GITHUB_SHA']
    release=api('/releases',dict(tag_name='v039-diagnostic-'+run,target_commitish=sha,name='v039 private diagnostics; not an approved delivery',draft=True,prerelease=False,make_latest='false',body='Internal recovery checkpoint after a failed build verification. Do not distribute as a release.'))
    path=ROOT/'OrlandoMX-v039-diagnostics.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('V039_OUTPUT','DOCUMENTATION','12_RELEASE/orlandomx_2026_v039'):
            for p in sorted((ROOT/folder).rglob('*')):
                if p.is_file():z.write(p,p.relative_to(ROOT).as_posix())
        p=ROOT/'12_RELEASE/OrlandoMX_2026_v039.pkz'
        if p.is_file():z.write(p,p.relative_to(ROOT).as_posix())
    asset=upload(release,path)
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
        raise RuntimeError('Expected temporary diagnostic redirect')
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        location=e.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
    descriptor=dict(release_id=release['id'],assets=[dict(name=asset['name'],asset_id=asset['id'],bytes=asset['size'],digest=asset['digest'],download_url=location)])
    blob=api('/git/blobs',dict(content=json.dumps(descriptor),encoding='utf-8'));print('CODEX_V039_DIAGNOSTIC_BLOB '+blob['sha'],flush=True)
    print('Unapproved native diagnostic checkpoint preserved privately.',flush=True)

if __name__=='__main__':
    {'source':source,'deliver':deliver,'diagnostic':diagnostic}[sys.argv[1]]()



