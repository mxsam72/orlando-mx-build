"""Check and package the dirt comparison; never invoke a native build."""
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image
from v058_trials import R, PREV, O, S, OUT, sha, save


def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    rows=manifest['renders']
    methods={'v056','A','B','C'}
    views={'01_tabletop','02_flat','03_triple','04_close'}
    assert len(rows)==16 and {(r['method'],r['view']) for r in rows}=={(m,v) for m in methods for v in views}
    assert manifest['source_only'] and manifest['not_game_captures']
    assert manifest['matching_camera_terrain_lighting']
    assert manifest['corrected_perspective_texture_sampling']
    for view in views:
        subset=[r for r in rows if r['view']==view]
        assert all(r['eye_xzy_m']==subset[0]['eye_xzy_m'] and r['target_xzy_m']==subset[0]['target_xzy_m'] for r in subset)
    for row in rows:
        assert sha(OUT/row['file'])==row['sha256']
        assert row['changes_outside_section']==0
        with Image.open(OUT/row['file']) as im: assert im.size==(1600,1000)
        if row['method']=='B': assert row['mean_abs_normal_difference_to_v056']==0
    recipe=json.loads((S/'experiments.json').read_text())
    assert sha(PREV/'terrain.raw')==recipe['terrain_sha256']
    assert sha(R/'V057_OUTPUT/scenery.fbx')==recipe['approved_scenery_sha256']
    assert not recipe['production_integration']['native_build_started']
    assert recipe['production_integration']['approved_method'] is None
    validation=json.loads((O/'trial_validation.json').read_text())
    assert validation['checks_pass']
    shutil.copy2(S/'README.md',OUT/'README.md')
    shutil.copy2(S/'experiments.json',OUT/'experiments.json')
    save(S/'render_manifest.json',manifest)
    save(S/'trial_validation.json',dict(checks_pass=True,**recipe))
    image_paths=sorted(OUT.glob('*.jpg'))
    assert len(image_paths)==23
    report=dict(checks_pass=True,individual_views=16,method_sheets=3,all_method_grids=4,
        all_cameras_matched=True,all_image_hashes_match=True,all_dimensions_checked=True,
        material_changes_outside_section=0,B_normal_samples_exact_v056=True,
        terrain_and_approved_scenery_hashes_match=True,native_build_started=False,
        estimated_memory_only=True,photographic_source='existing checksum-pinned v056 assets',
        author_script_sha256=sha(R/'TOOLS/v058_trials.py'),
        renderer_script_sha256=sha(R/'TOOLS/v058_render.py'),
        images=[dict(file=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in image_paths])
    save(OUT/'review_validation.json',report)
    save(S/'review_validation.json',report)
    package=R/'BUILD/Orlando_Dirt_Trials_v058.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in image_paths: z.write(path,'Orlando_Dirt_Trials_v058/'+path.name)
        for name in ['README.md','experiments.json','manifest.json','review_validation.json']:
            z.write(OUT/name,'Orlando_Dirt_Trials_v058/'+name)
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None and len(z.infolist())==27
    save(OUT/'package.json',dict(file=package.name,bytes=package.stat().st_size,sha256=sha(package)))
    print(json.dumps(dict(checks_pass=True,images=len(image_paths),package=str(package),bytes=package.stat().st_size,sha256=sha(package)),indent=2))


if __name__=='__main__': main()
