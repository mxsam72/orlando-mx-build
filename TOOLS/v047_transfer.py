"""Restore pinned accepted payloads; checkpoint and publish the native v047."""
import io,os,shutil,sys,urllib.parse,urllib.request,zipfile
from v047_common import *

REPOSITORY='mxsam72/orlando-mx-build'
API='https://api.github.com/repos/'+REPOSITORY
HEADERS={'Authorization':'Bearer '+os.environ.get('V047_RELEASE_TOKEN',''),'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v047-build'}
def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers=HEADERS|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=180) as response:return json.load(response)
def identity():
    j=api('');assert j['id']==1368050549 and j['full_name']==REPOSITORY and j['visibility']=='public' and not j['private']
def safe_name(name):
    p=Path(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name;return p
def extract(z,i,p):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(i) as src,p.open('wb') as out:shutil.copyfileobj(src,out,4*1024*1024)
def download(name,asset):
    spec=PINNED_ASSETS[name];p=R/'BUILD'/name;p.parent.mkdir(parents=True,exist_ok=True)
    assert asset['size']==spec['bytes'] and asset['digest']=='sha256:'+spec['sha256']
    if not p.is_file() or p.stat().st_size!=spec['bytes'] or sha(p)!=spec['sha256']:
        req=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'OrlandoMX-v047-build'})
        temp=p.with_suffix(p.suffix+'.partial')
        with urllib.request.urlopen(req,timeout=300) as src,temp.open('wb') as out:shutil.copyfileobj(src,out,4*1024*1024)
        assert temp.stat().st_size==spec['bytes'] and sha(temp)==spec['sha256'];temp.replace(p)
    print('Verified released input',name,p.stat().st_size,flush=True);return p

def restore():
    identity();releases={};paths={}
    for name,spec in PINNED_ASSETS.items():
        if spec['release'] not in releases:releases[spec['release']]=api('/releases/'+str(spec['release']))
        rel=releases[spec['release']];assert not rel['draft'] and rel['tag_name']==spec['tag']
        a=next(a for a in rel['assets'] if a['name']==name);paths[name]=download(name,a)
    with zipfile.ZipFile(paths['OrlandoMX-v044-source-checkpoint.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            keep=i.filename.startswith(('V044_OUTPUT/materials/','V044_OUTPUT/masks/','V044_OUTPUT/facility_textures/'))
            keep|=i.filename in ['V044_OUTPUT/scenery.fbx','V044_OUTPUT/terrain.raw','V044_OUTPUT/route.npz','V044_OUTPUT/compiled_track.hmf','V044_OUTPUT/v044_source_validation.json','V044_OUTPUT/v024_pit_gravel.tga','BUILD/tool_versions.json','BUILD/map_params.ini','BUILD/edf_params.ini']
            if keep and not i.is_dir():extract(z,i,R/i.filename)
        parts=sorted(n for n in z.namelist() if n.startswith('BUILD_INPUTS/native_inputs.zip.part'))
        with zipfile.ZipFile(io.BytesIO(b''.join(z.read(n) for n in parts))) as inner:
            extract(inner,inner.getinfo('05_NORMALS/grass_n.tga'),BASE/'grass_n.tga')
            extract(inner,inner.getinfo('04_TEXTURES/basemap.tga'),BASE/'basemap.tga')
    with zipfile.ZipFile(paths['OrlandoMX-v046-dirt-source-checkpoint.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            if not i.is_dir() and (i.filename.startswith(('V046_OUTPUT/','V046_SOURCE/')) or i.filename=='BUILD/v046_baseline_validation.json'):extract(z,i,R/i.filename)
    with zipfile.ZipFile(paths['Orlando_Tree_Prototypes_Review.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            keep=i.filename.startswith(('textures/','source/')) or i.filename in ['review/Tree_A_LOD0.fbx','review/Tree_B_LOD0.fbx','review/prototype_validation.json']
            if keep and not i.is_dir():extract(z,i,TREES/i.filename)
    qa=read(paths['OrlandoMX_v046_Validation.json'])
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v044'] and qa['native_scenery_identical_to_v044']
    assert qa['pkz_sha256']==PINNED_ASSETS['OrlandoMX_2026_v046.pkz']['sha256']
    with zipfile.ZipFile(paths['OrlandoMX_2026_v046.pkz']) as z:
        assert len(z.infolist())==13
        for i in z.infolist():
            safe_name(i.filename);assert i.filename.startswith('orlandomx_2026_v046/')
            if not i.is_dir() and not i.filename.endswith('.map'):extract(z,i,R/'BUILD/v047_baseline_game'/Path(i.filename).name)
    for row in qa['retained_game_files']:assert sha(R/'BUILD/v047_baseline_game'/row['file'])==row['sha256']
    assert sha(BASE/'scenery.fbx')==SCENERY_SHA and sha(BASE/'terrain.raw')==TERRAIN_SHA
    assert sha(BASE/'grass_n.tga')=='4de81532bf419efdc60fee0ca3f377b89168371f6bf858ab4f2e7a773a6cf881'
    assert sha(BASE/'basemap.tga')=='75fc72427f37e57c711c9d73c002d7bdba10e8501ae25e9c0a60c79e08fdc5b1'
    proto=read(TREES/'review/prototype_validation.json');assert proto['foliage_normals_align_with_front_and_back_faces']
    for which,digest in TREE_SHA.items():assert sha(TREES/'review'/('Tree_'+which+'_LOD0.fbx'))==digest
    for name,item in qa['surface_validation']['new_files'].items():assert sha(DIRT/name)==item['sha256'],name
    for name,digest in qa['surface_validation']['baseline_files'].items():assert sha(BASE/name)==digest,name
    save(R/'BUILD/v047_input_validation.json',dict(checks_pass=True,pinned_assets=PINNED_ASSETS,approved_tree_fbxs=TREE_SHA,baseline_scenery_sha256=SCENERY_SHA,terrain_sha256=TERRAIN_SHA,dirt_files_identical_to_delivered_v046=True))
    # Release assets already preserve these exact archives; keep working disk free.
    for name,p in paths.items():
        if name.endswith(('.zip','.pkz')):p.unlink()
    print('Authenticated delivered v046 dirt/collision and approved final A/B models.',flush=True)

def upload(rel,p):
    p=Path(p);digest=sha(p);existing=next((a for a in api('/releases/'+str(rel['id']))['assets'] if a['name']==p.name),None)
    if existing:
        assert existing['size']==p.stat().st_size and existing['digest']=='sha256:'+digest;return existing
    url=rel['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=1800) as r:a=json.load(r)
    assert a['state']=='uploaded' and a['size']==p.stat().st_size and a['digest']=='sha256:'+digest
    print('Preserved',p.name,p.stat().st_size,flush=True);return a

def checkpoint():
    identity();q=read(O/'v047_scenery_validation.json');assert q['checks_pass'] and q['all_retained_geometry_exact']
    p=R/'BUILD/OrlandoMX-v047-tree-source-checkpoint.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for folder in ['V047_OUTPUT','V047_SOURCE']:
            for f in sorted((R/folder).rglob('*')):
                if f.is_file():z.write(f,f.relative_to(R).as_posix())
        for f in sorted((R/'TOOLS').glob('*v047*.py')):z.write(f,f.relative_to(R).as_posix())
        z.write(R/'BUILD/v047_input_validation.json','BUILD/v047_input_validation.json')
        z.write(R/'BUILD/OrlandoMX_v046_Validation.json','BUILD/OrlandoMX_v046_Validation.json')
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    desc=R/'BUILD/v047_checkpoint_descriptor.json';save(desc,dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p),pinned_input_assets=PINNED_ASSETS))
    rel=api('/releases',dict(tag_name='v047-realistic-trees-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX v047 approved tree replacement — compilation pending',draft=True,prerelease=True,make_latest='false',body='User-approved realistic trees: 85% airy pine A, 15% woodland B (rounded to whole trees). All old trees replaced, distant density reduced. Delivered v046 dirt and collision retained. Native compilation pending.'))
    for f in [p,desc]:upload(rel,f)
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as e:e.write('V047_RELEASE_ID='+str(rel['id'])+'\n')
    print('CODEX_V047_RELEASE_ID',rel['id'],flush=True)

def preserve_edf():
    p=R/'BUILD/OrlandoMX-v047-native-scenery.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(P/'scenery.edf','scenery.edf')
        z.write(R/'DOCUMENTATION/fbx2edf_v047.log','fbx2edf_v047.log')
    upload(api('/releases/'+os.environ['V047_RELEASE_ID']),p)
def preserve_native():
    rel=api('/releases/'+os.environ['V047_RELEASE_ID']);assert rel['draft']
    for name in ['OrlandoMX_2026_v047.pkz','OrlandoMX_2026_v047.pkz.sha256']:upload(rel,R/'12_RELEASE'/name)

def deliver():
    identity();qa=read(R/'12_RELEASE/OrlandoMX_v047_Validation.json')
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v046'] and qa['v046_dirt_preserved_exact']
    assert qa['object_texture_validation']['checks_pass'] and qa['native_coordinate_validation']['checks_pass']
    q=qa['tree_validation'];assert q['checks_pass'] and q['all_near_trees_preserved'] and q['foliage_face_normal_alignment_pass']
    rel=api('/releases/'+os.environ['V047_RELEASE_ID']);assert rel['draft'] and rel['target_commitish']==qa['source_commit']
    assert qa.get('validation_commit',qa['source_commit'])==os.environ['GITHUB_SHA']
    for p in [R/'12_RELEASE/OrlandoMX_v047_Validation.json',R/'12_RELEASE/Install_v047.txt',O/'v047_scenery_validation.json',O/'v047_staging_validation.json',O/'v047_tree_placement_preview.png']:upload(rel,p)
    styles=q['style_counts'];body=f'''Replaced all 369 old generic, scan and facility trees. Retained {q['tree_count_after']} approved realistic trees: {styles['A']} A airy pines and {styles['B']} B dense woodland trees (85/15 rounded). All near-course and facility placements remain; reduced distant density controls file size and rendering load. Sizes and yaw vary. Approved foliage pixels, per-corner UVs, front/back geometry and custom normals are preserved. Native color-key transparency and tree shading are configured.

Delivered v046 whole-track dirt textures, masks, HMF visual depths and all other terrain source files remain byte-identical. Native collision TRH, race/reset files and lighting remain byte-identical. All non-tree source geometry and shared material/media records remain exact. Official FBX2EDF and TerrainEd compilation plus active bitmap, retained/new geometry and archive checks passed. In-game appearance, foliage motion and FPS still require user testing.

PKZ: {qa['pkz_bytes']:,} bytes. Change from v046: {qa['pkz_size_delta_percent']:+.2f}%. Install alongside v046, choose Orlando MX 2026 v047 and compare in standard dry weather.'''
    rel=api('/releases/'+str(rel['id']),dict(name='Orlando MX v047 — realistic trees, 85% A / 15% B',body=body,draft=False,prerelease=True,make_latest='false'),method='PATCH')
    save(R/'BUILD/v047_delivery.json',dict(release_id=rel['id'],release_url=rel['html_url'],source_commit=os.environ['GITHUB_SHA'],pkz_sha256=qa['pkz_sha256'],pkz_bytes=qa['pkz_bytes']))
    print('V047_RELEASE',rel['id'],rel['html_url'],flush=True)
    print('V047_DOWNLOAD',next(a['browser_download_url'] for a in api('/releases/'+str(rel['id']))['assets'] if a['name']=='OrlandoMX_2026_v047.pkz'),flush=True)
def diagnostics():
    rid=os.environ.get('V047_RELEASE_ID')
    if not rid:return
    p=R/'BUILD'/('v047_diagnostics-'+os.environ['GITHUB_RUN_ID']+'.zip')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in list((R/'DOCUMENTATION').glob('*v047*'))+list(O.glob('*.json')):
            if f.is_file():z.write(f,f.relative_to(R).as_posix())
    upload(api('/releases/'+rid),p)
if __name__=='__main__':{'restore':restore,'checkpoint':checkpoint,'deliver':deliver,'diagnostics':diagnostics}[sys.argv[1]]()
