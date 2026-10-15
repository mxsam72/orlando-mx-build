"""Durable source/native checkpoints; publish only after the complete validation gate."""
import os
import sys
import zipfile

from v052_transfer import api, identity, upload
from v056_inputs import R, PREV, O, NAME, DEST, sha, save
from v054_geometry import read


def release():
    rel = api('/releases/' + os.environ['V056_RELEASE_ID'])
    assert rel['draft'] and rel['tag_name'].startswith('v056-restored-corners-')
    return rel


def checkpoint():
    identity()
    for name in ['terrain_validation', 'surface_validation', 'scenery_validation', 'race_validation']:
        assert read(O / (name + '.json'))['checks_pass']
    assert read(R / 'BUILD/v056_review/manifest.json')['source_only']
    archive = R / 'BUILD/OrlandoMX-v056-source-checkpoint.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for folder in [O, DEST, R / 'V056_SOURCE', R / 'BUILD/v056_review']:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    z.write(p, p.relative_to(R).as_posix())
        for p in sorted((R / 'TOOLS').glob('*v056*.py')):
            z.write(p, p.relative_to(R).as_posix())
    descriptor = R / 'BUILD/v056_checkpoint_descriptor.json'
    save(descriptor, dict(version='v056', baseline='v054', source_commit=os.environ['GITHUB_SHA'],
         source_run=int(os.environ['GITHUB_RUN_ID']), file=archive.name, bytes=archive.stat().st_size,
         sha256=sha(archive), terrain_sha256=sha(O / 'terrain.raw'), scenery_sha256=sha(O / 'scenery.fbx'),
         checked_source=True, surface_validation_sha256=sha(O / 'surface_validation.json')))
    rel = api('/releases', dict(tag_name='v056-restored-corners-' + os.environ['GITHUB_RUN_ID'],
         target_commitish=os.environ['GITHUB_SHA'], name='Orlando MX v056 restored corners and track edges — native build pending',
         body='Repairs rejected v055 from accepted delivered v054. Every corner grid and all boundary masks exact v054. Full-resolution racing maps restored. A small local landing crown correction stops before T03. Source checks passed; native and game tests pending.',
         draft=True, prerelease=True, make_latest='false'))
    for p in [archive, descriptor]:
        upload(rel, p)
    for p in sorted((R / 'BUILD/v056_review').iterdir()):
        if p.is_file():
            upload(rel, p)
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as env:
        env.write('V056_RELEASE_ID=' + str(rel['id']) + '\n')
    print('V056_SOURCE_RELEASE', rel['id'], rel['tag_name'], flush=True)


def preserve_edf():
    p = R / 'BUILD/OrlandoMX-v056-native-scenery.zip'
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(R / 'BUILD/v056_stage/scenery.edf', 'scenery.edf')
        log = R / 'DOCUMENTATION/fbx2edf_v056.log'
        if log.exists():
            z.write(log, log.name)
    upload(release(), p)


def preserve_native():
    rel = release()
    for p in [R / '12_RELEASE/OrlandoMX_2026_v056.pkz', R / '12_RELEASE/OrlandoMX_2026_v056.pkz.sha256', O / 'native_compile_results.json']:
        upload(rel, p)


def deliver():
    q = read(R / '12_RELEASE/OrlandoMX_v056_Validation.json')
    assert all(q[k] for k in ['compiled', 'source_checks', 'centerline_merged', 'native_collision_updated', 'package_integrity_passed', 'package_size_budget_passed'])
    assert q['native_object_textures']['checks_pass']
    assert all(v['checks_pass'] for v in q['source_validation'].values())
    p = R / '12_RELEASE/OrlandoMX_2026_v056.pkz'
    assert sha(p) == q['pkz_sha256'] and p.stat().st_size <= 964987509
    assert q['native_height_validation']['checks_pass']
    assert q['native_height_validation']['native_all_14_corner_grids_exact_v054']
    assert q['unchanged_decoded_texture_allocation_vs_v054']
    rel = release()
    for name in ['OrlandoMX_v056_Validation.json', 'Install_v056.txt']:
        upload(rel, R / '12_RELEASE' / name)
    surf = q['source_validation']['surface_validation']
    terrain = q['source_validation']['terrain_validation']
    body = f'''Fixes the rejected v055 corner and track-edge regression using the accepted delivered v054 baseline, including its A/B/C layout and start changes.

All 14 corner banks and riding widths are restored exactly to v054, verified on full-width sample grids and the actual native collision and visual ground. All 18 visual/physical surface masks are byte-exact v054. The overly wide racing texture mask from v055 is removed. Full-resolution 4K racing photographs/normals, 8K colour/normal atlases, original compaction and directional grooming return. No reduced wear overlay or exaggerated macro normals.

The only colour change from v054 is a small base-soil tint of RGB -6/-4/-4, preserving approximately 75% of the original colour separation from the racing dirt. Clear boundaries take priority over a uniform dirt field.

The R03 right-side landing crown is reduced locally between route stations 261.8 and 272.0, before T03. Only {terrain['changed_samples']} RAW samples change from v054; every corner grid and the single's centre profile remain exact. This preserves the bank into the turn rather than flattening the turn. Unrelated jumps, race/start/reset data and all scenery remain exact.

Memory budget: same 14 layers, same unique active texture dimensions as accepted v054, no new texture allocations. This restores image quality lost in v055. Actual game memory/VRAM and FPS have not been measured. PKZ {q['pkz_bytes']:,} bytes.

Official TerrainEd MAP/TRH compilation and native route merge, complete 4,198,401-sample visual and collision grid equality, all 14 corner protections, bitmap/scenery probes, retained race files and 13-entry ZIP CRC passed. Actual MX Bikes appearance, loading, timing and riding still require a game test. Source previews are labelled and are not game screenshots. All players need the same PKZ.'''
    rel = api('/releases/' + str(rel['id']), dict(name='Orlando MX v056 — restored corners, clear edges and full-quality dirt',
         body=body, draft=False, prerelease=True, make_latest='false'), method='PATCH')
    # Keep the rejected release available for audit but flag its status clearly.
    old=api('/releases/413295265')
    assert old['tag_name']=='v055-soil-landing-38658838015'
    api('/releases/413295265',dict(name='Orlando MX v055 — rejected corner/edge regression; use v056',
        body='Superseded by '+rel['html_url']+'. This build was rejected in game: its broad landing patch removed part of T03/T12 and its shoulder blend obscured track boundaries. Use v056.\n\n'+old['body']),method='PATCH')
    assets = api('/releases/' + str(rel['id']))['assets']
    asset = next(a for a in assets if a['name'] == p.name)
    assert asset['size'] == q['pkz_bytes'] and asset['digest'] == 'sha256:' + q['pkz_sha256']
    save(R / 'BUILD/v056_delivery.json', dict(release_url=rel['html_url'], download_url=asset['browser_download_url'],
         release_id=rel['id'], pkz_sha256=q['pkz_sha256'], pkz_bytes=q['pkz_bytes']))
    print('V056_DOWNLOAD', asset['browser_download_url'], flush=True)


if __name__ == '__main__':
    {'checkpoint': checkpoint, 'deliver': deliver}[sys.argv[1]]()
