"""Private draft-release transport when Actions artifact storage is full.

No repository credentials leave the runner. Only narrowly scoped, temporary
asset download URLs are emitted for the authorized build-file transfer.
The transport draft remains unpublished; its tag anchors to the default
branch and its body records the actual build commit separately.
"""
from pathlib import Path
import os,json,hashlib,urllib.request,urllib.parse,urllib.error,zipfile,sys

ROOT=Path(__file__).resolve().parents[1]
REPO=os.environ['GITHUB_REPOSITORY'];TOKEN=os.environ['V030_RELEASE_TOKEN']
API='https://api.github.com/repos/'+REPO
HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json',
         'X-GitHub-Api-Version':'2026-03-10','User-Agent':'OrlandoMX-v030-build'}

def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    headers=HEADERS|({'Content-Type':'application/json'} if body is not None else {})
    request=urllib.request.Request(API+path,data=body,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)

def upload(release,path):
    url=release['upload_url'].split('{',1)[0]+'?'+urllib.parse.urlencode({'name':path.name})
    headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)}
    with path.open('rb') as source:
        request=urllib.request.Request(url,data=source,headers=headers,method='POST')
        with urllib.request.urlopen(request,timeout=1200) as response:result=json.load(response)
    assert result['state']=='uploaded' and result['size']==path.stat().st_size
    print('Private draft asset uploaded:',path.name,result['size'],flush=True)
    return result

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def transfer(asset,path):
    request=urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=120) as response:
            raise RuntimeError('Expected a temporary asset redirect; got '+str(response.status))
    except urllib.error.HTTPError as error:
        if error.code not in (301,302,303,307,308):raise
        location=error.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ['release-assets.githubusercontent.com','objects.githubusercontent.com']
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if asset.get('digest'):assert asset['digest']=='sha256:'+digest
    # This is file-transfer metadata, never an API token or session credential.
    print('CODEX_V030_ASSET '+json.dumps(dict(asset_id=asset['id'],name=path.name,bytes=path.stat().st_size,
        sha256=digest,download_url=location)),flush=True)

def preflight():
    repo=api('');assert repo['private'],'Build transfer requires the existing private repository'
    run=os.environ['GITHUB_RUN_ID'];sha=os.environ['GITHUB_SHA']
    release=api('/releases',dict(tag_name='v030-private-transfer-'+run,target_commitish=repo['default_branch'],
        name='Private build transfer: Orlando MX v030',draft=True,prerelease=False,make_latest='false',
        generate_release_notes=False,body='Unpublished build-file transport. Actual v030 source commit: '+sha+'. Grass starts from v028; main pits unchanged, marked start section cleared, remaining track grass halved patch by patch.'),'POST')
    assert release['draft']
    probe=ROOT/'v030_transfer_probe.txt';probe.write_text('Orlando MX v030 private asset-transfer probe\n')
    asset=upload(release,probe);transfer(asset,probe)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('release_id='+str(release['id'])+'\n')
    print('Private draft transfer preflight passed; release ID',release['id'],flush=True)

def deliver():
    release=api('/releases/'+os.environ['V030_RELEASE_ID']);assert release['draft'] and api('')['private']
    records=[]
    for name in ['OrlandoMX_2026_v030.pkz','OrlandoMX_v030_Validation.json','Install_v030.txt','OrlandoMX_2026_v030.pkz.sha256']:
        path=ROOT/'12_RELEASE'/name;assert path.is_file();records.append((upload(release,path),path))
    path=ROOT/'V030_OUTPUT/grass_scope_comparison.png';records.append((upload(release,path),path))
    # Keep the complete generated source and compiled native folder durable,
    # alongside the exact game package, for the next correction or version.
    checkpoint=ROOT/'OrlandoMX-v030-source-checkpoint.zip'
    folders=['V030_OUTPUT','12_RELEASE/orlandomx_2026_v030']
    extras=['V024_OUTPUT/facility_meshes.json','V024_OUTPUT/vehicle_meshes.json','V024_OUTPUT/sign_graphic_meshes.json']
    with zipfile.ZipFile(checkpoint,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for folder in folders:
            for source in sorted((ROOT/folder).rglob('*')):
                if source.is_file():archive.write(source,source.relative_to(ROOT).as_posix())
        for source in extras:archive.write(ROOT/source,source)
    records.append((upload(release,checkpoint),checkpoint))
    # Refresh all temporary download URLs after the large checkpoint upload.
    for asset,path in records:transfer(asset,path)
    print('Private draft native delivery and complete source preservation passed',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='preflight':preflight()
    elif sys.argv[1]=='deliver':deliver()
    else:raise SystemExit('Expected preflight or deliver')
