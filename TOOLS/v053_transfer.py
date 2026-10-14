"""Durable source checkpoints and publication gated by native v053 validation."""
import json,os,zipfile
from pathlib import Path
from v053_surface import R,O,sha,save
from v052_transfer import api,identity,upload
from v053_inputs import PINS

def checkpoint():
    identity(); d=json.loads((O/'v053_surface_validation.json').read_text()); g=json.loads((O/'v053_scenery_validation.json').read_text())
    assert d['checks_pass'] and d['pixels_changed_outside_corridor']==0 and g['grass_clumps']==4546 and g['all_non_grass_records_exact']
    p=R/'BUILD/OrlandoMX-v053-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V053_OUTPUT','V053_SOURCE','BUILD/v053_review']:
            for f in sorted((R/folder).rglob('*')):
                if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in [*sorted((R/'TOOLS').glob('*v053*.py')),R/'BUILD/v053_input_validation.json',R/'BUILD/v053_recovery.json']:
            z.write(f,f.relative_to(R).as_posix())
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    descriptor=R/'BUILD/v053_checkpoint_descriptor.json'
    save(descriptor,dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),pinned_v052_assets=PINS,source_commit=os.environ['GITHUB_SHA']))
    rel=api('/releases',dict(tag_name='v053-dirt-refinement-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],
        name='Orlando MX v053 dirt refinement — native validation pending',draft=True,prerelease=True,make_latest='false',
        body='Finer soil grain, narrower travel-aligned grooming, local curved tyre marks, landing compaction and irregular dirt edges. Exact v052 scene, grass, foliage, geometry and legacy trials retained.'))
    for f in [p,descriptor]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as env:env.write('V053_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V053_RELEASE_ID',rel['id'],flush=True)

def preserve_edf():
    recovery=json.loads((R/'BUILD/v053_recovery.json').read_text())
    p=R/'BUILD/OrlandoMX-v052-native-scenery.zip'
    assert sha(p)==PINS[p.name][1] and sha(R/'BUILD/v053_stage/scenery.edf')==recovery['saved_edf_sha256']
    upload(api('/releases/'+os.environ['V053_RELEASE_ID']),p)

def preserve_native():
    rel=api('/releases/'+os.environ['V053_RELEASE_ID']); assert rel['draft']
    for name in ['OrlandoMX_2026_v053.pkz','OrlandoMX_2026_v053.pkz.sha256']:upload(rel,R/'12_RELEASE'/name)

def deliver():
    identity(); q=json.loads((R/'12_RELEASE/OrlandoMX_v053_Validation.json').read_text()); d=q['surface_validation']
    assert q['compiled'] and q['source_checks'] and q['native_trh_identical_to_v050'] and q['race_reset_and_lighting_identical_to_v050']
    assert d['checks_pass'] and d['pixels_changed_outside_corridor']==0 and d['normal_specular_channel_identical']
    assert d['dirt_comparison_to_v052']['checks_pass'] and d['photographic_micro_normal_tiles_identical'] and d['hmf_identical_to_v052']
    assert all(p['checks_pass'] and p['fine_grain_contrast_ratio']>1.08 for p in d['photographic_grain_validation'].values())
    assert d['grass_ground_mask_identical_to_v052'] and d['isolated_layer_trials_identical_to_v052']
    assert q['grass_validation']['all_non_grass_records_exact'] and q['grass_validation']['grass_clumps']==4546
    assert q['object_texture_validation']['checks_pass'] and q['native_coordinate_validation']['checks_pass'] and q['package_size_budget_passed']
    assert q['foliage_validation']['native_bitmap_preflight_passed'] and q['foliage_validation']['specular_alpha_max']==0
    rel=api('/releases/'+os.environ['V053_RELEASE_ID']); assert rel['draft'] and rel['target_commitish']==q['source_commit']
    for f in [R/'12_RELEASE/OrlandoMX_v053_Validation.json',R/'12_RELEASE/Install_v053.txt',*sorted(O.glob('v053_*.json')),R/'BUILD/v053_review/manifest.json']:
        upload(rel,f)
    for f in sorted((R/'BUILD/v053_review').glob('*.jpg')):upload(rel,f)
    body=f'''Dirt refinement based on the latest rider video.

Fine photographic soil detail has approximately 20% more local grain contrast, a small warm colour adjustment (RGB approximately +3,-2,-1), and substantially more contribution beneath the route atlas. Exact photographic normal maps and matte specular alpha 2 remain.

Grooming uses narrower, irregularly spaced longitudinal furrows, about 28 cm apart, following the route and jump faces. Corner tyre fragments follow the local turning arc. Broken landing and run-out compaction differentiates impact areas. Irregular edge mixing stays entirely within the previous dirt footprint; no new grass coverage is added.

Same 14 layers, texture names, image dimensions and shader bindings. All approved riding geometry, native collision, road surfaces, race/reset files, lighting, v052 grass, tree foliage, facilities and the three isolated legacy-layer trial masks remain exact. Reuses the delivered v052 official scenery export, verified by SHA256.

Official TerrainEd compilation, source scope checks, native bitmap signatures, foliage alpha decoding, geometry probes, retained file hashes and 13-entry archive CRC passed. Package {q['pkz_bytes']:,} bytes; SHA256 {q['pkz_sha256']}. Matched source previews are labelled; final game appearance and FPS require a ride test.'''
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v053 — finer dirt, directional grooming and local wear',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
    save(R/'BUILD/v053_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=q['source_commit'],pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes']))
    print('V053_RELEASE',rel['id'],rel['html_url'],flush=True)
    print('V053_DOWNLOAD',next(a['browser_download_url'] for a in api('/releases/'+str(rel['id']))['assets'] if a['name']=='OrlandoMX_2026_v053.pkz'),flush=True)

def diagnostics():
    if not os.environ.get('V053_RELEASE_ID'):return
    p=R/'BUILD'/('v053_diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in [*sorted((R/'DOCUMENTATION').glob('*v053*')),*sorted(O.glob('*.json'))]:
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(api('/releases/'+os.environ['V053_RELEASE_ID']),p)
if __name__=='__main__':
    import sys
    {'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
