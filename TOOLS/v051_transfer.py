"""Authenticated inputs, durable checkpoints and gated v051 publication."""
import concurrent.futures,hashlib,io,json,os,shutil,sys,urllib.parse,urllib.request,zipfile
from pathlib import Path
from v051_surface import R,BASE,DIRT,O,sha,save
from download_v048_inputs import INPUTS as OLD_INPUTS,download
from v049_transfer import safe,extract

REPOSITORY='mxsam72/orlando-mx-build';API='https://api.github.com/repos/'+REPOSITORY
HEADERS={'Authorization':'Bearer '+os.environ.get('V051_RELEASE_TOKEN',''),'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v051-build'}
EXTRA={'v047_source.zip':('v047-realistic-trees-38458081921/OrlandoMX-v047-tree-source-checkpoint.zip',292379577,'0a1f44d74eef2908a17e120fac9eed7ad9ec416fa693c51d0c6a08c83749cdf1'),
       'v050_validation.json':('v050-natural-dirt-grass-38497104967/OrlandoMX_v050_Validation.json',94565,'3554b5df843b08d2907d954b650c0f80667e59eac40f0dd01bd15a22bd1b604f')}
INPUTS={k:v for k,v in OLD_INPUTS.items() if k!='v047_native.zip'}|EXTRA
def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers=HEADERS|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def identity():
    j=api('');assert j['id']==1368050549 and j['full_name']==REPOSITORY and j['visibility']=='public' and not j['private']
def restore():
    identity();tags={}
    for name,(url,size,digest) in INPUTS.items():
        tag,asset=url.split('/',1)
        if tag not in tags:
            rel=api('/releases/tags/'+tag);assert not rel['draft'];tags[tag]={a['name']:a for a in rel['assets']}
        a=tags[tag][asset];assert a['size']==size and a['digest']=='sha256:'+digest,(name,'release pin mismatch')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(download,INPUTS.items()))
    inputs=R/'BUILD/v048_inputs'
    with zipfile.ZipFile(inputs/'v044_source.zip') as z:
        for i in z.infolist():
            safe(i.filename)
            keep=i.filename.startswith(('V044_OUTPUT/materials/','V044_OUTPUT/masks/','V044_OUTPUT/facility_textures/','BUILD/v044_assets/grass_bermuda_01/'))
            keep|=i.filename in ['V044_OUTPUT/terrain.raw','V044_OUTPUT/route.npz','V044_OUTPUT/compiled_track.hmf','V044_OUTPUT/geometry_spec.json','V044_OUTPUT/jump_profiles.json','V044_OUTPUT/v024_pit_gravel.tga','BUILD/tool_versions.json','BUILD/map_params.ini','BUILD/edf_params.ini','BUILD/v044_assets/grass_bermuda_01_metadata.json']
            if keep and not i.is_dir():extract(z,i,R/i.filename)
        parts=sorted(n for n in z.namelist() if n.startswith('BUILD_INPUTS/native_inputs.zip.part'))
        with zipfile.ZipFile(io.BytesIO(b''.join(z.read(n) for n in parts))) as inner:
            extract(inner,inner.getinfo('05_NORMALS/grass_n.tga'),BASE/'grass_n.tga');extract(inner,inner.getinfo('04_TEXTURES/basemap.tga'),BASE/'basemap.tga')
    with zipfile.ZipFile(inputs/'v046_source.zip') as z:
        for i in z.infolist():
            safe(i.filename)
            if not i.is_dir() and i.filename.startswith(('V046_OUTPUT/','V046_SOURCE/')):extract(z,i,R/i.filename)
    with zipfile.ZipFile(inputs/'v047_source.zip') as z:
        for i in z.infolist():
            safe(i.filename)
            if not i.is_dir() and i.filename.startswith(('V047_OUTPUT/','V047_SOURCE/')):extract(z,i,R/i.filename)
    baseline=json.loads((inputs/'v047_validation.json').read_text());latest=json.loads((inputs/'v050_validation.json').read_text())
    assert baseline['compiled'] and latest['compiled'] and latest['grass_validation']['all_non_grass_records_exact'] and latest['native_trh_identical_to_v049']
    assert latest['pkz_bytes']==919035723 and latest['pkz_sha256']=='b3c5e808f03f53c461630ad5f8e188aa61e9b0a6c5f28b62dc3f3cc659067365'
    assert sha(R/'V047_OUTPUT/scenery.fbx')==baseline['tree_validation']['scenery_sha256']
    with zipfile.ZipFile(inputs/'v047.pkz') as z:
        assert len(z.infolist())==13
        for i in z.infolist():
            safe(i.filename);assert i.filename.startswith('orlandomx_2026_v047/')
            if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,R/'BUILD/v049_baseline_game'/Path(i.filename).name)
    for row in baseline['retained_game_files']:assert sha(R/'BUILD/v049_baseline_game'/row['file'])==row['sha256'],row['file']
    q=json.loads((DIRT/'v046_surface_validation.json').read_text());assert q['checks_pass']
    for name,digest in q['baseline_files'].items():assert sha(BASE/name)==digest,name
    for name,row in q['new_files'].items():assert sha(DIRT/name)==row['sha256'],name
    save(R/'BUILD/v051_input_validation.json',dict(checks_pass=True,pinned_assets=INPUTS,source_scenery_sha256=sha(R/'V047_OUTPUT/scenery.fbx'),
        baseline_version='v050',baseline_game_graphics_scenery_version='v047',latest_pkz_sha256=latest['pkz_sha256'],latest_pkz_bytes=latest['pkz_bytes'],
        exact_v050_collision_race_and_lighting=True,authenticated_photographic_grass_source=True))
    for p in inputs.iterdir():
        if p.suffix in ['.zip','.pkz','.part']:p.unlink()
    print('Authenticated delivered trees, collision, accepted soil tiles and real photographic grass.',flush=True)
def upload(rel,p):
    p=Path(p);digest=sha(p);existing=next((a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name),None)
    if existing:
        assert existing['size']==p.stat().st_size and existing['digest']=='sha256:'+digest;return existing
    url=rel['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as response:a=json.load(response)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+digest
    print('Preserved',p.name,p.stat().st_size,flush=True);return a
def checkpoint():
    identity();d=json.loads((O/'v051_surface_validation.json').read_text());g=json.loads((O/'v051_scenery_validation.json').read_text())
    assert d['checks_pass'] and g['checks_pass'] and d['pixels_changed_outside_corridor']==0 and g['all_non_grass_records_exact']
    p=R/'BUILD/OrlandoMX-v051-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V051_OUTPUT','V051_SOURCE','BUILD/v051_review']:
            if (R/folder).exists():
                for f in sorted((R/folder).rglob('*')):
                    if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in [*sorted((R/'TOOLS').glob('*v051*.py')),R/'BUILD/v051_input_validation.json',R/'BUILD/v048_inputs/v050_validation.json']:
            z.write(f,f.relative_to(R).as_posix())
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    descriptor=R/'BUILD/v051_checkpoint_descriptor.json';save(descriptor,dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),pinned_inputs=INPUTS,source_commit=os.environ['GITHUB_SHA']))
    rel=api('/releases',dict(tag_name='v051-natural-dirt-grass-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],
        name='Orlando MX v051 greener dense grass, directional grooming and layer trials — compilation pending',draft=True,prerelease=True,make_latest='false',
        body='Whole-track matte dirt without continuous pale lanes; photographic double-sided grass without panel shadows. 14 terrain layers and shared atlas pair, no added terrain textures. Exact approved trees, collision and facilities retained. Native checks and fixed size gate pending.'))
    for f in [p,descriptor]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as e:e.write('V051_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V051_RELEASE_ID',rel['id'],flush=True)
def preserve_edf():
    p=R/'BUILD/OrlandoMX-v051-native-scenery.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(R/'BUILD/v051_stage/scenery.edf','scenery.edf');z.write(R/'DOCUMENTATION/fbx2edf_v051.log','fbx2edf_v051.log')
    upload(api('/releases/'+os.environ['V051_RELEASE_ID']),p)
def preserve_native():
    rel=api('/releases/'+os.environ['V051_RELEASE_ID']);assert rel['draft']
    for name in ['OrlandoMX_2026_v051.pkz','OrlandoMX_2026_v051.pkz.sha256']:upload(rel,R/'12_RELEASE'/name)
def deliver():
    identity();q=json.loads((R/'12_RELEASE/OrlandoMX_v051_Validation.json').read_text())
    assert q['compiled'] and q['source_checks'] and q['native_trh_identical_to_v050'] and q['race_reset_and_lighting_identical_to_v050']
    assert q['surface_validation']['pixels_changed_outside_corridor']==0 and q['surface_validation']['normal_specular_channel_identical']
    assert q['grass_validation']['all_non_grass_records_exact'] and q['grass_validation']['grass_mesh_front_back_normals_verified'] and q['grass_validation']['all_grass_no_shadow_native_prefix']
    assert q['object_texture_validation']['checks_pass'] and q['native_coordinate_validation']['checks_pass'] and q['package_size_budget_passed']
    rel=api('/releases/'+os.environ['V051_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==q['source_commit']
    for f in [R/'12_RELEASE/OrlandoMX_v051_Validation.json',R/'12_RELEASE/Install_v051.txt',O/'v051_surface_validation.json',O/'v051_scenery_validation.json',O/'v051_staging_validation.json',O/'v051_layer_trials.json',O/'v051_verge_validation.json']:upload(rel,f)
    if (R/'BUILD/v051_review').exists():
        for f in sorted((R/'BUILD/v051_review').glob('*.jpg')):upload(rel,f)
    g=q['grass_validation'];body=f'''Grass revised from v050: {g['grass_clumps']:,} photographic Bermuda clumps ({g['clump_count_vs_v050_ratio']:.2f} times v050) with 1.38 times blade width, natural 17–40 cm heights, green material tint, and transparent-edge RGB extrusion. Opaque photographic RGB and all alpha pixels remain exact to the scan. Mip colour checks remain green. Uses the existing terrain grass layer for green verge ground cover, excluding the riding corridor, roads and paddock. Double-sided normals and visual-only no-shadow prefixes retained.

Predominantly forward/back tractor grooming on the straightaways and jump faces: lower cross-grain clods, straighter furrows, less wandering scuffs, no transverse bank comb. Approved photographic soil colours and matte specular alpha retained, with no paired bright racing lanes.

Three independent legacy-layer trials: A at R03 table-single removes only layer2 prepared-soil overlay; B at R10 big tabletop removes only layer8 packed-soil overlay; C at R17 eight rollers removes only layer9 jump-face overlay. Each mask edit stays inside its own section. All other sections retain all historic overlays. Textures remain needed elsewhere; no global texture allocation has been removed. Source comparisons and a trial map identify each change. Same 14 layers and shared atlas pair.

All approved trees and every non-grass scenery record are exact. Native collision, road riding surfaces, race/reset files and lighting remain exact. Official native compilation, bitmap signatures, grass tint, geometry probes, retained file hashes and 13-entry ZIP CRC passed. Package {q['pkz_bytes']:,} bytes ({q['pkz_growth_vs_v050_percent']:+.2f}% vs v050). Changes include denser grass as well as the isolated trials, so the total package change is not an isolated per-trial size estimate.

Reset the track and compare in matching dry weather. In-game distance colour, full-lap grooming, each layer trial, dirt persistence and FPS still require a ride test. Supplied source previews are not MX Bikes screenshots.'''
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v051 — dense green grass, directional grooming and isolated layer trials',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
    save(R/'BUILD/v051_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=q['source_commit'],pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes']))
    print('V051_RELEASE',rel['id'],rel['html_url'],flush=True)
    print('V051_DOWNLOAD',next(a['browser_download_url'] for a in api('/releases/'+str(rel['id']))['assets'] if a['name']=='OrlandoMX_2026_v051.pkz'),flush=True)
def diagnostics():
    if not os.environ.get('V051_RELEASE_ID'):return
    p=R/'BUILD'/('v051_diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in [*sorted((R/'DOCUMENTATION').glob('*v051*')),*sorted(O.glob('*.json'))]:
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(api('/releases/'+os.environ['V051_RELEASE_ID']),p)
if __name__=='__main__':{'restore':restore,'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
