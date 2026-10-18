"""Recover v002 from its immutable authored inputs; checkpoint native stages."""
from pathlib import Path
import argparse, configparser, hashlib, json, os, struct, zipfile
import numpy as np
import native_test as n

SOURCE_RUN = 39070771277
SOURCE_COMMIT = '58a4fe9992c9b78c53d6520f063c260e1d00e9e6'
INPUT_SHA = '8c03f41723ea2511a31201f60ad35e94c182d8380d2bec6c2b59716158d0984c'
ASSET_FILES = {
    'sky': ['MOON/build/game/moon_sky.edf'],
    'scenery': ['MOON/build/scenery.edf'],
    'collision': ['MOON/build/game/'+n.NAME+'.trh'],
}
PACKAGE_FILES = {
    'map-test': ['MOON/Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz',
                 'MOON/Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz.sha256',
                 'MOON/Moon_v002_Diagnostic_Validation.json'],
    'map': ['MOON/Taurus_Littrow_MX_v002.pkz', 'MOON/Taurus_Littrow_MX_v002.pkz.sha256',
            'MOON/Moon_v002_Validation.json', 'MOON/Moon_v002_Previews.zip'],
}
CHECKPOINT_FILES = ASSET_FILES | PACKAGE_FILES

def context():
    return dict(schema=1, source_archive_sha256=INPUT_SHA,
                authored_source_commit=SOURCE_COMMIT,
                compiler_commit=os.environ.get('GITHUB_SHA', 'local'),
                run_id=os.environ.get('GITHUB_RUN_ID', 'local'))

def checkpoint(stage, paths, details):
    paths = sorted(set(paths))
    assert set(paths) == set(CHECKPOINT_FILES[stage]), ('Unexpected checkpoint files', stage)
    files = {}
    for name in paths:
        path = n.R/name
        assert path.is_file(), name
        files[name] = dict(sha256=n.sha(path), bytes=path.stat().st_size)
    manifest = context() | dict(stage=stage, files=files, details=details)
    folder = n.M/'recovery_checkpoints'; folder.mkdir(exist_ok=True)
    dest = folder/(stage+'.zip')
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
        for name in paths: z.write(n.R/name, name)
    with zipfile.ZipFile(dest) as z: assert z.testzip() is None
    n.save(folder/(stage+'_manifest.json'), manifest)
    print('MOON_CHECKPOINT_SAVED', stage, dest.stat().st_size, n.sha(dest), flush=True)
    return dest

def restore(stage):
    path = n.M/'checkpoint_downloads'/(stage+'.zip')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, ('Bad checkpoint CRC', stage)
        manifest = json.loads(z.read('manifest.json'))
        for key, value in context().items():
            assert manifest[key] == value, ('Checkpoint provenance mismatch', stage, key)
        assert manifest['stage'] == stage
        assert set(manifest['files']) == set(CHECKPOINT_FILES[stage]), ('Unexpected restored files', stage)
        assert set(z.namelist()) == set(manifest['files']) | {'manifest.json'}
        # Validate every byte before writing anything into the working tree.
        for name, expected in manifest['files'].items():
            p = Path(name)
            assert not p.is_absolute() and '..' not in p.parts and name.startswith('MOON/')
            data = z.read(name)
            assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'], ('Checkpoint file mismatch', name)
        for name in manifest['files']:
            p = n.R/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(z.read(name))
    n.B.mkdir(exist_ok=True)
    n.save(n.B/('recovered_'+stage+'.json'), manifest)
    print('MOON_CHECKPOINT_RESTORED', stage, flush=True)
    return manifest

def unpack():
    archive = n.R/'Moon_v002_Native_Inputs.zip'
    assert n.sha(archive) == INPUT_SHA, 'Authored-input hash mismatch'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():
            p = Path(name)
            assert not p.is_absolute() and '..' not in p.parts
            assert name.startswith(('MOON/build/', 'MOON/previews_v002/'))
        z.extractall(n.R)
    n.save(n.M/'recovery_source.json', context() | dict(source_run=SOURCE_RUN))
    print('MOON_SOURCE_CHECKPOINT_VERIFIED', INPUT_SHA, flush=True)

def bake_params(original, shadows):
    cfg = configparser.ConfigParser(); cfg.read_string(original)
    p = cfg['params']
    p['shadowvolumes_create'] = '0'
    p['shadowmaps_create'] = '1' if shadows else '0'
    p['shadowmaps_scale'] = '0.2'
    p['shadowmaps_supersampling'] = '1'
    p['shadowmaps_terraincast'] = '1'
    from io import StringIO
    out = StringIO(); cfg.write(out)
    return out.getvalue()

def collision_check(path):
    expected = np.fromfile(n.B/'terrain.raw', '<u2').reshape(2049, 2049)
    with path.open('rb') as f:
        assert f.read(4) == b'TRH\0' and struct.unpack('<2I', f.read(8)) == (2049, 2049)
    encoded = np.memmap(path, mode='r', dtype='<u2', offset=12, shape=(2049, 2049))
    got = ((encoded.astype(np.uint32)-32768) & 65535).astype('<u2')[::-1]
    assert np.array_equal(got, expected)
    return dict(checks_pass=True, samples=expected.size)

def assets(stage):
    assert os.name == 'nt', 'Official tools require Windows'
    source, scene = n.preflight(); edf, terrain, tracked = n.tools()
    if stage == 'sky':
        result = n.run(edf, ['moon_sky.fbx', n.G/'moon_sky.edf', 'edf_params.ini', '-q'], 'moon_sky', 300)
        assert (n.G/'moon_sky.edf').read_bytes()[:4] == b'EDF\0'
    elif stage == 'scenery':
        result = n.run(edf, ['scenery.fbx', 'scenery.edf', 'edf_params.ini', '-q'], 'moon_scenery', 3600)
        path = n.B/'scenery.edf'; assert path.read_bytes()[:4] == b'EDF\0'
        import mmap
        with path.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
            errors = n.scan_points(data, scene['native_probe_local_xyz_m'], tolerance=.001)
        assert len(errors) >= 6 and all(e is not None for e in errors), ('EDF coordinate mismatch', errors)
        result['native_coordinate_probes'] = len(errors)
    elif stage == 'collision':
        path = n.G/(n.NAME+'.trh')
        result = dict(collision=n.run(terrain, ['track.tht', path, 'trh_params.ini'], 'moon_collision', 300))
        before = n.sha(path)
        result['centerline'] = n.run(tracked, ['-merge', path, 'cl', n.B/'main.tcl'], 'moon_route_merge', 300)
        assert n.sha(path) != before, 'Centerline did not alter TRH'
        result['collision_grid'] = collision_check(path)
        result['centerline_merged'] = True
    else: raise ValueError(stage)
    checkpoint(stage, ASSET_FILES[stage], result)

def graphics(diagnostic):
    assert os.name == 'nt', 'Official tools require Windows'
    manifests = {stage: restore(stage) for stage in ASSET_FILES}
    source, scene = n.preflight(); _, terrain, _ = n.tools()
    original = (n.B/'map_params.ini').read_text()
    params = bake_params(original, shadows=not diagnostic)
    name = 'map-test' if diagnostic else 'map'
    profile = dict(name='diagnostic-no-baked-shadows' if diagnostic else 'balanced-baked-shadows',
                   shadowmaps=not diagnostic, scale=.2, supersampling=1, terrain_self_shadow=True,
                   authored_source_commit=SOURCE_COMMIT, source_archive_sha256=INPUT_SHA)
    (n.B/'recovery_map_params.ini').write_text(params)
    mp = n.G/(n.NAME+'.map'); mp.unlink(missing_ok=True)
    results = {stage: m['details'] for stage, m in manifests.items()}
    results['graphics'] = n.run(terrain, ['track.hmf', mp, 'recovery_map_params.ini'], 'moon_terrain_'+name,
                                1200 if diagnostic else 5400)
    report = n.validate_package(source, scene, results, bake_profile=profile, diagnostic=diagnostic)
    # Preview archive travels with the completed package, so publication can be
    # retried separately without rerunning any native authoring tool.
    if not diagnostic:
        previews = n.M/'Moon_v002_Previews.zip'
        with zipfile.ZipFile(previews, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted((n.M/'previews_v002').iterdir()):
                if p.is_file(): z.write(p, p.name)
    checkpoint(name, PACKAGE_FILES[name], dict(checks_pass=report['checks_pass'], bake_profile=profile,
                                  native_height_validation=report['native_height_validation']))

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=['unpack', 'sky', 'scenery', 'collision', 'map-test', 'map', 'publish-restore'])
    stage = parser.parse_args().stage
    if stage == 'unpack': unpack()
    elif stage == 'publish-restore':
        m = restore('map'); assert m['details']['checks_pass'] and m['details']['bake_profile']['shadowmaps']
    elif stage in ASSET_FILES: assets(stage)
    else: graphics(stage == 'map-test')

if __name__ == '__main__': main()
