"""Durable source/native checkpoints; publish only after the complete validation gate."""
import os
import sys
import zipfile

from v052_transfer import api, identity, upload
from v055_inputs import R, PREV, O, NAME, DEST, sha, save
from v054_geometry import read


def release():
    rel = api('/releases/' + os.environ['V055_RELEASE_ID'])
    assert rel['draft'] and rel['tag_name'].startswith('v055-soil-landing-')
    return rel


def checkpoint():
    identity()
    for name in ['terrain_validation', 'surface_validation', 'scenery_validation', 'race_validation']:
        assert read(O / (name + '.json'))['checks_pass']
    assert read(R / 'BUILD/v055_review/manifest.json')['source_only']
    archive = R / 'BUILD/OrlandoMX-v055-source-checkpoint.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for folder in [O, DEST, R / 'V055_SOURCE', R / 'BUILD/v055_review']:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    z.write(p, p.relative_to(R).as_posix())
        for p in sorted((R / 'TOOLS').glob('*v055*.py')):
            z.write(p, p.relative_to(R).as_posix())
    descriptor = R / 'BUILD/v055_checkpoint_descriptor.json'
    save(descriptor, dict(version='v055', baseline='v054', source_commit=os.environ['GITHUB_SHA'],
         source_run=int(os.environ['GITHUB_RUN_ID']), file=archive.name, bytes=archive.stat().st_size,
         sha256=sha(archive), terrain_sha256=sha(O / 'terrain.raw'), scenery_sha256=sha(O / 'scenery.fbx'),
         checked_source=True, surface_validation_sha256=sha(O / 'surface_validation.json')))
    rel = api('/releases', dict(tag_name='v055-soil-landing-' + os.environ['GITHUB_RUN_ID'],
         target_commitish=os.environ['GITHUB_SHA'], name='Orlando MX v055 soil/landing update — native build pending',
         body='Delivered v054 baseline. Source height, shoulder palette, texture allocation, race and scenery checks passed. Native build and game test pending.',
         draft=True, prerelease=True, make_latest='false'))
    for p in [archive, descriptor]:
        upload(rel, p)
    for p in sorted((R / 'BUILD/v055_review').iterdir()):
        if p.is_file():
            upload(rel, p)
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as env:
        env.write('V055_RELEASE_ID=' + str(rel['id']) + '\n')
    print('V055_SOURCE_RELEASE', rel['id'], rel['tag_name'], flush=True)


def preserve_edf():
    p = R / 'BUILD/OrlandoMX-v055-native-scenery.zip'
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(R / 'BUILD/v055_stage/scenery.edf', 'scenery.edf')
        log = R / 'DOCUMENTATION/fbx2edf_v055.log'
        if log.exists():
            z.write(log, log.name)
    upload(release(), p)


def preserve_native():
    rel = release()
    for p in [R / '12_RELEASE/OrlandoMX_2026_v055.pkz', R / '12_RELEASE/OrlandoMX_2026_v055.pkz.sha256', O / 'native_compile_results.json']:
        upload(rel, p)


def deliver():
    q = read(R / '12_RELEASE/OrlandoMX_v055_Validation.json')
    assert all(q[k] for k in ['compiled', 'source_checks', 'centerline_merged', 'native_collision_updated', 'package_integrity_passed', 'package_size_budget_passed'])
    assert q['native_object_textures']['checks_pass']
    assert all(v['checks_pass'] for v in q['source_validation'].values())
    p = R / '12_RELEASE/OrlandoMX_2026_v055.pkz'
    assert sha(p) == q['pkz_sha256'] and p.stat().st_size <= q['baseline_pkz_bytes']
    rel = release()
    for name in ['OrlandoMX_v055_Validation.json', 'Install_v055.txt']:
        upload(rel, R / '12_RELEASE' / name)
    surf = q['source_validation']['surface_validation']
    terrain = q['source_validation']['terrain_validation']
    body = f'''Built from delivered v054, retaining the accepted wider A/C corners and rerouted B start.

Shoulder soil closely matches the accepted racing dirt hue. The same photographic skin blends farther across the bare shoulders. More of the real soil photograph shows through the macro overlay, exposing grain and clods while retaining lengthwise grooming. No new terrain layers or texture allocations.

R03 table-single repair: removes the inherited right-side landing/runout rise, reducing the measured maximum cross-width difference from {terrain['landing_cross_height_range_before_max_m']:.3f} m to {terrain['landing_cross_height_range_after_max_m']:.3f} m. The table and single, centre profile, other jumps, main/start routes, race/grid/pit/reset data and scenery outside the repair remain. Nearby object bases are bound vertically to the repaired ground.

Memory optimisation: photographic tiles 4K to 2K, macro colour atlas 8K to 4K, selected older dirt tiles to 1K; the directional normal atlas remains 8K. Unique active terrain texture dimensions imply {surf['rgba8_base_level_bytes_saved'] / 1048576:.0f} MiB less RGBA8 base-level allocation ({surf['estimated_rgba8_full_mip_bytes_saved'] / 1048576:.0f} MiB with complete mip pyramids). These are allocation estimates, not measured game RAM/VRAM or FPS.

PKZ {q['pkz_bytes']:,} bytes, {q['pkz_bytes_saved']:,} bytes smaller than v054. Official FBX2EDF, TerrainEd MAP/TRH, native centreline merge, bitmap/geometry, retained race files and 13-entry archive checks passed.

Actual MX Bikes load, first-lap timing, R03 riding, dirt/shoulder appearance and FPS require the user's game test. Source previews are labelled and are not game screenshots. All players need the same version.'''
    rel = api('/releases/' + str(rel['id']), dict(name='Orlando MX v055 — matched dirt, detailed soil and smooth table-single landing',
         body=body, draft=False, prerelease=True, make_latest='false'), method='PATCH')
    assets = api('/releases/' + str(rel['id']))['assets']
    asset = next(a for a in assets if a['name'] == p.name)
    assert asset['size'] == q['pkz_bytes'] and asset['digest'] == 'sha256:' + q['pkz_sha256']
    save(R / 'BUILD/v055_delivery.json', dict(release_url=rel['html_url'], download_url=asset['browser_download_url'],
         release_id=rel['id'], pkz_sha256=q['pkz_sha256'], pkz_bytes=q['pkz_bytes']))
    print('V055_DOWNLOAD', asset['browser_download_url'], flush=True)


if __name__ == '__main__':
    {'checkpoint': checkpoint, 'deliver': deliver}[sys.argv[1]]()
