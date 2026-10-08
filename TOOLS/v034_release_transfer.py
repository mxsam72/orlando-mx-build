"""Preserve the verified native delivery in a private unpublished build."""
import hashlib,json,os,sys,urllib.request,urllib.parse,urllib.error,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=os.environ['GITHUB_REPOSITORY'];TOKEN=os.environ['V034_RELEASE_TOKEN']
API='https://api.github.com/repos/'+REPO
HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v034-native-delivery'}

def api(path,data=None):
    payload=None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(API+path,data=payload,headers=HEADERS|({'Content-Type':'application/json'} if payload else {})),timeout=150) as response:return json.load(response)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def source():
    assert api('')['private']
    release=api('/releases/407195622');assert release['draft']
    assets=[a for a in release['assets'] if a['name']=='OrlandoMX-v033-source-checkpoint.zip']
    assert len(assets)==1;asset=assets[0]
    assert asset['size']==979008662 and asset['digest']=='sha256:e3867f58e8dd93419effe7c98f5539ac210b4c5e4e9b83fa077dc2e1924a73a5'
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
        raise RuntimeError('Expected private source redirect')
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        location=e.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
    checkpoint=ROOT/'BUILD/v034-tested-v030.zip';checkpoint.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256();total=0
    with urllib.request.urlopen(location,timeout=180) as response,checkpoint.open('wb') as output:
        while b:=response.read(1024*1024):output.write(b);h.update(b);total+=len(b)
    assert total==asset['size'] and h.hexdigest()==asset['digest'].removeprefix('sha256:')
    from v034_common import atomic
    with zipfile.ZipFile(checkpoint) as z:
        for info in z.infolist():
            name=info.filename
            wanted=name.startswith(('V033_OUTPUT/','V033_SOURCE/','V024_OUTPUT/')) or (name.startswith('12_RELEASE/orlandomx_2026_v033/') and not name.endswith('.map'))
            if not wanted or info.is_dir():continue
            assert '..' not in Path(name).parts
            atomic(ROOT/name,z.read(info))
    checkpoint.unlink()
    print('Immutable tested v030 source and native menu/race template restored.',flush=True)

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
    release=api('/releases',dict(tag_name='v034-private-build-'+run,target_commitish=sha,name='Orlando MX v034 private verified build',draft=True,prerelease=False,make_latest='false',body='Unpublished native build delivery. Source commit: '+sha+'. Longer wider holeshot approach and separated start/corner layout. T05 arc/bank moved intact; jump shapes, other corners, tested v030 colors and all three signs preserved. Gate/pit world positions retained and native race/reset references revised. In-game tests remain pending.'))
    paths=[ROOT/'12_RELEASE'/n for n in ('OrlandoMX_2026_v034.pkz','OrlandoMX_v034_Validation.json','Install_v034.txt','OrlandoMX_2026_v034.pkz.sha256')]
    paths+=[ROOT/'V034_OUTPUT'/n for n in ('holeshot_terrain_validation.json','holeshot_race_validation.json','holeshot_scenery_validation.json','holeshot_mask_validation.json')]
    assets=[upload(release,p) for p in paths]
    checkpoint=ROOT/'OrlandoMX-v034-source-checkpoint.zip'
    with zipfile.ZipFile(checkpoint,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ('V034_OUTPUT','V034_SOURCE','12_RELEASE/orlandomx_2026_v034'):
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
    print('CODEX_V034_DELIVERY_BLOB '+blob['sha'],flush=True)
    print('Verified v034 package, previews and complete source preserved privately.',flush=True)

if __name__=='__main__':
    {'source':source,'deliver':deliver}[sys.argv[1]]()

