"""Recover checksum-pinned delivered v054 source and its unchanged native scenery."""
import concurrent.futures
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from v052_transfer import api, HEADERS, identity, safe, extract
from v048_surface import R, BASE, sha, save

PREV = R / 'V054_OUTPUT'
O = R / 'V056_OUTPUT'
M = O / 'materials'
NAME = 'orlandomx_2026_v056'
DEST = R / '12_RELEASE' / NAME
TAG = 'v054-start-corners-38605191325'
PINS = {
    'OrlandoMX-v054-source-checkpoint.zip': (427895975, 'c2f756e94e37acf8f6cc95974765807032c1b22c974fae7a80c719d6c90e8992'),
    'OrlandoMX-v054-native-scenery.zip': (228735136, '50e3d6ac7a96b9988f5c9cf23ccb3c72fdd7cabe9841fbd4af00b67a74e8e8ed'),
    'OrlandoMX_v054_Validation.json': (142952, '9c485385b2fdfb373b5e9d2a2e2ced9ab1ec48154a2c8f3023f49b7b4ec16fd7'),
}


def download(item):
    name, (size, digest) = item
    p = R / 'BUILD/v056_inputs' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.stat().st_size == size and sha(p) == digest:
        return p
    url = 'https://github.com/mxsam72/orlando-mx-build/releases/download/' + TAG + '/' + name
    with urllib.request.urlopen(url, timeout=300) as src, p.with_suffix('.part').open('wb') as out:
        shutil.copyfileobj(src, out, 4 * 1024 * 1024)
    part = p.with_suffix('.part')
    assert part.stat().st_size == size and sha(part) == digest, name
    part.replace(p)
    print('Verified v054 input', name, size, flush=True)
    return p


def current():
    identity()
    rel = api('/releases/tags/' + TAG)
    assert not rel['draft'] and rel['id'] == 412990475
    assets = {a['name']: a for a in rel['assets']}
    for name, (size, digest) in PINS.items():
        assert assets[name]['size'] == size and assets[name]['digest'] == 'sha256:' + digest
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download, PINS.items()))
    folder = R / 'BUILD/v056_inputs'
    with zipfile.ZipFile(folder / 'OrlandoMX-v054-source-checkpoint.zip') as z:
        assert z.testzip() is None
        for i in z.infolist():
            safe(i.filename)
            if not i.is_dir() and i.filename.startswith(('V054_OUTPUT/', '12_RELEASE/orlandomx_2026_v054/')):
                extract(z, i, R / i.filename)
    native = R / 'BUILD/v056_native_baseline'
    native.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(folder / 'OrlandoMX-v054-native-scenery.zip') as z:
        assert z.testzip() is None and set(z.namelist()) == {'scenery.edf', 'fbx2edf_v054.log'}
        extract(z, z.getinfo('scenery.edf'), native / 'scenery.edf')
    import json
    report = json.loads((folder / 'OrlandoMX_v054_Validation.json').read_text())
    assert report['compiled'] and report['package_integrity_passed']
    assert sha(PREV / 'terrain.raw') == 'dcd96591f21b94a0bc8d23d6a779f93a117d6e833a1555868d8ef7e01adbeacd'
    assert sha(PREV / 'scenery.fbx') == 'c3ce33f0ed156031fd9d75a87d4786777333ac9097b7635b0fd23e06e3957389'
    save(R / 'BUILD/v056_input_validation.json', dict(checks_pass=True, baseline='v054', pins=PINS,
         terrain_sha256=sha(PREV / 'terrain.raw'), scenery_sha256=sha(PREV / 'scenery.fbx'),
         scenery_edf_sha256=sha(native / 'scenery.edf'), baseline_pkz_bytes=report['pkz_bytes']))
    for p in folder.glob('*.zip'):
        p.unlink()
    print('Delivered v054 current source recovered exactly', flush=True)


def restore():
    from v054_inputs import restore as base_restore
    base_restore()
    current()


if __name__ == '__main__':
    if not os.environ.get('V052_RELEASE_TOKEN'):
        HEADERS.pop('Authorization', None)
    {'restore': restore, 'current': current}[sys.argv[1]]()
