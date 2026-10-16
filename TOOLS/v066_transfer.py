"""Preserve checked v066 source, then publish only a validated native package."""
import argparse
import os
import zipfile
from v052_transfer import api, identity, upload
from v066_lighting import R, O, S, BASE_BUILD, NAME, DEST, read, save, sha


def release():
    result = api('/releases/' + os.environ['V066_RELEASE_ID'])
    assert result['draft'] and result['tag_name'].startswith('v066-cinematic-lighting-')
    return result


def checkpoint():
    identity()
    for name in ['precompile_validation', 'native_staging_validation']:
        assert read(O / (name + '.json'))['checks_pass']
    archive = R / 'BUILD/OrlandoMX-v066-source-checkpoint.zip'
    temporary = archive.with_suffix('.writing.zip')
    written = set()
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        def add(path, name=None):
            name = name or path.relative_to(R).as_posix()
            if name not in written:
                bundle.write(path, name)
                written.add(name)
        for directory in [O, S, DEST]:
            for path in sorted(directory.rglob('*')):
                if path.is_file():
                    add(path)
        for path in sorted((R / 'TOOLS').glob('*v066*.py')):
            add(path)
        for name in ['v054_track.tht', 'edf_params.ini', 'trh_params.ini', 'tool_versions.json']:
            add(BASE_BUILD / name, 'BUILD/' + name)
        add(R / 'BUILD/v066_recovered_inputs.json')
        for name in ['track.tht', 'map_params.ini']:
            add(R / 'BUILD/v066_stage' / name)
    with zipfile.ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
    temporary.replace(archive)
    descriptor = R / 'BUILD/v066_checkpoint_descriptor.json'
    save(descriptor, dict(version='v066', source_commit=os.environ['GITHUB_SHA'],
         source_run=int(os.environ['GITHUB_RUN_ID']), file=archive.name,
         bytes=archive.stat().st_size, sha256=sha(archive),
         inputs=read(S / 'native_expected_inputs.json'), lighting=read(S / 'lighting_spec.json'),
         checked_source=True, all_active_materials_and_scenery_textures_included=True))
    result = api('/releases', dict(
        tag_name='v066-cinematic-lighting-' + os.environ['GITHUB_RUN_ID'],
        target_commitish=os.environ['GITHUB_SHA'], draft=True, prerelease=True, make_latest='false',
        name='Orlando MX v066 - cinematic daylight test; native build pending',
        body='Lighting-only comparison against v065. A matched 28-degree sun, warmer direct light, '
             'balanced cool fill and reduced clear-weather haze. All terrain, approved B/C materials, '
             'start grass clearance, scenery and race data are retained. No new texture allocation '
             'or higher-resolution shadow maps. Native compilation and validation pending.'))
    for path in [archive, descriptor, S / 'lighting_spec.json', S / 'native_expected_inputs.json',
                 O / 'precompile_validation.json', O / 'native_staging_validation.json']:
        upload(result, path)
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
        stream.write('V066_RELEASE_ID=' + str(result['id']) + '\n')
    print('V066_SOURCE_CHECKPOINT_SAVED', result['id'], flush=True)


def preserve_native():
    result = release()
    for path in [R / '12_RELEASE/OrlandoMX_2026_v066.pkz',
                 R / '12_RELEASE/OrlandoMX_2026_v066.pkz.sha256', O / 'native_compile_results.json']:
        upload(result, path)


def deliver():
    identity()
    report = read(R / '12_RELEASE/OrlandoMX_v066_Validation.json')
    for key in ['compiled', 'source_checks', 'centerline_merged', 'native_collision_exact_v065',
                'wall_roller_visual_collision_exact', 'all_source_scenery_and_textures_exact_v065',
                'all_race_data_exact_v065', 'baked_runtime_lighting_synchronized',
                'source_texture_and_geometry_allocation_unchanged', 'native_shadow_quality_exact_v065',
                'package_integrity_passed', 'package_size_budget_passed']:
        assert report[key], key
    assert report['native_object_textures']['checks_pass'] and report['native_height_validation']['checks_pass']
    assert all(item['checks_pass'] for item in report['source_validation'].values())
    path = R / '12_RELEASE/OrlandoMX_2026_v066.pkz'
    assert sha(path) == report['pkz_sha256']
    result = release()
    assert result['target_commitish'] == report['source_commit']
    for name in ['OrlandoMX_v066_Validation.json', 'Install_v066.txt']:
        upload(result, R / '12_RELEASE' / name)
    for name in ['native_height_validation.json', 'native_staging_validation.json', 'precompile_validation.json']:
        upload(result, O / name)
    body = f'''Native MX Bikes lighting test inspired by the v065 cinematic renders.

Clear-weather sunlight is lowered from about 54 to 28 degrees and turned toward the cinematic key direction. Warm direct light, balanced cool ambient fill and reduced distance haze target clearer dirt, berms, jump faces and vehicle shading. TerrainEd's baked shadow direction and the runtime sun position are identical.

All v065 terrain heights, B corners, C course and start surfaces, cleared start grass, low wall-entry roller, vehicles, candy sign, Pup memorial, crocodile and race/reset data are retained. Every active terrain bitmap and shader, the native scenery EDF, texture dimensions and 14 terrain layers are exact. No new images, scene geometry, shadow resolution or shadow sampling were added.

Official TerrainEd compilation and TrackEd route merge passed. All 4,198,401 native visual and collision samples match v065. Native bitmap payloads, scenery probes, matte foliage, race-file hashes and PKZ CRC passed. Package: {report['pkz_bytes']:,} bytes.

Keep v065 for comparison. Select v066 in CLEAR weather with the same game graphics settings and shadows enabled. All players need the same PKZ. This is not Blender rendering or a ReShade preset; actual game appearance, riding, RAM/VRAM and FPS require the user's test.'''
    result = api('/releases/' + str(result['id']), dict(
        name='Orlando MX v066 - cinematic daylight test', body=body, draft=False,
        prerelease=True, make_latest='false'), method='PATCH')
    asset = next(item for item in api('/releases/' + str(result['id']))['assets'] if item['name'] == path.name)
    assert asset['size'] == report['pkz_bytes'] and asset['digest'] == 'sha256:' + report['pkz_sha256']
    save(R / 'BUILD/v066_delivery.json', dict(release_url=result['html_url'], download_url=asset['browser_download_url'],
         release_id=result['id'], pkz_sha256=report['pkz_sha256'], pkz_bytes=report['pkz_bytes'],
         source_commit=report['source_commit']))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write('[Download validated v066 PKZ](' + asset['browser_download_url'] + ')\n\n'
                         '[Validation and install notes](' + result['html_url'] + ')\n')
    print('V066_DOWNLOAD', asset['browser_download_url'], flush=True)


def diagnostics():
    if not os.environ.get('V066_RELEASE_ID'):
        return
    target = R / 'BUILD' / ('v066-diagnostics-' + os.environ['GITHUB_RUN_ID'] + '.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as bundle:
        paths = [*sorted(O.glob('*validation.json')), *sorted((R / 'DOCUMENTATION').glob('*v066*.log')),
                 *sorted((R / 'DOCUMENTATION').glob('*v066*.json'))]
        for path in paths:
            if path.is_file():
                bundle.write(path, path.relative_to(R).as_posix())
    upload(release(), target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['checkpoint', 'deliver', 'diagnostics'])
    {'checkpoint': checkpoint, 'deliver': deliver, 'diagnostics': diagnostics}[parser.parse_args().action]()
