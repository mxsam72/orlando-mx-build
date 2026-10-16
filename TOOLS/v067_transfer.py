"""Checkpoint authenticated v067 source, then publish only fully validated native PKZ."""
import argparse
import os
import zipfile
from pathlib import Path
from v052_transfer import api, identity, upload
from native_base_v067 import R, O, S, BASE_BUILD, NAME, DEST, read, save, sha

TAG_PREFIX = 'v067-approved-dirt-daylight-'


def release():
    result = api('/releases/' + os.environ['V067_RELEASE_ID'])
    assert result['draft'] and result['tag_name'].startswith(TAG_PREFIX)
    return result


def checkpoint():
    identity()
    for name in ['precompile_validation', 'surface_validation', 'native_staging_validation', 'race_validation']:
        assert read(O / (name + '.json'))['checks_pass'], name
    assert read(S / 'native_build_authorization.json')['native_compilation_authorized']
    archive = R / 'BUILD/OrlandoMX-v067-source-checkpoint.zip'
    temporary = archive.with_suffix('.writing.zip')
    entries = set()
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        def add(path, name=None):
            name = name or path.relative_to(R).as_posix()
            if name not in entries:
                bundle.write(path, name)
                entries.add(name)
        for folder in [O, S, DEST]:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    add(p)
        for path in sorted((R / 'TOOLS').glob('*v067*.py')):
            add(path)
        for path in ['v066_lighting.py','v067_surface.py']:
            add(R / 'TOOLS' / path)
        for name in ['v054_track.tht','edf_params.ini','trh_params.ini','tool_versions.json']:
            add(BASE_BUILD / name, 'BUILD/' + name)
        for name in ['track.tht','map_params.ini']:
            add(R / 'BUILD/v067_stage' / name)
        add(R / 'BUILD/v067_pinned_expected.json')
        add(R / 'BUILD/v066_recovered_inputs.json')
    with zipfile.ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
    temporary.replace(archive)
    descriptor = R / 'BUILD/v067_checkpoint_descriptor.json'
    save(descriptor, dict(version='v067',source_commit=os.environ['GITHUB_SHA'],
         source_run=int(os.environ['GITHUB_RUN_ID']),file=archive.name,
         bytes=archive.stat().st_size, sha256=sha(archive),
         inputs=read(S/'native_expected_inputs.json'),
         lighting=read(S/'visual_spec.json'),source_checks=True,
         native_compilation_authorized=True))
    info = api('/releases',dict(
        tag_name=TAG_PREFIX + os.environ['GITHUB_RUN_ID'],
        target_commitish=os.environ['GITHUB_SHA'],draft=True,prerelease=True,make_latest='false',
        name='Orlando MX v067 - approved dirt and 11 a.m. lighting (build pending)',
        body='User-approved native MX Bikes build based on v066. Six terrain material maps are '
             'updated, with a 45-degree late-morning sunlight and synchronized baked shadows. '
             'Existing geometry, B corners, C course, start dirt and grass masks, vehicles, '
             'memorial, crocodile, race data and shadow resolution remain unchanged. Native validation pending.'))
    for path in [archive,descriptor,S/'visual_spec.json',S/'native_expected_inputs.json',
                 S/'native_build_authorization.json',O/'precompile_validation.json',
                 O/'native_staging_validation.json']:
        upload(info,path)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as stream:
        stream.write('V067_RELEASE_ID=' + str(info['id']) + '\n')
    print('V067_SOURCE_CHECKPOINT_SAVED',info['id'],flush=True)


def preserve_native():
    info = release()
    for path in [R/'12_RELEASE/OrlandoMX_2026_v067.pkz',
                 R/'12_RELEASE/OrlandoMX_2026_v067.pkz.sha256',
                 O/'native_compile_results.json']:
        upload(info,path)


def deliver():
    identity()
    report=read(R/'12_RELEASE/OrlandoMX_v067_Validation.json')
    for field in ['compiled','source_checks','centerline_merged','native_collision_exact_v065',
                  'wall_roller_visual_collision_exact','v066_scenery_exact_and_v067_textures_hash_verified',
                  'all_race_data_exact_v065','baked_runtime_lighting_synchronized',
                  'source_texture_and_geometry_allocation_unchanged','native_shadow_quality_exact_v065',
                  'package_integrity_passed','package_size_budget_passed']:
        assert report[field],field
    assert report['native_object_textures']['checks_pass']
    assert report['native_height_validation']['checks_pass']
    assert all(row['checks_pass'] for row in report['source_validation'].values())
    path=R/'12_RELEASE/OrlandoMX_2026_v067.pkz'
    assert sha(path)==report['pkz_sha256']
    info=release()
    assert info['target_commitish']==report['source_commit']
    for name in ['OrlandoMX_v067_Validation.json','Install_v067.txt']:
        upload(info,R/'12_RELEASE'/name)
    for name in ['native_height_validation.json','native_staging_validation.json',
                 'precompile_validation.json']:
        upload(info,O/name)
    body = ('Native v067 is built and validated. This is the approved material-and-lighting update '
            'relative to v066, with dirt aggregate contrast, revised packed/loose/track normals, '
            'and synchronized approximately 11 a.m. daylight (45-degree sun). '
            'The accepted B corners, C dirt elsewhere and at the start, all track geometry, '
            'track masks, vehicles, Pup memorial, crocodile, pit scenery, collision and race '
            'data are preserved. No new material layers, textures or geometry added. '
            'TerrainEd native compiled and TrackEd route merge passed. '
            'All 4,198,401 visual/collision grid samples were validated. '
            'Native material payload, native scenery probes and ZIP checksum passed. '
            f'PKZ size: {report["pkz_bytes"]:,} bytes. '
            'Compare against v066 under CLEAR weather with identical in-game graphics '
            'settings. Blender preview shading does not establish identical in-game results; '
            'rideability, rendering quality and FPS still need user testing.')
    info = api('/releases/' + str(info['id']),dict(
        name='Orlando MX v067 - approved dirt and 11 a.m. lighting',
        body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
    asset = next(a for a in api('/releases/' + str(info['id']))['assets'] if a['name'] == path.name)
    assert asset['size']==report['pkz_bytes'] and asset['digest']=='sha256:'+report['pkz_sha256']
    save(R/'BUILD/v067_delivery.json',dict(release_url=info['html_url'],
         download_url=asset['browser_download_url'],release_id=info['id'],
         pkz_sha256=report['pkz_sha256'],pkz_bytes=report['pkz_bytes'],
         source_commit=report['source_commit']))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:
            stream.write('[Download validated v067 PKZ](' + asset['browser_download_url'] + ')\n\n' +
                         '[Validation details and installation](' + info['html_url'] + ')\n')
    print('V067_DOWNLOAD',asset['browser_download_url'],flush=True)


def diagnostics():
    if not os.environ.get('V067_RELEASE_ID'):
        return
    path=R/'BUILD'/('v067-diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as bundle:
        paths=[*sorted(O.glob('*validation.json')),
               *sorted((R/'DOCUMENTATION').glob('*v067*.log')),
               *sorted((R/'DOCUMENTATION').glob('*v067*.json'))]
        for item in paths:
            if item.is_file():
                bundle.write(item,item.relative_to(R).as_posix())
    upload(release(),path)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['checkpoint','deliver','diagnostics'])
    {'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[parser.parse_args().action]()
