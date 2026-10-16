"""Restore exact v065 assets and author only a synchronized native daylight test."""
from pathlib import Path
import argparse
import configparser
import copy
import hashlib
import json
import math
import os
import re
import shutil
import urllib.request
import zipfile
import zlib

R = Path(__file__).resolve().parents[1]
B = R / 'V065_OUTPUT'
O = R / 'V066_OUTPUT'
S = R / 'V066_SOURCE'
CACHE = R / 'BUILD/v066_inputs'
BASE_BUILD = CACHE / 'baseline_build'
BASE_GAME = CACHE / 'baseline_game'
BASE_SOURCE = CACHE / 'baseline_source'
SAVED = CACHE / 'native_scenery'
NAME = 'orlandomx_2026_v066'
DEST = R / '12_RELEASE' / NAME
OLD_NAME = 'orlandomx_2026_v065'
TERRAIN_SHA = '860350c4c733e5d26939e9e2f40204679ecef302d6e07889f78a849afc8a8fa2'
SCENERY_SHA = '40d8e6ddeacfa0d0c3c9fad454abd2f83acee633fb367e31c8530d8dbafa6e99'
DAYLIGHT_SHA = '77f98c93c8cd3d9ae7277f01c94edf06b7e6da1c6f96c38027484b4172735ecb'
EDF_SHA = '9ab4c5a2b1493d45863a4c4c831f08891daff2a8dbadd8828aa1139e9dc7acf8'
PHYSICS_SHA = '04aa0b587248caa8fb822c8fa8ed972bd3a919686def52a3639d71fc40cfbc9e'
PINS = {
    'v065_source.zip': (
        'v065-start-C-38852452690/OrlandoMX-v065-source-checkpoint.zip',
        808606861, '5ce49b42d54d2bcef50c6c11ce87037e7c625e5d387c06fd8c85cc73d9614b9a'),
    'v060_native_scenery.zip': (
        'v060-dense-grooming-38699998845/OrlandoMX-v060-native-scenery.zip',
        229447747, 'c0be39314e299458654371e08f437f68975d2c3f0aaa4cb38a369d79644c91a4'),
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.writing')
    with temp.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, indent=2) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def source(name):
    assert Path(name).name == name, name
    for folder in [O / 'materials', O / 'facility_textures', O]:
        if (folder / name).is_file():
            return folder / name
    raise FileNotFoundError(name)


def parse_amb(text):
    tokens = re.findall(r'[{}=]|[^\s{}=]+', re.sub(r';[^\n]*', '', text))
    position = 0

    def block(nested=False):
        nonlocal position
        result = {}
        while position < len(tokens):
            key = tokens[position]
            position += 1
            if key == '}':
                assert nested, 'Unexpected closing brace'
                return result
            assert key not in result and key not in ['{', '='], key
            marker = tokens[position]
            position += 1
            if marker == '{':
                result[key] = block(True)
            else:
                assert marker == '=', (key, marker)
                value = tokens[position]
                position += 1
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
        assert not nested, 'Unclosed block'
        return result

    result = block()
    assert position == len(tokens)
    return result


def format_amb(data, indent=0):
    lines = []
    for key, value in data.items():
        pad = ' ' * indent
        if isinstance(value, dict):
            lines.extend([pad + key, pad + '{', format_amb(value, indent + 1).rstrip(), pad + '}'])
        else:
            rendered = format(value, '.9g') if isinstance(value, (int, float)) else value
            lines.append(pad + key + ' = ' + rendered)
    return '\n'.join(lines) + '\n'


def sun_position(spec):
    azimuth = math.radians(spec['sun_azimuth_xz_degrees'])
    elevation = math.radians(spec['sun_elevation_degrees'])
    y = float(spec['sun_position_y'])
    assert 20 <= spec['sun_elevation_degrees'] <= 45 and y > 0
    horizontal = y / math.tan(elevation)
    return dict(x=horizontal * math.cos(azimuth), y=y, z=horizontal * math.sin(azimuth))


def author_amb(baseline_text, spec):
    baseline = parse_amb(baseline_text)
    assert set(baseline) == {'sun_position', 'clear', 'cloudy', 'rainy'}
    result = copy.deepcopy(baseline)
    result['sun_position'] = sun_position(spec)
    for key, field in [('ambient', 'clear_ambient_rgb'), ('sun_color', 'clear_sun_rgb')]:
        rgb = spec[field]
        assert len(rgb) == 3 and all(math.isfinite(v) and 0 <= v <= 1 for v in rgb)
        result['clear'][key] = dict(zip(['red', 'green', 'blue'], rgb))
    assert 0 < spec['clear_fog_density'] < baseline['clear']['fog']['density']
    result['clear']['fog']['density'] = spec['clear_fog_density']
    assert result['cloudy'] == baseline['cloudy'] and result['rainy'] == baseline['rainy']
    assert all(result[w]['sky'] == baseline[w]['sky'] and result[w]['sky_rot'] == baseline[w]['sky_rot']
               for w in ['clear', 'cloudy', 'rainy'])
    return format_amb(result)


def author_params(baseline_text, spec):
    result = baseline_text
    for axis, value in sun_position(spec).items():
        result, count = re.subn(r'(?m)^lightdir_' + axis + r'\s*=\s*[^\n]+$',
                                'lightdir_' + axis + '=' + format(value, '.9g'), result)
        assert count == 1, axis
    before = configparser.ConfigParser()
    before.read_string(baseline_text)
    after = configparser.ConfigParser()
    after.read_string(result)
    assert {k: v for k, v in before['params'].items() if not k.startswith('lightdir_')} == {
        k: v for k, v in after['params'].items() if not k.startswith('lightdir_')}
    assert after['params'].getfloat('shadowmaps_scale') == spec['shadowmaps_scale'] == .1
    for key in ['shadowmaps_supersampling', 'shadowvolumes_supersampling']:
        assert after['params'].getint(key) == spec[key] == 4
    for key in ['shadowmaps_create', 'shadowvolumes_create', 'shadowmaps_terraincast']:
        assert after['params'].getint(key) == 1
    return result


def validate_pair(amb_text, params_text):
    amb = parse_amb(amb_text)
    params = configparser.ConfigParser()
    params.read_string(params_text)
    a = [amb['sun_position'][axis] for axis in 'xyz']
    b = [params['params'].getfloat('lightdir_' + axis) for axis in 'xyz']
    assert all(abs(x - y) < 1e-7 for x, y in zip(a, b)), 'Baked and runtime sun directions differ'
    x, y, z = a
    return dict(sun_position_xyz=a, sun_elevation_degrees=math.degrees(math.atan2(y, math.hypot(x, z))),
                sun_azimuth_xz_degrees=math.degrees(math.atan2(z, x)) % 360,
                synchronized_baked_and_runtime_sun=True)


def download(name):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    relative, size, digest = PINS[name]
    if path.is_file() and path.stat().st_size == size and sha(path) == digest:
        return path
    temporary = path.with_suffix('.downloading')
    request = urllib.request.Request('https://github.com/mxsam72/orlando-mx-build/releases/download/' + relative,
                                     headers={'User-Agent': 'OrlandoMX-v066-lighting'})
    with urllib.request.urlopen(request, timeout=120) as src, temporary.open('wb') as dst:
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    assert temporary.stat().st_size == size and sha(temporary) == digest, name
    temporary.replace(path)
    return path


def extract_file(archive, member, target):
    assert not Path(member).is_absolute() and '..' not in Path(member).parts, member
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    info = archive.getinfo(member)
    if target.is_file() and target.stat().st_size == info.file_size:
        crc = 0
        with target.open('rb') as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                crc = zlib.crc32(chunk, crc)
        if crc == info.CRC:
            return
    temporary = target.with_name(target.name + '.extracting')
    with archive.open(member) as src, temporary.open('wb') as dst:
        shutil.copyfileobj(src, dst, 4 * 1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    assert temporary.stat().st_size == info.file_size, member
    crc = 0
    with temporary.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            crc = zlib.crc32(chunk, crc)
    assert crc == info.CRC, member
    temporary.replace(target)


def copy_exact(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = sha(src)
    if dest.exists() and sha(dest) == digest:
        return
    # The Windows native job can share immutable inputs on NTFS, keeping the
    # checkpoint/staging disk footprint down. Local copies use flushed writes.
    if os.name == 'nt' and not dest.exists():
        try:
            os.link(src, dest)
            assert sha(dest) == digest
            return
        except OSError:
            pass
    temporary = dest.with_name(dest.name + '.copying')
    with src.open('rb') as reader, temporary.open('wb') as writer:
        shutil.copyfileobj(reader, writer, 4 * 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())
    assert sha(temporary) == digest, dest
    temporary.replace(dest)


def actual_inputs():
    surface = read(B / 'surface_validation.json')
    return dict(terrain=sha(O / 'terrain.raw'), scenery=sha(O / 'scenery.fbx'),
                hmf=sha(O / 'compiled_track.hmf'), physical_declarations=sha(BASE_BUILD / 'v054_track.tht'),
                main_route=sha(O / 'main.tcl'), start_route=sha(O / 'start.tcl'),
                daylight=sha(O / 'trial_daylight.amb'), map_params=sha(O / 'map_params.ini'),
                native_scenery=sha(SAVED / 'scenery.edf'),
                terrain_images={row['file']: sha(source(row['file'])) for row in surface['active_terrain_inventory']},
                terrain_shaders={row['file']: sha(source(row['file'])) for row in surface['active_shaders']})


def prepare():
    O.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    for path in sorted(B.rglob('*')):
        if path.is_file() and path.suffix != '.json' and path.name != 'trial_daylight.amb':
            copy_exact(path, O / path.relative_to(B))
    copy_exact(B / 'native_probes.json', O / 'native_probes.json')
    spec = read(S / 'lighting_spec.json')
    baseline_amb = BASE_GAME / (OLD_NAME + '.amb')
    assert sha(baseline_amb) == DAYLIGHT_SHA
    text = author_amb(baseline_amb.read_text(), spec)
    (O / 'trial_daylight.amb').write_text(text, encoding='utf-8', newline='\n')
    params = author_params((BASE_BUILD / 'v065_stage/map_params.ini').read_text(), spec)
    (O / 'map_params.ini').write_text(params, encoding='utf-8', newline='\n')
    retained = []
    for path in sorted(BASE_GAME.iterdir()):
        target = DEST / path.name.replace(OLD_NAME, NAME)
        if path.suffix == '.amb':
            shutil.copy2(O / 'trial_daylight.amb', target)
        elif path.suffix == '.ini':
            target.write_text(path.read_text().replace('v065', 'v066'), encoding='utf-8', newline='\n')
        else:
            shutil.copy2(path, target)
            retained.append(dict(file=target.name, sha256=sha(path)))
    assert len(list(DEST.iterdir())) == 11
    save(O / 'race_validation.json', dict(checks_pass=True, retained_game_files=retained,
         all_race_reset_grid_pits_checkpoints_exact_v065=True, version_name_only_ini_change=True,
         lighting_sha256=sha(DEST / (NAME + '.amb'))))
    baseline = read(B / 'surface_validation.json')
    save(O / 'surface_validation.json', dict(checks_pass=True, baseline='v065',
         accepted_B_corners_C_course_and_start_exact=True, start_grass_clearance_exact=True,
         layer_count=baseline['layer_count'], texture_allocation_bytes=baseline['texture_allocation_bytes'],
         active_terrain_inventory=baseline['active_terrain_inventory'], active_shaders=baseline['active_shaders'],
         added_images=0, added_layers=0, every_terrain_bitmap_and_shader_exact_v065=True))
    actual = actual_inputs()
    assert actual['terrain'] == TERRAIN_SHA and actual['scenery'] == SCENERY_SHA
    assert actual['physical_declarations'] == PHYSICS_SHA and actual['native_scenery'] == EDF_SHA
    for field, key in [('active_terrain_inventory', 'terrain_images'), ('active_shaders', 'terrain_shaders')]:
        assert {row['file']: row['sha256'] for row in baseline[field]} == actual[key]
    expected = S / 'native_expected_inputs.json'
    if expected.exists():
        assert read(expected) == actual, 'Inputs differ from the reviewed v066 source'
    else:
        save(expected, actual)
    check()


def restore():
    archive = download('v065_source.zip')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for member in z.namelist():
            if member.endswith('/'):
                continue
            if member.startswith('V065_OUTPUT/'):
                target = B / member.removeprefix('V065_OUTPUT/')
            elif member.startswith('V065_SOURCE/'):
                target = BASE_SOURCE / member.removeprefix('V065_SOURCE/')
            elif member.startswith('12_RELEASE/' + OLD_NAME + '/'):
                target = BASE_GAME / Path(member).name
            elif member.startswith('BUILD/'):
                target = BASE_BUILD / member.removeprefix('BUILD/')
            else:
                continue
            extract_file(z, member, target)
    native = download('v060_native_scenery.zip')
    with zipfile.ZipFile(native) as z:
        assert set(z.namelist()) == {'scenery.edf', 'fbx2edf_v060.log'} and z.testzip() is None
        for member in z.namelist():
            extract_file(z, member, SAVED / member)
    assert sha(SAVED / 'scenery.edf') == EDF_SHA
    shutil.copy2(BASE_BUILD / 'tool_versions.json', R / 'BUILD/tool_versions.json')
    save(R / 'BUILD/v066_recovered_inputs.json', dict(checks_pass=True, pinned_assets=PINS,
         baseline_release='v065-start-C-38852452690', saved_edf_sha256=EDF_SHA,
         source_scenery_sha256=SCENERY_SHA, game_file_count=len(list(BASE_GAME.iterdir()))))
    prepare()


def check():
    actual = actual_inputs()
    assert actual == read(S / 'native_expected_inputs.json')
    assert actual['terrain'] == TERRAIN_SHA and actual['scenery'] == SCENERY_SHA
    assert actual['physical_declarations'] == PHYSICS_SHA and actual['native_scenery'] == EDF_SHA
    for name in ['terrain.raw', 'scenery.fbx', 'compiled_track.hmf', 'main.tcl', 'start.tcl', 'route.npz']:
        assert sha(O / name) == sha(B / name), name
    surface = read(B / 'surface_validation.json')
    for field, key in [('active_terrain_inventory', 'terrain_images'), ('active_shaders', 'terrain_shaders')]:
        assert {row['file']: row['sha256'] for row in surface[field]} == actual[key]
    assert surface['layer_count'] == 14
    race = read(O / 'race_validation.json')
    for row in race['retained_game_files']:
        assert sha(DEST / row['file']) == row['sha256']
    assert (DEST / (NAME + '.ini')).read_text() == (BASE_GAME / (OLD_NAME + '.ini')).read_text().replace('v065', 'v066')
    assert sha(DEST / (NAME + '.amb')) == actual['daylight'] == race['lighting_sha256']
    spec = read(S / 'lighting_spec.json')
    baseline = parse_amb((BASE_GAME / (OLD_NAME + '.amb')).read_text())
    amb_text = (O / 'trial_daylight.amb').read_text()
    current = parse_amb(amb_text)
    assert current['cloudy'] == baseline['cloudy'] and current['rainy'] == baseline['rainy']
    assert amb_text == author_amb((BASE_GAME / (OLD_NAME + '.amb')).read_text(), spec)
    params = (O / 'map_params.ini').read_text()
    assert params == author_params((BASE_BUILD / 'v065_stage/map_params.ini').read_text(), spec)
    matched = validate_pair(amb_text, params)
    assert abs(matched['sun_elevation_degrees'] - spec['sun_elevation_degrees']) < 1e-6
    assert abs(matched['sun_azimuth_xz_degrees'] - spec['sun_azimuth_xz_degrees']) < 1e-6
    report = dict(checks_pass=True, version='v066', expected_inputs=actual, lighting=matched,
         clear_ambient_rgb=spec['clear_ambient_rgb'], clear_sun_rgb=spec['clear_sun_rgb'],
         clear_fog_density=spec['clear_fog_density'], cloudy_and_rainy_colors_exact=True,
         stock_skies_exact=True, all_terrain_and_scenery_source_exact_v065=True,
         all_accepted_B_C_surface_images_and_shaders_exact=True, wall_roller_exact=True,
         vehicles_candy_sign_memorial_and_crocodile_exact=True, all_race_data_exact=True,
         layer_count=14, added_images=0, added_layers=0,
         source_texture_allocation_bytes=surface['texture_allocation_bytes'],
         native_shadow_scale_unchanged=.1, native_shadow_supersampling_unchanged=4,
         in_game_visual_check=False, performance_test=False)
    save(O / 'precompile_validation.json', report)
    save(O / 'generated_final_inputs.json', actual)
    print('V066_PRECOMPILE_PASS; synchronized 28-degree daylight; exact v065 geometry, materials and races', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['restore', 'check'])
    {'restore': restore, 'check': check}[parser.parse_args().action]()
