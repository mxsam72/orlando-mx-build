"""Reuse authenticated v002 outputs and limit shadow receiving to nearby scenery."""
from pathlib import Path
import argparse, configparser, hashlib, io, json, os, shutil, struct, zipfile
import native_recovery as recovery

n = recovery.n
BASE_RUN = '39121779597'
BASE_COMMIT = '6e4f8fae94e913ae29b452c73fa456c38e09a3a1'
BASE_CONTEXT = dict(schema=1, source_archive_sha256=recovery.INPUT_SHA,
                    authored_source_commit=recovery.SOURCE_COMMIT,
                    compiler_commit=BASE_COMMIT, run_id=BASE_RUN)
ORIGINAL_FBX_SHA = '62df81212586989c9783ce788d268437334c5e348ceb5e125c8c654d355e4430'
LOCALIZED_FBX_SHA = 'cd951a4702ab9d74e1010d42ec4145ae2e163fd26fc46076185f18a532aa5dd1'
DIAGNOSTIC_SHA = 'd0f38fc0cc7b9a3ca789b3c50af84b5bcf7bd2dfb106b394e66bce35c30559a1'
LOCALIZED_FILES = ['MOON/build/scenery.edf', 'MOON/build/localized_scenery_derivation.json']
recovery.CHECKPOINT_FILES['scenery-localized'] = LOCALIZED_FILES


def restore_base(stage):
    assert stage in recovery.ASSET_FILES or stage == 'map-test'
    manifest = recovery.restore(stage, expected_context=BASE_CONTEXT)
    if stage == 'map-test':
        assert n.sha(n.M/'Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz') == DIAGNOSTIC_SHA
        report = json.loads((n.M/'Moon_v002_Diagnostic_Validation.json').read_text())
        assert report['source_commit'] == BASE_COMMIT and str(report['run_id']) == BASE_RUN
        assert report['compiled'] and report['checks_pass'] and report['diagnostic_only']
        assert report['native_height_validation']['checks_pass'] and report['bake_profile']['shadowmaps'] is False
    return manifest


def rename_distant_receivers(data):
    """Edit only FBX object-name string properties; keep all other bytes exact."""
    assert data[:23] == b'Kaydara FBX Binary  \x00\x1a\x00'
    assert struct.unpack_from('<I', data, 23)[0] == 7400
    result = bytearray(data); edits = []; counts = {'Geometry': 0, 'Model': 0}
    header_size = struct.calcsize('<IIIB')

    def walk(at, limit, parents=()):
        while at + header_size <= limit:
            end, count, size, length = struct.unpack_from('<IIIB', data, at)
            if not end:
                assert data[at:at+header_size] == bytes(header_size)
                return
            assert at + header_size + length + size <= end <= limit, 'Invalid FBX node range'
            node = data[at+header_size:at+header_size+length]
            prop = at + header_size + length; children = prop + size
            if parents == (b'Objects',) and node in (b'Model', b'Geometry'):
                assert count == 3 and data[prop:prop+1] == b'L'
                prop += 9
                assert data[prop:prop+1] == b'S'; prop += 1
                text_length = struct.unpack_from('<I', data, prop)[0]; prop += 4
                assert prop + text_length <= children
                value = data[prop:prop+text_length]
                if value.startswith(b'SHAD_massif_patch_'):
                    name = value.split(b'\x00\x01')[0].decode('ascii')
                    assert name in {f'SHAD_massif_patch_{r}_{c}' for r in (0,75,150,225) for c in (0,75,150,225)}
                    result[prop:prop+5] = b'VIEW_'
                    edits.append(dict(kind=node.decode(), offset=prop, original=name,
                                      replacement='VIEW_'+name[5:]))
                    counts[node.decode()] += 1
            walk(children, end, parents+(node,))
            at = end

    walk(27, len(data))
    assert counts == {'Geometry': 16, 'Model': 16}, counts
    assert len({(e['kind'], e['original']) for e in edits}) == 32
    reverted = bytearray(result)
    for edit in edits: reverted[edit['offset']:edit['offset']+5] = b'SHAD_'
    assert bytes(reverted) == data, 'A non-name FBX byte changed'
    assert sum(a != b for a,b in zip(data,result)) == 128
    return bytes(result), edits


def derive_scenery():
    source = n.B/'scenery.fbx'
    assert n.sha(source) == ORIGINAL_FBX_SHA
    derived, edits = rename_distant_receivers(source.read_bytes())
    assert hashlib.sha256(derived).hexdigest() == LOCALIZED_FBX_SHA
    dest = n.B/'scenery_localized.fbx'; dest.write_bytes(derived)
    report = dict(original_fbx_sha256=ORIGINAL_FBX_SHA, derived_fbx_sha256=LOCALIZED_FBX_SHA,
                  geometry_material_texture_transform_bytes_unchanged=True,
                  changed_bytes=128, changed_names=edits,
                  far_shadow_receivers=False, near_and_clast_receivers_retained=True)
    return dest, report


def localized_scenery():
    assert os.name == 'nt', 'Official tools require Windows'
    _, scene = n.preflight(); edf, _, _ = n.tools()
    derived, report = derive_scenery()
    shutil.copytree(n.B/'scenery.fbm', n.B/'scenery_localized.fbm', dirs_exist_ok=True)
    dest = n.B/'scenery.edf'; dest.unlink(missing_ok=True)
    result = n.run(edf, [derived.name, dest, 'edf_params.ini', '-q'], 'moon_scenery_localized', 2700)
    assert dest.read_bytes()[:4] == b'EDF\0'
    import mmap
    with dest.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
        errors = n.scan_points(data, scene['native_probe_local_xyz_m'], tolerance=.001)
        assert all(e is not None for e in errors) and len(errors) == 16
        for edit in report['changed_names']:
            if edit['kind'] == 'Model': assert edit['replacement'].encode()+b'\x00' in data
        assert b'SHAD_measured_near\x00' in data and b'SHAD_illustrative_clasts\x00' in data
        assert b'SHAD_massif_patch_' not in data
    report['native_edf_sha256'] = n.sha(dest)
    n.save(n.B/'localized_scenery_derivation.json', report)
    recovery.checkpoint('scenery-localized', LOCALIZED_FILES,
                        dict(native_compile=result, derivation=report, native_coordinate_probes=len(errors)))


def write_params(terrain_cast, scale):
    cfg = configparser.ConfigParser(); cfg.read(n.B/'map_params.ini')
    cfg['params'].update(shadowvolumes_create='0', shadowmaps_create='1',
                         shadowmaps_scale=str(scale), shadowmaps_supersampling='1',
                         shadowmaps_terraincast='1' if terrain_cast else '0')
    text = io.StringIO(); cfg.write(text)
    dest = n.B/'lighting_map_params.ini'; dest.write_text(text.getvalue())
    return dest


def graphics(localized):
    assert os.name == 'nt', 'Official tools require Windows'
    stages = ['sky', 'collision'] + ([] if localized else ['scenery'])
    manifests = {stage: restore_base(stage) for stage in stages}
    if localized:
        manifests['scenery-localized'] = recovery.restore('scenery-localized')
        _, expected = derive_scenery()
        got = json.loads((n.B/'localized_scenery_derivation.json').read_text())
        assert all(got[k] == value for k,value in expected.items())
        assert got['native_edf_sha256'] == n.sha(n.B/'scenery.edf')
    source, scene = n.preflight(); _, terrain, _ = n.tools()
    profile = dict(name='localized-baked-shadows' if localized else 'probe-terrain-cast-off',
                   shadowmaps=True, scale=.3 if localized else .2, supersampling=1,
                   terrain_self_shadow=localized, far_shadow_receivers=not localized,
                   authored_source_commit=recovery.SOURCE_COMMIT,
                   source_archive_sha256=recovery.INPUT_SHA,
                   recovered_asset_context=BASE_CONTEXT,
                   native_asset_provenance={s:{k:m[k] for k in BASE_CONTEXT} for s,m in manifests.items()})
    params = write_params(localized, profile['scale'])
    dest = n.G/(n.NAME+'.map'); dest.unlink(missing_ok=True)
    results = {stage:m['details'] for stage,m in manifests.items()}
    label = 'localized' if localized else 'terrain-cast-off'
    try:
        results['graphics'] = n.run(terrain, ['track.hmf', dest, params.name], 'moon_terrain_'+label,
                                    1200 if localized else 900)
    except TimeoutError:
        if localized: raise
        n.save(n.M/'terrain_cast_probe_outcome.json', dict(outcome='timeout', limit_seconds=900, bake_profile=profile))
        print('MOON_SHADOW_PROBE_INCONCLUSIVE terrain-cast-off reached 900 seconds', flush=True)
        return
    report = n.validate_package(source, scene, results, bake_profile=profile, diagnostic=not localized)
    if not localized:
        old = n.M/'Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz'
        new = n.M/'Taurus_Littrow_MX_v002_Diagnostic_Terrain_Cast_Off.pkz'
        old.replace(new); old.with_suffix('.pkz.sha256').unlink()
        new.with_suffix('.pkz.sha256').write_text(n.sha(new)+'  '+new.name+'\n')
        (n.M/'Moon_v002_Diagnostic_Validation.json').replace(n.M/'Moon_v002_Terrain_Cast_Off_Validation.json')
        n.save(n.M/'terrain_cast_probe_outcome.json', dict(outcome='compiled_and_validated', bake_profile=profile,
                                                         pkz_sha256=report['pkz_sha256']))
        return
    with zipfile.ZipFile(n.M/'Moon_v002_Previews.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted((n.M/'previews_v002').iterdir()):
            if path.is_file(): z.write(path, path.name)
    recovery.checkpoint('map', recovery.PACKAGE_FILES['map'],
                        dict(checks_pass=report['checks_pass'], bake_profile=profile,
                             native_height_validation=report['native_height_validation']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['unpack', 'restore-diagnostic', 'scenery-localized',
                                         'probe-terrain-cast-off', 'map-localized', 'publish-restore'])
    stage = parser.parse_args().stage
    if stage == 'unpack': recovery.unpack()
    elif stage == 'restore-diagnostic': restore_base('map-test')
    elif stage == 'scenery-localized': localized_scenery()
    elif stage == 'publish-restore':
        m = recovery.restore('map')
        assert m['details']['checks_pass'] and m['details']['bake_profile']['name'] == 'localized-baked-shadows'
        assert m['details']['bake_profile']['shadowmaps'] and not m['details']['bake_profile']['far_shadow_receivers']
    else: graphics(stage == 'map-localized')


if __name__ == '__main__': main()
