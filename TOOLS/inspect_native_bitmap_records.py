"""Inspect saved native v044 texture records without invoking any compiler."""
import json, mmap, shutil, struct, subprocess, sys, zipfile
from pathlib import Path
from v044_common import R, O, F, NAME, read, save, sha, atomic
from v044_source import api, download, blob
from v044_release_transfer import restore
from validate_native_textures_v024 import bitmap_signature, texture_record

RELEASE_ID = 411058375
CANDIDATE_NAME = 'v044-native-candidate-38319134828.zip'
CANDIDATE_BYTES = 843801281
CANDIDATE_SHA256 = 'd67e66e3f233a8148dffa3ba1ca25ef08f05c4f535de3529bda9c700c527d37b'
NATIVE_COMMIT = 'ded4ea2bbe08bdbabe11f3436560b1df8a921744'
PKZ_SHA256 = '899fb2e574fc1e0063dc001f6e2be96076b82e7d793a929f28b42fe42d3f59b0'

def restore_source():
    """Authenticate Windows text with platform line endings normalized for comparison."""
    release = api('/releases/' + str(RELEASE_ID))
    assert api('')['private'] and release['draft'] and release['target_commitish'] == NATIVE_COMMIT
    assets = {a['name']: a for a in release['assets']}
    source = assets['OrlandoMX-v044-source-checkpoint.zip']
    descriptor = assets['v044_checkpoint_descriptor.json']
    assert source['size'] == 1599713927
    assert source['digest'] == 'sha256:1c45844424b0f8e9384a9344f0563b6f108e5003f699c71430dc499166bff881'
    assert descriptor['digest'] == 'sha256:38b29297ea5bd495a3299419da1f44a7ebf381e28a76d2e95e5a6bf6b891ca83'
    download(descriptor, R / 'BUILD/v044_checkpoint_descriptor.json')
    checkpoint = R / 'BUILD/OrlandoMX-v044-source-checkpoint.zip'
    download(source, checkpoint)
    with zipfile.ZipFile(checkpoint) as archive:
        for name in ['V044_SOURCE/visual_spec.json', 'TOOLS/build_v044.py', 'TOOLS/v044_assets.py', 'TOOLS/v044_scenery.py', 'TOOLS/v044_surface_detail.py']:
            assert archive.read(name).replace(b'\r\n', b'\n') == (R / name).read_bytes().replace(b'\r\n', b'\n'), ('Authored source changed', name)
    restore()
    print('Authored source authenticated with Windows/Linux text line endings normalized.', flush=True)

def restore_candidate():
    release = api('/releases/' + str(RELEASE_ID))
    assert api('')['private'] and release['draft']
    assert release['target_commitish'] == NATIVE_COMMIT
    asset = next(a for a in release['assets'] if a['name'] == CANDIDATE_NAME)
    assert asset['size'] == CANDIDATE_BYTES
    assert asset['digest'] == 'sha256:' + CANDIDATE_SHA256
    checkpoint = R / 'BUILD' / CANDIDATE_NAME
    download(asset, checkpoint)
    with zipfile.ZipFile(checkpoint) as archive:
        assert archive.testzip() is None
        for item in archive.infolist():
            path = Path(item.filename)
            assert not path.is_absolute() and '..' not in path.parts
            assert item.filename.startswith(('12_RELEASE/', 'BUILD/v009_work/08_OBJECTS_GAME/', 'V044_OUTPUT/', 'DOCUMENTATION/'))
            if not item.is_dir():
                atomic(R / item.filename, archive.read(item))
    checkpoint.unlink()
    pkz = R / '12_RELEASE/OrlandoMX_2026_v044.pkz'
    assert pkz.stat().st_size == 610018083 and sha(pkz) == PKZ_SHA256
    with zipfile.ZipFile(pkz) as archive:
        assert archive.testzip() is None and len(archive.namelist()) == 13
        for item in archive.infolist():
            path = Path(item.filename)
            assert not path.is_absolute() and '..' not in path.parts
            assert item.filename.startswith(NAME + '/')
            atomic(R / '12_RELEASE' / item.filename, archive.read(item))
    manifest = read(R / 'DOCUMENTATION/native_build_validation.json')
    assert manifest['compiled'] and manifest['centerline_merged']
    for name, details in manifest['outputs'].items():
        path = R / '12_RELEASE' / NAME / name
        assert path.stat().st_size == details['bytes'] and sha(path) == details['sha256'], name
    print('Saved native EDF, MAP, TRH and PKZ authenticated; no compilation requested.', flush=True)

def texture_paths():
    manifest = read(O / 'v044_staging_validation.json')
    assert manifest['checks_pass'] and manifest['all_texture_references_resolved']
    root = R / 'BUILD/v009_work/07_OBJECTS_SOURCE/scenery.fbm'
    paths = []
    for record in manifest['active_scenery_textures']:
        name = record['file']
        candidates = [F / name, root / name, R / 'BUILD/v009_work/04_TEXTURES' / name,
                      R / 'BUILD/v009_work/05_NORMALS' / name, R / record['source']]
        path = next((p for p in candidates if p.is_file() and sha(p) == record['sha256']), None)
        if path is None:
            candidates += [p for p in (R / 'BUILD/v009_work').rglob(name) if p.is_file()]
            path = next((p for p in candidates if p.is_file() and sha(p) == record['sha256']), None)
        if path is None:
            print('SOURCE_TEXTURE_RESOLUTION ' + json.dumps(dict(texture=name, expected_sha256=record['sha256'],
                  candidates=[dict(path=p.relative_to(R).as_posix(), sha256=sha(p), bitmap_signature=[*bitmap_signature(p)[:2], bitmap_signature(p)[2].hex()])
                              for p in candidates if p.is_file()])), flush=True)
        assert path is not None, ('Staged texture cannot be reproduced exactly', name, candidates)
        paths.append(path)
    return paths

def inspect():
    restore_source()
    subprocess.run([sys.executable, str(R / 'TOOLS/materialize_v009_baseline.py')], cwd=R, check=True)
    restore_candidate()
    paths = texture_paths()
    result = {'native_source_commit': NATIVE_COMMIT, 'candidate_sha256': CANDIDATE_SHA256,
              'pkz_sha256': PKZ_SHA256, 'compiler_invoked': False, 'textures': []}
    edf = R / 'BUILD/v009_work/08_OBJECTS_GAME/scenery.edf'
    mapfile = R / '12_RELEASE' / NAME / (NAME + '.map')
    with edf.open('rb') as ef, mapfile.open('rb') as mf:
        with mmap.mmap(ef.fileno(), 0, access=mmap.ACCESS_READ) as eb, mmap.mmap(mf.fileno(), 0, access=mmap.ACCESS_READ) as mb:
            assert eb[:4] == b'EDF\0' and mb[:2] == b'MP'
            result['edf_bytes'] = len(eb)
            result['map_bytes'] = len(mb)
            for path in paths:
                w, h, digest = bitmap_signature(path)
                signature = struct.pack('<2I', w, h) + digest
                row = dict(texture=path.name, source_sha256=sha(path), width=w, height=h,
                           pixel_md5=digest.hex(), edf_signature_offset=eb.find(signature), map_signature_offset=mb.find(signature))
                key = path.stem.encode('ascii') + bytes(100 - len(path.stem))
                pos = eb.find(key)
                row['name_records'] = []
                while pos >= 0 and len(row['name_records']) < 4:
                    row['name_records'].append(dict(offset=pos, next_96_bytes_hex=eb[pos+100:pos+196].hex(),
                                                   next_20_uint32=list(struct.unpack('<20I', eb[pos+100:pos+180]))))
                    pos = eb.find(key, pos + 1)
                try:
                    row['existing_reader'] = texture_record(eb, path)
                    row['existing_reader_passed'] = True
                except (RuntimeError, ValueError) as error:
                    row['existing_reader_passed'] = False
                    row['existing_reader_error'] = str(error)
                    offset = row['edf_signature_offset']
                    if offset >= 0:
                        row['signature_context_offset'] = max(0, offset - 112)
                        row['signature_context_hex'] = eb[max(0, offset-112):offset+96].hex()
                result['textures'].append(row)
                print('TEXTURE_DIAGNOSTIC ' + json.dumps(row), flush=True)
    result['reader_failure_count'] = sum(not t['existing_reader_passed'] for t in result['textures'])
    result['missing_exact_pixel_signatures'] = [t['texture'] for t in result['textures'] if t['edf_signature_offset'] < 0 or t['map_signature_offset'] < 0]
    output = R / 'DOCUMENTATION/v044_native_texture_record_diagnostics.json'
    save(output, result)
    print('CODEX_V044_BITMAP_DIAGNOSTIC_BLOB ' + blob(json.dumps(result)), flush=True)
    print('Reader failures:', result['reader_failure_count'], 'missing exact pixel signatures:', result['missing_exact_pixel_signatures'], flush=True)

if __name__ == '__main__':
    inspect()
