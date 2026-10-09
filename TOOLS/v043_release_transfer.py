"""Authenticate delivered v042 and preserve verified v043 in a private draft."""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import zipfile
from v043_common import *

API = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
TOKEN = os.environ['V043_RELEASE_TOKEN']
HEADERS = {'Authorization': 'Bearer '+TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'OrlandoMX-v043-private-delivery'}

def api(path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    headers = HEADERS | ({'Content-Type': 'application/json'} if payload else {})
    with urllib.request.urlopen(urllib.request.Request(API+path, data=payload, headers=headers), timeout=150) as response:
        return json.load(response)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def record(asset):
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(asset['url'], headers=HEADERS|{'Accept': 'application/octet-stream'}), timeout=120)
        raise RuntimeError('Expected private release file redirect')
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        location = error.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com', 'objects.githubusercontent.com')
    return dict(name=asset['name'], asset_id=asset['id'], bytes=asset['size'], digest=asset['digest'], download_url=location)

def download(asset, path):
    rec = record(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    count = 0
    with urllib.request.urlopen(rec['download_url'], timeout=180) as response, path.open('wb') as output:
        while chunk := response.read(4*1024*1024):
            output.write(chunk)
            h.update(chunk)
            count += len(chunk)
    assert count == rec['bytes'] and h.hexdigest() == rec['digest'].removeprefix('sha256:')

def source():
    assert api('')['private']
    cfg = read(S/'update.json')
    release = api('/releases/'+str(cfg['baseline_release_id']))
    assert release['draft'] and release['target_commitish'] == cfg['baseline_source_commit']
    found = {a['name']: a for a in release['assets']}
    asset = found['OrlandoMX-v042-source-checkpoint.zip']
    assert asset['size'] == cfg['baseline_checkpoint_bytes']
    assert asset['digest'] == 'sha256:'+cfg['baseline_checkpoint_sha256']
    path = R/'BUILD/v043-v042-baseline.zip'
    download(asset, path)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for info in archive.infolist():
            name = info.filename
            if info.is_dir():
                continue
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            restore = name.startswith(('V042_OUTPUT/', 'V042_SOURCE/', 'V024_OUTPUT/'))
            restore |= name.startswith('12_RELEASE/orlandomx_2026_v042/') and not name.endswith('.map')
            if restore:
                atomic(R/name, archive.read(info))
    path.unlink()
    validation = found['OrlandoMX_v042_Validation.json']
    assert validation['digest'] == 'sha256:'+cfg['baseline_validation_sha256']
    dest = R/'BUILD/v043_baseline_native_validation.json'
    download(validation, dest)
    qa = read(dest)
    assert qa['compiled'] and qa['centerline_merged'] and qa['source_checks']
    assert qa['source_commit'] == cfg['baseline_source_commit']
    assert all(qa[k]['checks_pass'] for k in ['independent_source_checks', 'staging_validation', 'object_texture_validation', 'native_coordinate_validation'])
    assert qa['pkz_bytes'] == cfg['baseline_pkz_bytes'] and qa['pkz_sha256'] == cfg['baseline_pkz_sha256']
    assert sha(BASE/'scenery.fbx') == cfg['baseline_scenery_sha256']
    assert sha(BASE/'terrain.raw') == cfg['baseline_terrain_sha256']
    print('Delivered v042 checkpoint and actual native validation authenticated before editing.', flush=True)

def upload(release, path):
    url = release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name': path.name})
    with path.open('rb') as data:
        headers = HEADERS | {'Content-Type': 'application/octet-stream', 'Content-Length': str(path.stat().st_size)}
        request = urllib.request.Request(url, data=data, method='POST', headers=headers)
        with urllib.request.urlopen(request, timeout=1800) as response:
            asset = json.load(response)
    assert asset['state'] == 'uploaded' and asset['size'] == path.stat().st_size
    assert asset['digest'] == 'sha256:'+sha(path)
    print('Private verified file saved:', path.name, asset['size'], flush=True)
    return asset

def deliver():
    assert api('')['private']
    run, commit = os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_SHA']
    qa = read(R/'12_RELEASE/OrlandoMX_v043_Validation.json')
    assert qa['compiled'] and qa['source_checks'] and qa['pkz_bytes'] < 500000000
    assert qa['source_commit'] == commit
    checkpoint = R/'OrlandoMX-v043-source-checkpoint.zip'
    # Complete editable current source plus the exact v042 baseline and all
    # scripts/tool inputs needed to reproduce v043. Older derived V039/V040
    # output caches and the previous native MAP are available in their original
    # private releases; they are not inputs to the v043 rebuild.
    folders = ('V043_OUTPUT', 'V043_SOURCE', 'V042_OUTPUT', 'V042_SOURCE', 'V041_SOURCE', 'V040_SOURCE', 'V039_SOURCE',
               'V024_OUTPUT', 'V009_SOURCE', 'TOOLS', '.github', 'BUILD_INPUTS', 'BUILD_V007', 'BUILD_V008',
               '12_RELEASE/orlandomx_2026_v042', '12_RELEASE/orlandomx_2026_v043')
    with zipfile.ZipFile(checkpoint, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for folder in folders:
            for p in sorted((R/folder).rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts or p.suffix == '.pyc' or p.name.startswith('.'):
                    continue
                if folder == '12_RELEASE/orlandomx_2026_v042' and p.suffix == '.map':
                    continue
                archive.write(p, p.relative_to(R).as_posix())
        for name in ('track.tht', 'track.hmf', 'map_params.ini', 'trh_params.ini', 'edf_params.ini', 'tool_versions.json',
                     'native_coordinate_probes.json', 'v043_baseline_native_validation.json'):
            p = R/'BUILD'/name
            archive.write(p, p.relative_to(R).as_posix())
        for p in [R/'requirements-v009.txt', R/'README.md', R/'DOCUMENTATION/v043_native_validation.json', R/'12_RELEASE/OrlandoMX_v043_Validation.json']:
            archive.write(p, p.relative_to(R).as_posix())
    assert checkpoint.stat().st_size < 2*1024**3
    with zipfile.ZipFile(checkpoint) as archive:
        assert archive.testzip() is None
    paths = [R/'12_RELEASE'/n for n in ('OrlandoMX_2026_v043.pkz', 'OrlandoMX_2026_v043.pkz.sha256', 'OrlandoMX_v043_Validation.json', 'Install_v043.txt')]
    paths += [O/'v043_asset_validation.json', O/'v043_independent_validation.json', O/'v043_flag_validation.json', O/'v043_vehicle_validation.json', checkpoint]
    checks = R/'12_RELEASE/OrlandoMX_v043_SHA256SUMS.txt'
    atomic(checks, (''.join(sha(p)+'  '+p.name+'\n' for p in paths)).encode())
    paths.append(checks)
    release = api('/releases', dict(tag_name='v043-private-build-'+run, target_commitish=commit,
        name='Orlando MX v043 private verified build', draft=True, prerelease=False, make_latest='false',
        body='Unpublished v043 from the authenticated delivered v042 checkpoint. Corrected only the track-facing American flag horizontal UVs so the canton stays at the physical hoist on both sides; accepted pit-facing UVs, original artwork, pole, winding and 30 cm separated opaque faces retained. Added Sam Ford F-150 King Ranch beside the Qwikchute billboard at the figure-eight course, using the accepted model and original opaque materials, terrain-fitted with audited parking clearance. Original pit Ford and all previous vehicles retained. All accepted MX course, figure-eight road and wall-gap collision fill, freestyle double, inward-facing stadium seating, crocodile, Qwikchute and Speed World signs, memorial, race data and optimized textures preserved. Official Windows compilation and independent source/native validation passed. PKZ '+str(qa['pkz_bytes'])+' bytes. User in-game confirmation pending. Complete editable source and exact v042 rebuild baseline included. Source commit '+commit+'.'))
    assets = [upload(release, path) for path in paths]
    descriptor = dict(release_id=release['id'], release_url=release['html_url'], source_commit=commit,
                      build_run=int(run), assets=[record(a) for a in assets])
    blob = api('/git/blobs', dict(content=json.dumps(descriptor), encoding='utf-8'))
    print('CODEX_V043_DELIVERY_BLOB '+blob['sha'], flush=True)
    assert api('/releases/'+str(release['id']))['draft']
    print('v043 playable assets and complete editable checkpoint saved privately without publication.', flush=True)

if __name__ == '__main__':
    {'source': source, 'deliver': deliver}[sys.argv[1]]()
