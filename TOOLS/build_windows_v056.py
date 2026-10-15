"""Official native compilation with independent texture, geometry and package checks."""
import mmap
import os
import re
import shutil
import struct
import zipfile
from pathlib import Path

from v056_inputs import R, BASE, PREV, O, M, NAME, DEST, sha, save
from v056_surface import source
from v054_geometry import read
from v027_scenery import parse, values, child
from scene_texture_bindings_v044 import actual_diffuse_bindings
from legacy_color_validation_v044 import legacy_materials
from validate_native_textures_v024 import bitmap_signature, verify_files
from native_coordinate_scan_v044 import scan_points
from native_specular_v052 import specular_records
from v052_foliage import MATTE
from build_windows_v047 import run_native, native_tools

P = R / 'BUILD/v056_stage'
LOG = R / 'DOCUMENTATION'


def stage():
    for name in ['terrain_validation', 'surface_validation', 'scenery_validation', 'race_validation']:
        assert read(O / (name + '.json'))['checks_pass']
    P.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    for src, name in [(O / 'terrain.raw', 'terrain.raw'), (O / 'scenery.fbx', 'scenery.fbx'),
                      (O / 'compiled_track.hmf', 'track.hmf'), (O / 'main.tcl', 'main.tcl'),
                      (O / 'start.tcl', 'start.tcl'), (R / 'BUILD/v054_track.tht', 'track.tht'),
                      (R / 'BUILD/edf_params.ini', 'edf_params.ini'), (R / 'BUILD/trh_params.ini', 'trh_params.ini')]:
        shutil.copy2(src, P / name)
    assert sha(P / 'terrain.raw') == read(O / 'terrain_validation.json')['terrain_sha256']
    assert sha(P / 'scenery.fbx') == read(O / 'scenery_validation.json')['scenery_sha256']
    assert sha(P / 'track.tht') == read(R / 'BUILD/v054_input_validation.json')['physical_material_declarations_sha256']
    params = (R / 'BUILD/map_params.ini').read_text()
    for key in ['shadowvolumes_supersampling', 'shadowmaps_supersampling']:
        params, count = re.subn(r'(?m)^' + key + r'\s*=\s*1\s*$', key + '=4', params)
        assert count == 1
    params, count = re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$', 'shadowmaps_scale=0.1', params)
    assert count == 1
    (P / 'map_params.ini').write_text(params)
    # Use the exact accepted folder overlays, including shader and flag files.
    folders = [BASE/'materials', R/'V046_OUTPUT/materials', R/'V052_OUTPUT/materials',
               BASE/'facility_textures', R/'V047_OUTPUT/facility_textures', R/'V052_OUTPUT/facility_textures',
               PREV/'materials', M]
    for folder in folders:
        for src in folder.iterdir():
            if src.suffix in ['.tga','.shd','.flg']:
                shutil.copy2(src,P/src.name)
    for src in (BASE/'masks').glob('*.tga'):
        # Base masks are overlaid first; restored v054 masks take precedence.
        name = 'mask_'+src.name
        if not (PREV/'materials'/name).is_file():
            shutil.copy2(src,P/name)
    for name in ['grass_n.tga','basemap.tga','v024_pit_gravel.tga']:
        shutil.copy2(BASE/name,P/name)
    terrain_names = {row['file'] for row in read(O/'surface_validation.json')['active_terrain_inventory']}
    nodes = parse((P / 'scenery.fbx').read_bytes())[0]
    binding = actual_diffuse_bindings(nodes)
    objects = {values(n)[0]: n for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    links = [values(n) for n in next(n for n in nodes if n['name'] == b'Connections')['children']]
    fbm = P / 'scenery.fbm'
    fbm.mkdir(exist_ok=True)
    # Facility shaders include approved matte foliage and object normal maps.
    facilities = [BASE / 'facility_textures', R / 'V047_OUTPUT/facility_textures', R / 'V052_OUTPUT/facility_textures']
    for folder in facilities:
        for src in folder.iterdir():
            if src.suffix in ['.tga', '.shd', '.flg']:
                shutil.copy2(src, P / src.name)
    for b in binding['bindings']:
        name = b['texture']
        assert Path(name).name == name
        if not (P / name).exists():
            video = next(objects[v[1]] for v in links if v[2] == b['texture_id'] and objects.get(v[1], {}).get('name') == b'Video')
            content = child(video, b'Content')['props']
            assert content[:1] == b'R' and struct.unpack_from('<I', content, 1)[0] == len(content) - 5
            (P / name).write_bytes(content[5:])
        shutil.copy2(P / name, fbm / name)
    names = set(binding['actual_diffuse_textures'])
    normals = set()
    for name in list(names):
        shader = P / (Path(name).stem + '.shd')
        if not shader.exists():
            continue
        shutil.copy2(shader, fbm / shader.name)
        for ref in re.findall(r'(?m)^\s*map\s*=\s*(\S+)', shader.read_text()):
            assert (P / ref).exists(), (name, ref)
            names.add(ref)
            if ref != MATTE:
                normals.add(ref)
    for name in names:
        bitmap_signature(P / name)
        shutil.copy2(P / name, fbm / name)
    for row in read(O / 'surface_validation.json')['active_terrain_inventory']:
        assert sha(P / row['file']) == row['sha256'], row['file']
    for ref in re.findall(r'(?m)^\s*(?:data|map|mask)\s*=\s*(\S+)', (P / 'track.hmf').read_text() + (P / 'track.tht').read_text()):
        assert (P / ref).exists(), ref
    save(O / 'native_staging_validation.json', dict(checks_pass=True, all_active_textures_resolved=True,
         source_terrain_exact=True, source_scenery_exact=True, physical_declarations_exact_v054=True,
         terrain_textures=sorted(terrain_names), object_textures=sorted(names)))
    return [P / n for n in sorted(names)], [P / n for n in sorted(normals)]


def package():
    for p in [DEST / 'code.txt', P / 'code.txt']:
        if p.exists():
            shutil.copy2(p, LOG / 'v056_track_code.txt')
            if p.parent == DEST:
                p.unlink()
    pkz = R / '12_RELEASE/OrlandoMX_2026_v056.pkz'
    tmp = pkz.with_suffix('.pkz.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(DEST.iterdir()):
            if p.is_file():
                z.write(p, NAME + '/' + p.name)
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None and len(z.infolist()) == 13
        assert all(n.startswith(NAME + '/') for n in z.namelist())
    tmp.replace(pkz)
    pkz.with_suffix('.pkz.sha256').write_text(sha(pkz) + '  ' + pkz.name + '\n')
    return pkz


def validate(textures, normals, native, pkz):
    edf = P / 'scenery.edf'
    mappath, trh = DEST / (NAME + '.map'), DEST / (NAME + '.trh')
    objects = verify_files(edf, mappath, [p for p in textures if p.name != MATTE], LOG / 'v056_native_object_texture_validation.json',
         legacy_materials=legacy_materials(P / 'scenery.fbx', textures), normal_maps=normals)
    assert objects['checks_pass']
    with edf.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        matte_edf = specular_records(raw, P / MATTE, minimum_records=2)
    points = read(O / 'native_probes.json')
    points = points['retained_geometry'] + points['changed_geometry']
    payloads = []
    with mappath.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        assert raw[:2] == b'MP'
        matte_map = specular_records(raw, P / MATTE)
        for row in read(O / 'surface_validation.json')['active_terrain_inventory']:
            name = row['file']
            if name.startswith('mask_'):
                continue
            w, h, digest = bitmap_signature(P / name)
            offset = raw.find(struct.pack('<2I', w, h) + digest)
            assert offset >= 0, ('Missing/incorrect native terrain texture', name)
            payloads.append(dict(texture=name, size=[w, h], pixel_md5=digest.hex(), map_offset=offset, source_sha256=sha(P / name)))
        errors = scan_points(raw, [p['expected_xyz_m'] for p in points])
        assert all(e is not None for e in errors), 'Native scenery coordinates do not match source'
    base = read(R / 'BUILD/v056_inputs/OrlandoMX_v054_Validation.json')
    assert sha(trh) != base['trh_sha256'] and sha(trh) != native['unmerged_trh_sha256']
    assert sha(P / 'terrain.raw') == read(O / 'terrain_validation.json')['terrain_sha256']
    race = read(O / 'race_validation.json')
    for row in race['retained_game_files']:
        assert sha(DEST / row['file']) == row['sha256']
    assert pkz.stat().st_size <= 964987509, ('Exceeded accepted v054 package budget', pkz.stat().st_size)
    from v056_native_heights import validate_native_heights
    height_check = validate_native_heights(mappath,trh)
    assert read(O/'surface_validation.json')['rgba8_base_level_bytes_after'] == read(O/'surface_validation.json')['rgba8_base_level_bytes_before']
    sources = {n: read(O / (n + '.json')) for n in ['terrain_validation', 'surface_validation', 'scenery_validation', 'race_validation', 'native_staging_validation']}
    report = dict(version='v056', baseline='v054', compiled=True, source_checks=True, centerline_merged=True,
         native_collision_updated=True, source_commit=os.environ['GITHUB_SHA'], native_build_run=int(os.environ['GITHUB_RUN_ID']),
         native_compile=native, source_validation=sources, native_object_textures=objects,
         native_height_validation=height_check, exact_all_14_corner_banks_v054=True,
         unchanged_decoded_texture_allocation_vs_v054=True,
         native_matte_foliage_EDF=matte_edf, native_matte_foliage_MAP=matte_map,
         terrain_texture_payloads=payloads, native_geometry_probes=len(points), native_geometry_error_max_m=max(errors),
         package_integrity_passed=True, package_size_budget_passed=True,
         pkz_bytes=pkz.stat().st_size, baseline_pkz_bytes=base['pkz_bytes'], pkz_bytes_saved=base['pkz_bytes']-pkz.stat().st_size,
         pkz_sha256=sha(pkz), map_bytes=mappath.stat().st_size, map_sha256=sha(mappath), trh_sha256=sha(trh),
         in_game_visual_check=False, in_game_riding_test=False, performance_test=False,
         pending=['MX Bikes load and first-lap timing check', 'R03 landing ride test', 'Dirt/shoulder appearance and FPS comparison'])
    save(R / '12_RELEASE/OrlandoMX_v056_Validation.json', report)
    (R/'12_RELEASE/Install_v056.txt').write_text(
        'Orlando MX 2026 v056\n\nCopy OrlandoMX_2026_v056.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select v056 and reset the track.\n\n'
        'Repairs the rejected v055 update. All 14 v054 corner banks and full track boundaries are restored. Full-resolution accepted racing photographs, normals and grooming return. Only the base soil is mildly tinted closer to the racing hue, retaining most of the original edge contrast. No wider photographic mask and no new texture allocations.\n\n'
        'The right-side R03 crown is reduced locally before the next corner. The single centre profile and every corner grid remain exact v054. The original turn bank is retained, so the banked entry is intentionally not flattened. Accepted A/B/C layout, start, race/reset data and scenery are retained.\n\n'
        'Same 14 layers and unique active image dimensions as v054. Actual process memory, VRAM and FPS have not been measured. Full MAP and TRH height grids, corner banks, native textures/scenery, race data and archive checks passed. Actual game appearance and riding still require a ride test. All players need the same PKZ.\n',encoding='utf-8')
    print('V056_NATIVE_VALIDATED', pkz.stat().st_size, 'bytes', sha(pkz), flush=True)


def main():
    assert os.name == 'nt', 'Use the Windows workflow'
    textures, normals = stage()
    edfexe, terrainexe = native_tools()
    tracked = edfexe.parents[1] / 'tracked/tracked.exe'
    assert tracked.is_file()
    import build_windows_v047 as helper
    helper.P, helper.LOG = P, LOG
    native = {}
    if read(O / 'scenery_validation.json')['scenery_unchanged']:
        src = R / 'BUILD/v056_native_baseline/scenery.edf'
        assert sha(src) == read(R / 'BUILD/v056_input_validation.json')['scenery_edf_sha256']
        shutil.copy2(src, P / 'scenery.edf')
        native['scenery'] = dict(returncode=0, reused_exact_delivered_v054=True, sha256=sha(src))
    else:
        native['scenery'] = run_native(edfexe, ['scenery.fbx', 'scenery.edf', 'edf_params.ini', '-q'], 'fbx2edf_v056', 7200)
    assert (P / 'scenery.edf').read_bytes()[:4] == b'EDF\0'
    from v056_transfer import preserve_edf, preserve_native
    preserve_edf()
    with (P / 'scenery.edf').open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        points = read(O / 'native_probes.json')
        points = points['retained_geometry'] + points['changed_geometry']
        errors = scan_points(raw, [p['expected_xyz_m'] for p in points])
        assert all(e is not None for e in errors), 'EDF geometry preflight failed'
        specular_records(raw, P / MATTE, minimum_records=2)
    trh, mappath = DEST / (NAME + '.trh'), DEST / (NAME + '.map')
    for path in [trh, mappath]:
        path.unlink(missing_ok=True)
    native['collision'] = run_native(terrainexe, ['track.tht', trh, 'trh_params.ini'], 'terrained_trh_v056', 7200)
    assert trh.stat().st_size > 2049*2049*2 and trh.read_bytes()[:3] == b'TRH'
    native['unmerged_trh_sha256'] = sha(trh)
    native['centreline'] = run_native(tracked, ['-merge', trh, 'cl', P/'main.tcl', 'sa', P/'start.tcl'], 'tracked_merge_v056', 1800)
    assert sha(trh) != native['unmerged_trh_sha256']
    native['terrain'] = run_native(terrainexe, ['track.hmf', mappath, 'map_params.ini'], 'terrained_map_v056', 9000)
    assert 'Map File Write' in (LOG/'terrained_map_v056.log').read_text() and mappath.is_file()
    save(O / 'native_compile_results.json', native)
    pkz = package()
    # Save native results before the final validator, so a checker fix can resume.
    preserve_native()
    validate(textures, normals, native, pkz)


if __name__ == '__main__':
    main()
