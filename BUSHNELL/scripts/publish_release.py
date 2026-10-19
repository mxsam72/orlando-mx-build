"""Publish only the fully validated, branch-specific first ride download."""
from pathlib import Path
import hashlib, json, os, urllib.request
R=Path(__file__).resolve().parents[1];OUT=R/'release';REPO='mxsam72/orlando-mx-build'


def request(url,method='GET',payload=None,data=None,content_type='application/json'):
    token=os.environ['GITHUB_TOKEN'];headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':content_type,'User-Agent':'BushnellMX-build'}
    if payload is not None:data=json.dumps(payload).encode()
    with urllib.request.urlopen(urllib.request.Request(url,method=method,data=data,headers=headers),timeout=240) as response:return json.load(response)


def main():
    report=json.loads((OUT/'BushnellMX_v001_Validation.json').read_text());pkz=OUT/'BushnellMX_v001.pkz'
    if not report['checks_pass'] or not report['native_compiled'] or not report['centerline_merged']:raise ValueError('Native validation is incomplete')
    with pkz.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=report['pkz_sha256']:raise ValueError('Package hash changed')
    if report['source_commit']!=os.environ['GITHUB_SHA'] or report['run_id']!=os.environ['GITHUB_RUN_ID']:raise ValueError('Release build provenance mismatch')
    tag='bushnell-v001-first-ride-'+os.environ['GITHUB_RUN_ID']
    body='First Bushnell Motocross ride-test build from the eight supplied GoPro track-walk clips.\n\nThe approved layout is preserved, with 19 authored jump/rise profiles, 12 berms, shallow worn lines and Bushnell landmark scenery. Dimensions and object placements are estimates from the footage. Standard MX Bikes physics; no plugin required.\n\nDownload **BushnellMX_v001.pkz**, keep its name, and copy it into your active MX Bikes `mods/tracks` folder. Select **Bushnell Motocross v001** in Testing. See the installation text for the default location.\n\nNative MAP/TRH, the closed centerline, source/visual/collision height agreement, texture payloads, scenery coordinates and ZIP contents passed automated checks. **In-game loading, riding, timing and FPS checks are still pending.** Pits and the eight-rider test grid are provisional.\n\nThe previews are renders of the authored source assets, not in-game screenshots.\n\nThis release is separate from the Orlando and Moon tracks. Source: `bushnell-v001/BUSHNELL/`.\n'
    release=request('https://api.github.com/repos/'+REPO+'/releases',method='POST',payload=dict(tag_name=tag,target_commitish=os.environ['GITHUB_SHA'],name='Bushnell MX v001 — first ride test',body=body,draft=False,prerelease=True))
    upload=release['upload_url'].split('{')[0];assets=[]
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path.name=='BushnellMX_v001_Delivery.json':continue
        content='application/zip' if path.suffix in ['.pkz','.zip'] else 'image/png' if path.suffix=='.png' else 'application/json' if path.suffix=='.json' else 'text/plain'
        asset=request(upload+'?name='+path.name,method='POST',data=path.read_bytes(),content_type=content)
        if asset['size']!=path.stat().st_size:raise ValueError('Release upload size mismatch')
        assets.append(dict(name=path.name,bytes=asset['size'],url=asset['browser_download_url']))
    delivery=dict(release_url=release['html_url'],tag=tag,source_commit=os.environ['GITHUB_SHA'],assets=assets,checks_pass=True)
    (OUT/'BushnellMX_v001_Delivery.json').write_text(json.dumps(delivery,indent=2)+'\n');print(json.dumps(delivery,indent=2))


if __name__=='__main__':main()
