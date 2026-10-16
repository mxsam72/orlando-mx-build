"""v067 native build contract; preserve validated v066, authorize only approved material and sun delta."""
from pathlib import Path
import os
import shutil
import v066_lighting as previous

R = previous.R
B = previous.O
O = R / 'V067_OUTPUT'
S = R / 'V067_SOURCE'
BASE_BUILD = previous.BASE_BUILD
SAVED = previous.SAVED
NAME = 'orlandomx_2026_v067'
DEST = R / '12_RELEASE' / NAME
EDF_SHA = previous.EDF_SHA
TERRAIN_SHA = previous.TERRAIN_SHA
PHYSICS_SHA = previous.PHYSICS_SHA
SCENERY_SHA = previous.SCENERY_SHA
read = previous.read
save = previous.save
sha = previous.sha
copy_exact = previous.copy_exact
validate_pair = previous.validate_pair


def source(name):
    from v067_surface import source as candidate_source
    return candidate_source(name)


def verify_candidate():
    previous.check()
    approval = read(S / 'native_build_authorization.json')
    assert approval['version'] == 'v067' and approval['native_compilation_authorized'] is True
    spec = read(S / 'visual_spec.json')
    assert spec['preserve_B_corners_C_elsewhere'] and spec['preserve_all_masks']
    report = read(O / 'surface_validation.json')
    assert report['checks_pass'] and report['version'] == 'v067'
    assert report['all_masks_exact_v066'] and report['all_scenery_exact_v066']
    assert report['baseline_integrity_pass'] and not report['native_compilation_started']
    assert report['added_images'] == report['added_layers'] == 0
    assert len(report['changed_material_files']) == 6
    expected = read(S / 'native_expected_inputs.json')
    pinned = read(R / 'BUILD/v067_pinned_expected.json')
    if expected != pinned:
        differences = []
        for key in sorted(set(expected) | set(pinned)):
            actual, saved = expected.get(key), pinned.get(key)
            if isinstance(actual, dict) and isinstance(saved, dict):
                for name in sorted(set(actual) | set(saved)):
                    if actual.get(name) != saved.get(name):
                        differences.append((key + '.' + name, saved.get(name), actual.get(name)))
            elif actual != saved:
                differences.append((key, saved, actual))
        for key, old_hash, new_hash in differences:
            print('V067_SOURCE_HASH_MISMATCH', key, 'preview=',old_hash, 'windows=',new_hash, flush=True)
        raise AssertionError('Generated v067 source differs from approved preview: ' +
                             str(len(differences)) + ' mismatches; see exact file hashes above')
    assets = dict(terrain='terrain.raw', scenery='scenery.fbx', hmf='compiled_track.hmf',
                  main_route='main.tcl', start_route='start.tcl',
                  daylight='trial_daylight.amb', map_params='map_params.ini')
    for key,filename in assets.items():
        assert sha(O / filename) == expected[key], (key,filename)
    assert sha(BASE_BUILD / 'v054_track.tht') == expected['physical_declarations'] == PHYSICS_SHA
    assert sha(SAVED / 'scenery.edf') == expected['native_scenery'] == EDF_SHA
    for name in ['terrain.raw','scenery.fbx','compiled_track.hmf','main.tcl','start.tcl','route.npz']:
        assert sha(O / name) == sha(B / name), name
    for row in report['active_terrain_inventory']:
        assert sha(source(row['file'])) == expected['terrain_images'][row['file']], row['file']
    for row in report['active_shaders']:
        assert sha(source(row['file'])) == expected['terrain_shaders'][row['file']], row['file']
    assert len(report['active_terrain_inventory']) == len(expected['terrain_images'])
    assert len(report['active_shaders']) == len(expected['terrain_shaders'])
    assert validate_pair((O / 'trial_daylight.amb').read_text(),
                         (O / 'map_params.ini').read_text())['synchronized_baked_and_runtime_sun']
    assert abs(report['lighting']['sun_elevation_degrees'] - 45) < 0.001
    print('V067_SOURCE_CHECK_PASS; pinned materials, preserved geometry, approved native build', flush=True)


def prepare_game():
    verify_candidate()
    DEST.mkdir(parents=True, exist_ok=True)
    expected_names = set()
    for path in sorted(previous.DEST.iterdir()):
        if not path.is_file():
            continue
        name = path.name.replace('v066', 'v067')
        target = DEST / name
        expected_names.add(name)
        if path.suffix.lower() == '.amb':
            copy_exact(O / 'trial_daylight.amb', target)
        elif path.suffix.lower() == '.ini':
            target.write_text(path.read_text(encoding='utf-8').replace('v066','v067'),
                              encoding='utf-8', newline='\n')
        else:
            copy_exact(path,target)
    assert len(expected_names) == 11 and {p.name for p in DEST.iterdir()} == expected_names
    assert sha(DEST / (NAME + '.amb')) == read(S / 'native_expected_inputs.json')['daylight']
    for item in previous.DEST.iterdir():
        if item.suffix.lower() not in ['.ini','.amb']:
            assert sha(DEST / item.name.replace('v066','v067')) == sha(item)
    copy_exact(B / 'race_validation.json', O / 'race_validation.json')
    save(O / 'precompile_validation.json', read(S / 'precompile_validation.json'))
    assert read(O / 'race_validation.json')['checks_pass']
    print('V067_GAME_PREP_PASS; separate game directory, v066 intact', flush=True)


def check():
    verify_candidate()
    assert (DEST / (NAME + '.amb')).is_file(), 'Call prepare_game before staging'
    assert sha(DEST / (NAME + '.amb')) == read(S / 'native_expected_inputs.json')['daylight']
    assert read(O / 'precompile_validation.json')['checks_pass']
    assert read(O / 'race_validation.json')['checks_pass']
    validate_pair((DEST / (NAME+'.amb')).read_text(),(O / 'map_params.ini').read_text())


if __name__ == '__main__':
    prepare_game()
