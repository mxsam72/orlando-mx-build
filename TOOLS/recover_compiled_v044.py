"""Validate and deliver the authenticated existing v044 compilation."""
# Recovery supports the exact repository after its owner-authorized public conversion.
import os, re, shutil
from v044_common import R, O, M, NAME, read, save, sha
from inspect_native_bitmap_records import restore_candidate, texture_paths, NATIVE_COMMIT, PKZ_SHA256, RELEASE_ID
from build_windows_v044 import validate_native_outputs
from v044_release_transfer import deliver
from scene_texture_bindings_v044 import inspect as inspect_bindings

def main():
    assert os.environ['V044_SOURCE_RELEASE_ID'] == str(RELEASE_ID)
    restore_candidate()
    all_textures = texture_paths()
    bindings = inspect_bindings(O / 'scenery.fbx')
    available = {p.name: p for p in all_textures}
    assert set(bindings['actual_diffuse_textures']) <= set(available)
    obsolete = set(available) - set(bindings['actual_diffuse_textures'])
    assert obsolete <= set(bindings['obsolete_relative_filename_hints']), ('Unexplained inactive texture references', sorted(obsolete))
    textures = [available[name] for name in bindings['actual_diffuse_textures']]
    bindings['checks_pass'] = True
    bindings['staging_only_relative_hints'] = sorted(obsolete)
    save(O / 'v044_actual_texture_binding_validation.json', bindings)
    print('Actual FBX diffuse bindings: ' + str(len(textures)) + '; independently confirmed old relative hints: ' + str(sorted(obsolete)), flush=True)
    stage = R / 'BUILD/v044_validation_stage'
    stage.mkdir(parents=True, exist_ok=True)
    text = (O / 'compiled_track.hmf').read_text()
    names = set(re.findall(r'(?m)^\s*map\s*=\s*(\S+)', text))
    for name in list(names):
        shader = M / (name[:-4] + '.shd')
        if shader.is_file():
            names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)', shader.read_text()))
    for name in sorted(names):
        assert name == os.path.basename(name)
        candidates = [M / name, O / name, R / 'BUILD/v009_work/04_TEXTURES' / name, R / 'BUILD/v009_work/05_NORMALS' / name]
        source = next((p for p in candidates if p.is_file()), None)
        assert source is not None, ('Saved terrain texture unresolved', name)
        shutil.copy2(source, stage / name)
        assert sha(source) == sha(stage / name)
    print('Reusing saved compiled files; all original final checks run again.', flush=True)
    validate_native_outputs(stage, object_textures=textures, native_source_commit=NATIVE_COMMIT)
    validation = read(R / '12_RELEASE/OrlandoMX_v044_Validation.json')
    assert validation['pkz_sha256'] == PKZ_SHA256
    validation['actual_texture_binding_validation'] = bindings
    validation['native_checkpoint_recovery'] = dict(checks_pass=True, source_release_id=RELEASE_ID,
                                                    native_source_commit=NATIVE_COMMIT,
                                                    validation_commit=os.environ['GITHUB_SHA'],
                                                    native_files_recompiled=False, pkz_unchanged=True)
    save(R / '12_RELEASE/OrlandoMX_v044_Validation.json', validation)
    deliver()

if __name__ == '__main__':
    main()
