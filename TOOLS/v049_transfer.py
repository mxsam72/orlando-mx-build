"""Pinned inputs, durable checkpoints, and publication of the v049 benchmark."""
import concurrent.futures,io,json,os,shutil,sys,urllib.parse,urllib.request,zipfile
from pathlib import Path
from v049_surface import R,BASE,DIRT,O,M,sha,save
from download_v048_inputs import INPUTS,download

REPOSITORY='mxsam72/orlando-mx-build';API='https://api.github.com/repos/'+REPOSITORY
HEADERS={'Authorization':'Bearer '+os.environ.get('V049_RELEASE_TOKEN',''),'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v049-build'}
RELEASE_IDS={'untagged-281f90b2ce09d3a57800':411058375,'v046-persistent-dirt-38405384917':411710729,'v047-realistic-trees-38458081921':412053683}
def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers=HEADERS|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def identity():
    j=api('');assert j['id']==1368050549 and j['full_name']==REPOSITORY and j['visibility']=='public' and not j['private']
def safe(name):
    p=Path(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name;return p
def extract(z,i,p):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(i) as a,p.open('wb') as b:shutil.copyfileobj(a,b,4*1024*1024)
def restore():
    identity();releases={}
    for tag,rid in RELEASE_IDS.items():
        rel=api('/releases/'+str(rid));assert not rel['draft'] and rel['tag_name']==tag
        releases[tag]={a['name']:a for a in rel['assets']}
    for name,(url,size,digest) in INPUTS.items():
        tag,asset=url.split('/',1);a=releases[tag][asset]
        assert a['size']==size and a['digest']=='sha256:'+digest,(name,'release pin mismatch')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(download,INPUTS.items()))
    inputs=R/'BUILD/v048_inputs'
    with zipfile.ZipFile(inputs/'v044_source.zip') as z:
        for i in z.infolist():
            safe(i.filename)
            keep=i.filename.startswith(('V044_OUTPUT/materials/','V044_OUTPUT/masks/'))
            keep|=i.filename in ['V044_OUTPUT/terrain.raw','V044_OUTPUT/route.npz','V044_OUTPUT/compiled_track.hmf','V044_OUTPUT/geometry_spec.json','V044_OUTPUT/jump_profiles.json','V044_OUTPUT/v024_pit_gravel.tga','BUILD/tool_versions.json','BUILD/map_params.ini']
            if keep and not i.is_dir():extract(z,i,R/i.filename)
        parts=sorted(n for n in z.namelist() if n.startswith('BUILD_INPUTS/native_inputs.zip.part'))
        with zipfile.ZipFile(io.BytesIO(b''.join(z.read(n) for n in parts))) as inner:
            extract(inner,inner.getinfo('05_NORMALS/grass_n.tga'),BASE/'grass_n.tga')
            extract(inner,inner.getinfo('04_TEXTURES/basemap.tga'),BASE/'basemap.tga')
    with zipfile.ZipFile(inputs/'v046_source.zip') as z:
        for i in z.infolist():
            safe(i.filename)
            if not i.is_dir() and i.filename.startswith(('V046_OUTPUT/','V046_SOURCE/')):extract(z,i,R/i.filename)
    baseline=json.loads((inputs/'v047_validation.json').read_text())
    assert baseline['compiled'] and baseline['source_checks'] and baseline['native_trh_identical_to_v046']
    assert baseline['object_texture_validation']['checks_pass'] and baseline['native_coordinate_validation']['checks_pass']
    with zipfile.ZipFile(inputs/'v047_native.zip') as z:extract(z,z.getinfo('scenery.edf'),R/'BUILD/v049_stage/scenery.edf')
    assert sha(R/'BUILD/v049_stage/scenery.edf')==baseline['scenery_edf_sha256']=='967ed6e8e393e0f83a504219f11bb8d271ed725326de8ab9d0d2ce604992ab2b'
    with zipfile.ZipFile(inputs/'v047.pkz') as z:
        assert len(z.infolist())==13
        for i in z.infolist():
            safe(i.filename);assert i.filename.startswith('orlandomx_2026_v047/')
            if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,R/'BUILD/v049_baseline_game'/Path(i.filename).name)
    for row in baseline['retained_game_files']:assert sha(R/'BUILD/v049_baseline_game'/row['file'])==row['sha256'],row['file']
    q=json.loads((DIRT/'v046_surface_validation.json').read_text());assert q['checks_pass']
    for name,digest in q['baseline_files'].items():assert sha(BASE/name)==digest,name
    for name,row in q['new_files'].items():assert sha(DIRT/name)==row['sha256'],name
    save(R/'BUILD/v049_input_validation.json',dict(checks_pass=True,pinned_assets=INPUTS,baseline_game_version='v047',scenery_edf_sha256=baseline['scenery_edf_sha256'],all_baseline_terrain_and_dirt_sources_authenticated=True))
    for p in inputs.iterdir():
        if p.suffix in ['.zip','.pkz','.part']:p.unlink()
    reference=R/'BUILD/v048_inputs/v048_validation.json'
    url='https://github.com/mxsam72/orlando-mx-build/releases/download/v048-tabletop-dirt-38474799178/OrlandoMX_v048_Validation.json'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OrlandoMX-v049-reference'}),timeout=120).read()
    import hashlib
    assert len(data)==46523 and hashlib.sha256(data).hexdigest()=='29405bde223fe3508ec6bf31a9201c7a00fa1775cfdb57b0f2058cbadcf6e65f'
    reference.write_bytes(data)
    print('Restored exact v047 trees/collision/race data and v046/v044 terrain inputs.',flush=True)
def upload(rel,p):
    p=Path(p);digest=sha(p)
    existing=next((a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name),None)
    if existing:
        assert existing['size']==p.stat().st_size and existing['digest']=='sha256:'+digest;return existing
    url=rel['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as response:a=json.load(response)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+digest
    print('Preserved release asset',p.name,p.stat().st_size,flush=True);return a
def checkpoint():
    identity();q=json.loads((O/'v049_surface_validation.json').read_text());assert q['checks_pass'] and q['pixels_changed_outside_sample']==0
    p=R/'BUILD/OrlandoMX-v049-dirt-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V049_OUTPUT','V049_SOURCE','BUILD/v049_authoring_renders']:
            for f in sorted((R/folder).rglob('*')):
                if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in [*sorted((R/'TOOLS').glob('*v049*.py')),R/'BUILD/v049_input_validation.json',R/'BUILD/v048_inputs/v047_validation.json']:
            z.write(f,f.relative_to(R).as_posix())
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    descriptor=R/'BUILD/v049_checkpoint_descriptor.json';save(descriptor,dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),pinned_inputs=INPUTS,source_commit=os.environ['GITHUB_SHA']))
    rel=api('/releases',dict(tag_name='v049-matte-dirt-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX v049 matte dirt through triple — compilation pending',draft=True,prerelease=True,make_latest='false',body='Accepted colour and matte specular restored; improved existing normal/wear detail extends through all three triple crests. 14 layers, no added textures. Exact v047 scenery/collision retained; native compilation and size-budget gates pending.'))
    for f in [p,descriptor]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as e:e.write('V049_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V049_RELEASE_ID',rel['id'],flush=True)
def preserve_native():
    rel=api('/releases/'+os.environ['V049_RELEASE_ID']);assert rel['draft']
    for name in ['OrlandoMX_2026_v049.pkz','OrlandoMX_2026_v049.pkz.sha256']:upload(rel,R/'12_RELEASE'/name)
def deliver():
    identity();q=json.loads((R/'12_RELEASE/OrlandoMX_v049_Validation.json').read_text())
    assert q['compiled'] and q['source_checks'] and q['native_trh_identical_to_v047'] and q['native_scenery_identical_to_v047']
    assert q['surface_validation']['pixels_changed_outside_sample']==0
    assert q['object_texture_validation']['checks_pass'] and q['native_coordinate_validation']['checks_pass']
    rel=api('/releases/'+os.environ['V049_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==q['source_commit']
    for f in [R/'12_RELEASE/OrlandoMX_v049_Validation.json',R/'12_RELEASE/Install_v049.txt',O/'v049_surface_validation.json',R/'BUILD/v049_authoring_renders/manifest.json']:
        upload(rel,f)
    for f in sorted((R/'BUILD/v049_authoring_renders').glob('comparison_*.jpg')):upload(rel,f)
    body=f'''Matte accepted-colour dirt from the finish tabletop through the complete triple and its exit (station -3 to 190 m). Every accepted v046 colour map, photographic soil tile and shader remains byte-identical. Specular alpha is the accepted 2/255; removed the full-strength RGB clod normal responsible for v048 glare. Improved slope-aligned furrows, compact crests, wheel wear, churn and bank erosion cover R01, its connector, all three R02 crests and the exit. R03 and the rest of the circuit retain the accepted dirt.

Optimization: return from 16 to the exact accepted 14-layer HMF. No added textures, masks, resolutions or per-section atlases: only the existing macro normal atlas and wear mask are edited in scope. All original 4 m visual depths, v047 scenery/trees, collision, race/reset files and lighting remain exact.

Official native compilation, {len(q['terrain_texture_payloads'])} terrain bitmap checks, 92 object records, {q['native_coordinate_validation']['probes']} scenery probes, collision hashes and 13-entry PKZ CRC checks passed. PKZ {q['pkz_bytes']:,} bytes; {q['pkz_reduction_vs_v048_percent']:.2f}% smaller than v048 and {q['pkz_size_delta_percent']:+.2f}% versus v047. Both size-budget gates passed.

Comparison JPGs are matched actual-source renders with an approximate specular stress light, not game footage. Reset the track, compare in matching dry weather/camera, then ride with usual deformation enabled. In-game colour/glare, persistence and FPS require user testing.'''
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v049 — matte dirt through the triple, optimized',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
    save(R/'BUILD/v049_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=q['source_commit'],pkz_sha256=q['pkz_sha256'],pkz_bytes=q['pkz_bytes']))
    print('V049_RELEASE',rel['id'],rel['html_url'],flush=True)
    print('V049_DOWNLOAD',next(a['browser_download_url'] for a in api('/releases/'+str(rel['id']))['assets'] if a['name']=='OrlandoMX_2026_v049.pkz'),flush=True)
def diagnostics():
    if not os.environ.get('V049_RELEASE_ID'):return
    p=R/'BUILD'/('v049_diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in [*sorted((R/'DOCUMENTATION').glob('*v049*')),*sorted(O.glob('*.json'))]:
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(api('/releases/'+os.environ['V049_RELEASE_ID']),p)
if __name__=='__main__':{'restore':restore,'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
