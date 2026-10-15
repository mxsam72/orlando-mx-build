"""Preserve the combined material review and orientation evidence."""
import json,shutil,zipfile
from pathlib import Path
from PIL import Image
from v058_trials import R,S,PREV,sha,save

OUT=R/'BUILD/v058_hybrid_review'

def main():
    material=json.loads((OUT/'hybrid_validation.json').read_text())
    orientation=json.loads((OUT/'orientation_validation.json').read_text())
    assert material['checks_pass'] and orientation['checks_pass']
    assert not material['native_build_started'] and not orientation['new_native_build_started']
    assert len(material['face_checks'])==4 and all(r['flat_pixels_exact_C'] for r in material['face_checks'])
    rows=[r for r in material['renders'] if r['method'] in ['B','C','H']]
    assert len(rows)==12 and all(r['changes_outside_section']==0 for r in rows)
    for row in rows:assert sha(OUT/row['file'])==row['sha256']
    assert sha(PREV/'terrain.raw')==material['terrain_sha256']
    assert sha(R/'V057_OUTPUT/scenery.fbx')==material['scenery_sha256']==orientation['scenery_sha256']
    # The same original B/C controls must remain identical to the first review.
    for row in rows:
        if row['method'] in ['B','C']:
            assert sha(R/'BUILD/v058_review'/row['file'])==row['sha256'],('Control drift',row['file'])
    shutil.copy2(R/'BUILD/v058_review/Van_Sign_Current_Placement.jpg',OUT/'Van_Sign_Current_Placement.jpg')
    shutil.copy2(S/'HYBRID_REVIEW.md',OUT/'README.md')
    images=[OUT/r['file'] for r in rows]+sorted(OUT.glob('Hybrid_Comparison_*.jpg'))+[OUT/'Orlando_Dirt_C_With_B_Jump_Grooves_4Views.jpg',OUT/'Van_Sign_Current_Placement.jpg',OUT/'Sign_Front_Back_Orientation_Check.jpg']
    assert len(images)==19
    for path in images:
        with Image.open(path) as im:im.verify()
    report=dict(checks_pass=True,matched_material_views=12,comparison_rows=4,complete_four_view_sheet=True,
        original_B_and_C_controls_exact=True,flat_and_deck_material_exact_C=True,
        approved_terrain_and_scenery_exact=True,legacy_preview_orientation_corrected=True,
        sign_native_projection_contract_checked=True,native_game_sign_appearance_verified=False,
        full_build_started=False,adds_material_images=False,adds_terrain_layers=False,
        images=[dict(file=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in images])
    save(S/'hybrid_review_validation.json',report);save(OUT/'review_validation.json',report)
    archive=R/'BUILD/Orlando_Dirt_Hybrid_v058.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in images:z.write(path,'Orlando_Dirt_Hybrid_v058/'+path.name)
        for name in ['README.md','hybrid_validation.json','orientation_validation.json','review_validation.json']:
            z.write(OUT/name,'Orlando_Dirt_Hybrid_v058/'+name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    save(OUT/'package.json',dict(file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive)))
    print(json.dumps(dict(checks_pass=True,file=str(archive),bytes=archive.stat().st_size,sha256=sha(archive))))

if __name__=='__main__':main()
