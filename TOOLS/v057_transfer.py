"""Durable source/native checkpoints; publish only after the complete validation gate."""
import os
import sys
import zipfile

from v052_transfer import api, identity, upload
from v057_inputs import R, PREV, O, NAME, DEST, sha, save
from v054_geometry import read


def release():
    rel = api('/releases/' + os.environ['V057_RELEASE_ID'])
    assert rel['draft'] and rel['tag_name'].startswith('v057-loam-express-')
    return rel


def checkpoint():
    identity()
    for name in ['terrain_validation', 'surface_validation', 'scenery_validation', 'race_validation']:
        assert read(O / (name + '.json'))['checks_pass']
    assert read(R / 'BUILD/v057_review/manifest.json')['source_only']
    archive = R / 'BUILD/OrlandoMX-v057-source-checkpoint.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for folder in [O, DEST, R / 'V057_SOURCE', R / 'BUILD/v057_review']:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    z.write(p, p.relative_to(R).as_posix())
        for p in sorted((R / 'TOOLS').glob('*v057*.py')):
            z.write(p, p.relative_to(R).as_posix())
    descriptor = R / 'BUILD/v057_checkpoint_descriptor.json'
    save(descriptor, dict(version='v057', baseline='user-tested v056', source_commit=os.environ['GITHUB_SHA'],
         source_run=int(os.environ['GITHUB_RUN_ID']), file=archive.name, bytes=archive.stat().st_size,
         sha256=sha(archive), terrain_sha256=sha(O / 'terrain.raw'), scenery_sha256=sha(O / 'scenery.fbx'),
         checked_source=True, surface_validation_sha256=sha(O / 'surface_validation.json')))
    rel = api('/releases', dict(tag_name='v057-loam-express-' + os.environ['GITHUB_RUN_ID'],
         target_commitish=os.environ['GITHUB_SHA'], name='Orlando MX v057 — loam, Express and pit update; native build pending',
         body='Based on user-tested v056. Strict 25% overlay cap, current-route loam and new photographic grain normals. Five marked Cybertrucks: 3 black / 2 stainless. Rebuilt Chevrolet Express and readable solid cardboard sign 3m from the van. Source checks passed; native build pending.',
         draft=True, prerelease=True, make_latest='false'))
    for p in [archive, descriptor]:
        upload(rel, p)
    for p in sorted((R / 'BUILD/v057_review').iterdir()):
        if p.is_file():
            upload(rel, p)
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as env:
        env.write('V057_RELEASE_ID=' + str(rel['id']) + '\n')
    print('V057_SOURCE_RELEASE', rel['id'], rel['tag_name'], flush=True)


def preserve_edf():
    p = R / 'BUILD/OrlandoMX-v057-native-scenery.zip'
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(R / 'BUILD/v057_stage/scenery.edf', 'scenery.edf')
        log = R / 'DOCUMENTATION/fbx2edf_v057.log'
        if log.exists():
            z.write(log, log.name)
    upload(release(), p)


def preserve_native():
    rel = release()
    for p in [R / '12_RELEASE/OrlandoMX_2026_v057.pkz', R / '12_RELEASE/OrlandoMX_2026_v057.pkz.sha256', O / 'native_compile_results.json']:
        upload(rel, p)


def deliver():
    q = read(R / '12_RELEASE/OrlandoMX_v057_Validation.json')
    assert all(q[k] for k in ['compiled', 'source_checks', 'centerline_merged', 'native_collision_retained', 'package_integrity_passed', 'package_size_budget_passed'])
    assert q['native_object_textures']['checks_pass']
    assert all(v['checks_pass'] for v in q['source_validation'].values())
    p = R / '12_RELEASE/OrlandoMX_2026_v057.pkz'
    assert sha(p) == q['pkz_sha256'] and p.stat().st_size <= 964987509
    assert q['native_height_validation']['checks_pass']
    assert q['native_height_validation']['native_all_14_corner_grids_exact_v054']
    assert q['estimated_source_texture_and_geometry_budget_not_increased']
    rel = release()
    for name in ['OrlandoMX_v057_Validation.json', 'Install_v057.txt']:
        upload(rel, R / '12_RELEASE' / name)
    body = f'''Based on user-tested v056. All 4,198,401 ground samples, all 14 corner banks, repaired landing, track boundaries, race/reset data and start positions are retained.

Racing overlay is capped below 25% (8-bit alpha 63/255 = 24.71%). The full 4K photographic dirt colours are exposed, with photograph-derived fine clod normals and new loamy relief using the current riding direction. Flat surfaces get more loose cultivation. No diagonal tread stamps or cross-track comb terms are authored.

The five circled Cybertrucks alternate black/stainless in screenshot order: 3 black, 2 silver. The unmarked green truck and existing silver/red/black displays remain unchanged. The black Chevrolet Express gets a shorter bonnet, forward cab, low rounded cargo roof, solid cargo sides, steel wheels, Express fascia and Chevrolet bowtie. A weathered cardboard FREE CANDY sign (2m x 1m) sits 3m clear of the van's nose; its text is forward and upright on both solid, separated faces, without coplanar flickering decals.

Same 14 terrain layers and texture dimensions. Five unused paint textures removed; existing black/stainless materials reused. Source decoded texture plus conservative geometry allocation estimate is lower than v056. Actual game RAM/VRAM and FPS are unmeasured. PKZ: {q['pkz_bytes']:,} bytes.

Official native compilation, route merge, complete native visual/collision height-grid checks, terrain/object bitmap payload checks, source-to-native scenery probes, retained race files and 13-entry ZIP CRC passed. Game appearance/loading and riding still need a test. Source previews are not MX Bikes screenshots. All players need the same PKZ.'''
    rel = api('/releases/' + str(rel['id']), dict(name='Orlando MX v057 — loamy dirt, Chevrolet Express and pit update',
         body=body, draft=False, prerelease=True, make_latest='false'), method='PATCH')
    assets = api('/releases/' + str(rel['id']))['assets']
    asset = next(a for a in assets if a['name'] == p.name)
    assert asset['size'] == q['pkz_bytes'] and asset['digest'] == 'sha256:' + q['pkz_sha256']
    save(R / 'BUILD/v057_delivery.json', dict(release_url=rel['html_url'], download_url=asset['browser_download_url'],
         release_id=rel['id'], pkz_sha256=q['pkz_sha256'], pkz_bytes=q['pkz_bytes']))
    print('V057_DOWNLOAD', asset['browser_download_url'], flush=True)


if __name__ == '__main__':
    {'checkpoint': checkpoint, 'deliver': deliver}[sys.argv[1]]()
