"""Native lighting-only build: exact v065 scene, materials, geometry and races."""
import argparse
import mmap
import os
import re
import shutil
import struct
import zipfile
import numpy as np
from v066_lighting import (R, B, O, S, BASE_BUILD, SAVED, NAME, DEST, EDF_SHA,
                           TERRAIN_SHA, PHYSICS_SHA, read, save, source, sha,
                           copy_exact, check, validate_pair)
from v027_scenery import parse, values, child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature, verify_files
from native_coordinate_scan_v044 import scan_points
from native_specular_v052 import specular_records
from v052_foliage import MATTE
from build_windows_v047 import run_native, native_tools

P = R / 'BUILD/v066_stage'
LOG = R / 'DOCUMENTATION'


def probes():
    records = read(O / 'native_probes.json')
    return records['retained_geometry'] + records['changed_geometry']


def stage():
    check()
    P.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    for src, name in [(O / 'terrain.raw', 'terrain.raw'), (O / 'scenery.fbx', 'scenery.fbx'),
                      (O / 'compiled_track.hmf', 'track.hmf'), (O / 'main.tcl', 'main.tcl'),
                      (O / 'start.tcl', 'start.tcl'), (O / 'map_params.ini', 'map_params.ini'),
                      (BASE_BUILD / 'v054_track.tht', 'track.tht'),
                      (BASE_BUILD / 'edf_params.ini', 'edf_params.ini'),
                      (BASE_BUILD / 'trh_params.ini', 'trh_params.ini')]:
        copy_exact(src, P / name)
    expected = read(S / 'native_expected_inputs.json')
    assert sha(P / 'terrain.raw') == expected['terrain'] == TERRAIN_SHA
    assert sha(P / 'scenery.fbx') == expected['scenery']
    assert sha(P / 'track.tht') == expected['physical_declarations'] == PHYSICS_SHA
    assert sha(P / 'track.hmf') == expected['hmf']
    assert re.search(r'(?m)^num_layers\s*=\s*14\s*$', (P / 'track.hmf').read_text())
    validate_pair((DEST / (NAME + '.amb')).read_text(), (P / 'map_params.ini').read_text())
    for src in sorted((O / 'facility_textures').iterdir()):
        if src.suffix in ['.tga', '.shd', '.flg']:
            copy_exact(src, P / src.name)
    surface = read(O / 'surface_validation.json')
    for row in surface['active_terrain_inventory'] + surface['active_shaders']:
        src = source(row['file'])
        assert sha(src) == row['sha256'], row['file']
        copy_exact(src, P / row['file'])
    nodes = parse((P / 'scenery.fbx').read_bytes())[0]
    bindings = actual_diffuse_bindings(nodes)
    objects = {values(n)[0]: n for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    links = [values(n) for n in next(n for n in nodes if n['name'] == b'Connections')['children']]
    fbm = P / 'scenery.fbm'
    fbm.mkdir(exist_ok=True)
    for binding in bindings['bindings']:
        name = binding['texture']
        assert name == os.path.basename(name)
        if not (P / name).is_file():
            video = next(objects[v[1]] for v in links if v[2] == binding['texture_id']
                         and objects.get(v[1], {}).get('name') == b'Video')
            content = child(video, b'Content')['props']
            assert content[:1] == b'R' and struct.unpack_from('<I', content, 1)[0] == len(content) - 5
            with (P / name).open('wb') as stream:
                stream.write(content[5:])
                stream.flush()
                os.fsync(stream.fileno())
    names = set(bindings['actual_diffuse_textures'])
    normals = set()
    for name in list(names):
        shader = P / (os.path.splitext(name)[0] + '.shd')
        if shader.is_file():
            copy_exact(shader, fbm / shader.name)
            for ref in re.findall(r'(?m)^\s*map\s*=\s*(\S+)', shader.read_text()):
                assert ref == os.path.basename(ref) and (P / ref).is_file(), (name, ref)
                names.add(ref)
                if ref != MATTE:
                    normals.add(ref)
    for name in names:
        bitmap_signature(P / name)
        copy_exact(P / name, fbm / name)
    for ref in re.findall(r'(?m)^\s*(?:data|map|mask)\s*=\s*(\S+)',
                          (P / 'track.hmf').read_text() + (P / 'track.tht').read_text()):
        assert ref == os.path.basename(ref) and (P / ref).is_file(), ref
    del nodes, objects, links
    copy_exact(SAVED / 'scenery.edf', P / 'scenery.edf')
    assert sha(P / 'scenery.edf') == EDF_SHA
    with (P / 'scenery.edf').open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        assert raw[:4] == b'EDF\0'
        errors = scan_points(raw, [p['expected_xyz_m'] for p in probes()])
        assert all(error is not None for error in errors)
        specular_records(raw, P / MATTE, minimum_records=2)
    for row in surface['active_terrain_inventory'] + surface['active_shaders']:
        assert sha(P / row['file']) == row['sha256'], row['file']
    save(O / 'native_staging_validation.json', dict(
        checks_pass=True, all_source_geometry_and_materials_exact_v065=True,
        all_active_textures_and_shaders_resolved=True, baked_runtime_sun_synchronized=True,
        saved_edf_sha256=EDF_SHA, object_texture_files=sorted(names),
        object_normal_files=sorted(normals), native_scenery_probe_count=len(errors),
        native_scenery_max_error_m=max(errors), native_shadow_supersampling=4,
        native_shadowmap_scale=.1, shadow_resolution_and_sampling_exact_v065=True,
        map_params_sha256=sha(P / 'map_params.ini'), daylight_sha256=expected['daylight']))
    print('V066_NATIVE_STAGING_PASS; exact v065 assets, synchronized raking daylight', flush=True)


def native_context():
    assert os.name == 'nt', 'Use the Windows workflow'
    assert read(O / 'native_staging_validation.json')['checks_pass']
    import build_windows_v047 as helper
    helper.P, helper.LOG = P, LOG
    return native_tools()


def collision():
    edfexe, terrainexe = native_context()
    tracked = edfexe.parents[1] / 'tracked/tracked.exe'
    assert tracked.is_file()
    trh = DEST / (NAME + '.trh')
    trh.unlink(missing_ok=True)
    native = dict(scenery=dict(reused=True, sha256=EDF_SHA, exact_v065_native_scenery=True))
    native['collision'] = run_native(terrainexe, ['track.tht', trh, 'trh_params.ini'], 'terrained_trh_v066', 7200)
    native['unmerged_trh_sha256'] = sha(trh)
    native['centreline'] = run_native(tracked, ['-merge', trh, 'cl', P / 'main.tcl', 'sa', P / 'start.tcl'],
                                     'tracked_merge_v066', 1800)
    assert sha(trh) != native['unmerged_trh_sha256']
    from v057_native_heights import collision_heights
    expected = np.fromfile(O / 'terrain.raw', '<u2').reshape(2049, 2049)
    assert np.array_equal(collision_heights(trh), expected)
    native['complete_collision_grid_exact_v065'] = True
    save(O / 'native_compile_results.json', native)
    print('V066_COLLISION_AND_ROUTES_PASS; all 4198401 collision samples exact v065', flush=True)


def package():
    code = DEST / 'code.txt'
    if code.exists():
        shutil.copy2(code, LOG / 'v066_track_code.txt')
        code.unlink()
    target = R / '12_RELEASE/OrlandoMX_2026_v066.pkz'
    temporary = target.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(DEST.iterdir()):
            if path.is_file():
                archive.write(path, NAME + '/' + path.name)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None and len(archive.infolist()) == 13
        assert all(n.startswith(NAME + '/') for n in archive.namelist())
    temporary.replace(target)
    target.with_suffix('.pkz.sha256').write_text(sha(target) + '  ' + target.name + '\n')
    return target


def validate(native, pkz):
    check()
    record = read(O / 'native_staging_validation.json')
    textures = [P / n for n in record['object_texture_files']]
    normals = [P / n for n in record['object_normal_files']]
    mappath = DEST / (NAME + '.map')
    trh = DEST / (NAME + '.trh')
    objects = verify_files(P / 'scenery.edf', mappath, [p for p in textures if p.name != MATTE],
                           LOG / 'v066_native_object_texture_validation.json',
                           legacy_materials=legacy_materials(P / 'scenery.fbx', textures), normal_maps=normals)
    assert objects['checks_pass']
    payloads = []
    with mappath.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        assert raw[:4] == b'MP2\0'
        matte = specular_records(raw, P / MATTE)
        for row in read(O / 'surface_validation.json')['active_terrain_inventory']:
            name = row['file']
            if name.startswith('mask_'):
                continue
            width, height, digest = bitmap_signature(P / name)
            offset = raw.find(struct.pack('<2I', width, height) + digest)
            assert offset >= 0, ('Native terrain bitmap changed or missing', name)
            payloads.append(dict(texture=name, size=[width, height], pixel_md5=digest.hex(), map_offset=offset))
        errors = scan_points(raw, [p['expected_xyz_m'] for p in probes()])
        assert all(error is not None for error in errors)
    from v057_native_heights import collision_heights, map_heights
    expected = np.fromfile(O / 'terrain.raw', '<u2').reshape(2049, 2049)
    visual, offset = map_heights(mappath, expected)
    assert np.array_equal(visual, expected) and np.array_equal(collision_heights(trh), expected)
    heights = dict(checks_pass=True, native_visual_collision_grids_exact=True,
                   every_height_exact_v065=True, samples_checked_per_grid=int(expected.size),
                   map_grid_offset=offset, wall_roller_visual_collision_exact=True, source_raw_sha256=TERRAIN_SHA)
    save(O / 'native_height_validation.json', heights)
    assert sha(P / 'map_params.ini') == read(S / 'native_expected_inputs.json')['map_params']
    lighting = validate_pair((DEST / (NAME + '.amb')).read_text(), (P / 'map_params.ini').read_text())
    assert pkz.stat().st_size <= 964987509
    report = dict(version='v066', baseline='v065', compiled=True, source_checks=True,
        source_commit=os.environ['GITHUB_SHA'], native_build_run=int(os.environ['GITHUB_RUN_ID']),
        centerline_merged=True, native_compile=native, native_object_textures=objects,
        native_height_validation=heights, native_collision_exact_v065=True,
        wall_roller_visual_collision_exact=True, all_source_scenery_and_textures_exact_v065=True,
        all_race_data_exact_v065=True, accepted_B_C_surfaces_and_cleared_start_grass_exact=True,
        baked_runtime_lighting_synchronized=True, lighting=lighting,
        source_validation={name: read(O / (name + '.json')) for name in
                           ['surface_validation', 'race_validation', 'precompile_validation', 'native_staging_validation']},
        source_texture_and_geometry_allocation_unchanged=True, native_shadow_quality_exact_v065=True,
        layer_count=14, added_images=0, added_layers=0,
        texture_allocation_bytes=read(O / 'surface_validation.json')['texture_allocation_bytes'],
        native_matte_foliage_MAP=matte, terrain_texture_payloads=payloads,
        native_geometry_probes=len(errors), native_geometry_max_error_m=max(errors),
        package_integrity_passed=True, package_size_budget_passed=True,
        pkz_bytes=pkz.stat().st_size, pkz_sha256=sha(pkz), map_bytes=mappath.stat().st_size,
        map_sha256=sha(mappath), trh_sha256=sha(trh), in_game_visual_check=False,
        in_game_riding_test=False, performance_test=False,
        pending=['Compare v065 and v066 in Clear weather with matching game graphics',
                 'Confirm shaded van, dirt and jump-face visibility while riding', 'RAM/VRAM and FPS test'])
    assert all(value['checks_pass'] for value in report['source_validation'].values())
    save(R / '12_RELEASE/OrlandoMX_v066_Validation.json', report)
    (R / '12_RELEASE/Install_v066.txt').write_text(
        'Orlando MX 2026 v066 - cinematic daylight test\n\n'
        'Keep v065 installed for comparison. Copy OrlandoMX_2026_v066.pkz to '
        'Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v066 and reset the track. '
        'All players must use the same PKZ.\n\n'
        'Compare in CLEAR weather using the same graphics settings, with shadows enabled. '
        'The sun is lowered from about 54 to 28 degrees and turned toward the cinematic photo key. '
        'Warm direct light, restrained cool fill and reduced distance haze target clearer dirt and vehicle shading. '
        'Baked terrain/scenery shadows and runtime sunlight use exactly the same direction.\n\n'
        'All v065 terrain heights, riding physics, B corners, C surfaces, start grass clearance, wall roller, '
        'vehicles, candy sign, Pup memorial, crocodile and race data are retained. No new textures, '
        'layers, scenery meshes or higher-resolution shadow maps were added.\n\n'
        'This is a native MX Bikes lighting test, not Blender lighting or a ReShade preset. '
        'Actual in-game appearance, RAM/VRAM and FPS require your test.\n', encoding='utf-8')
    print('V066_NATIVE_VALIDATED', pkz.stat().st_size, 'bytes', sha(pkz), flush=True)


def final():
    _, terrainexe = native_context()
    native = read(O / 'native_compile_results.json')
    assert native['complete_collision_grid_exact_v065']
    validate_pair((DEST / (NAME + '.amb')).read_text(), (P / 'map_params.ini').read_text())
    mappath = DEST / (NAME + '.map')
    mappath.unlink(missing_ok=True)
    native['terrain'] = run_native(terrainexe, ['track.hmf', mappath, 'map_params.ini'], 'terrained_map_v066', 9000)
    assert mappath.is_file() and 'Map File Write' in (LOG / 'terrained_map_v066.log').read_text()
    save(O / 'native_compile_results.json', native)
    pkz = package()
    validate(native, pkz)
    from v066_transfer import preserve_native
    preserve_native()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['stage', 'collision', 'final'])
    {'stage': stage, 'collision': collision, 'final': final}[parser.parse_args().action]()
