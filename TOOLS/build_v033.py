"""Preserve v032; recess three memorial supports and append the supplied logo."""
import argparse, copy, math, os, subprocess, sys
from scipy.spatial import cKDTree
from v033_common import *
from v027_scenery import parse, encode, values, child, fingerprint, geometry_records, vertices
from rebind_scenery import array, encoded_array
import v033_billboard as billboard

MEMORIAL_FRAME='v032_pup_whatley_memorial_frame'
PARENT_COMMIT='1f99f9bf6e766d10c58cd1760341d26c11afdb8c'

def fix_memorial():
    original=(O/'scenery.fbx').read_bytes();nodes,tail=parse(original)
    assert encode(nodes,tail)==original
    geom=geometry_records(nodes)[MEMORIAL_FRAME][0]
    vn=child(geom,b'Vertices');native=array(vn).reshape(-1,3).copy()
    before=vertices(geom);assert before.shape==(64,3)
    selected=[];columns=[]
    for k,x in enumerate([318.7,322.,325.3]):
        ids=np.arange(40+8*k,48+8*k);points=before[ids]
        assert np.allclose([points[:,0].mean(),points[:,2].mean()],[x,144.],atol=1e-10)
        assert np.allclose(np.ptp(points,axis=0)[[0,2]],[.24,.24],atol=1e-10)
        assert np.ptp(points[:,1])>7.7
        native[ids,2]=-14400.+(native[ids,2]+14400.)*.5
        selected.extend(ids.tolist())
        columns.append(dict(x_m=x,original_depth_m=.24,revised_depth_m=.12,art_plane_local_z_m=[-.104,.104],revised_post_local_z_m=[-.06,.06],clearance_each_face_m=.044))
    vn['props']=encoded_array(native)
    after=vertices(geom);assert np.array_equal(before[:,[0,1]],after[:,[0,1]])
    assert np.array_equal(before[:40],after[:40])
    assert np.allclose(abs(after[selected,2]-144.),.06,atol=1e-10)
    output=encode(nodes,tail);atomic(O/'scenery.fbx',output)
    parsed,_=parse(output);assert np.array_equal(vertices(geometry_records(parsed)[MEMORIAL_FRAME][0]),after)
    meshes=read(O/'memorial_meshes.json');frame=next(m for m in meshes if m['name']==MEMORIAL_FRAME)
    assert np.allclose(frame['vertices'],before,atol=1e-10);frame['vertices']=after.tolist();save(O/'memorial_meshes.json',meshes)
    # Retained compiled probes referencing a moved post must follow that post.
    for name in ['native_coordinate_probes.json','memorial_native_probes.json']:
        data=read(O/name)
        for point in data['expected_xyz_metres']:
            for i in selected:
                if np.allclose(point,before[i],rtol=0,atol=1e-9):point[:]=after[i].tolist();break
        save(O/name,data)
    probeids=[40,44,42,46,48,52,50,54,56,60,58,62]
    moved=after[probeids].tolist();old=before[probeids].tolist()
    globalprobes=read(O/'native_coordinate_probes.json');globalprobes['expected_xyz_metres']+=moved;save(O/'native_coordinate_probes.json',globalprobes)
    save(O/'memorial_support_native_probes.json',dict(expected_xyz_metres=moved,prior_xyz_metres=old))
    qa=dict(checks_pass=True,frame_mesh=MEMORIAL_FRAME,changed_vertices=24,columns=columns,front_and_back_art_clear_of_supports=True,only_support_depth_changed=True,existing_frame_footings_positions_and_artwork_unchanged=True,source_fbx_before_sha256=sha(BASE/'scenery.fbx'),source_fbx_after_support_fix_sha256=sha(O/'scenery.fbx'),native_probe_count=len(moved),in_game_visual_check=False)
    save(O/'memorial_support_validation.json',qa)
    return qa

def placement_checks(meshes):
    v=np.concatenate([np.asarray(m['vertices']) for m in meshes]);xz=v[:,[0,2]]
    grid=np.array([[x,z] for x in np.linspace(xz[:,0].min(),xz[:,0].max(),80) for z in np.linspace(xz[:,1].min(),xz[:,1].max(),8)])
    route=dict(np.load(O/'route.npz'));results={}
    for name,q,width in [('main',route['q'],route['width']),('start',route['start'],np.full(len(route['start']),8.))]:
        d,i=cKDTree(q[:,:2]).query(grid);results[name+'_edge_clearance_m']=float((d-width[i]/2).min());assert results[name+'_edge_clearance_m']>3
    # Footprint must not touch any existing scenery, especially spectator fence.
    nodes,_=parse((O/'scenery.fbx').read_bytes());near=[]
    for name,(g,_) in geometry_records(nodes).items():
        old=vertices(g);gap=float(np.linalg.norm(np.maximum(np.maximum(old.min(0)-v.max(0),v.min(0)-old.max(0)),0)))
        assert gap>.25,(name,'billboard intersects existing scenery bounds',gap)
        if gap<12:near.append(dict(mesh=name,bounds_gap_m=gap))
    results['nearby_objects']=sorted(near,key=lambda q:q['bounds_gap_m']);results['checks_pass']=True
    return results

def add_qwikchute():
    cfg=read(S/'qwikchute_spec.json');src=S/'qwikchute_logo.png';assert sha(src)==cfg['supplied_image_sha256']
    im=Image.open(src);im.load();assert list(im.size)==cfg['supplied_image_size_px'];im=im.convert('RGB')
    assert abs(cfg['image_width_m']/cfg['image_height_m']-im.width/im.height)<1e-10
    folder=O/'facility_textures';path=folder/'v033_qwikchute_logo.tga'
    image_file(im.resize(cfg['texture_size_px'],Image.Resampling.LANCZOS),path)
    textures={'logo':(path,(255,255,255))}
    for material,rgb in [('frame',(43,45,47)),('concrete',(145,143,137))]:
        p=folder/('v033_qwikchute_'+material+'.tga');image_file(Image.new('RGB',(32,32),rgb),p);textures[material]=(p,rgb)
    height=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    meshes,origin=billboard.make_meshes(height,cfg);clear=placement_checks(meshes)
    save(O/'qwikchute_meshes.json',meshes)
    qa=billboard.append(meshes,textures);qa.update(checks_pass=True,supplied_image_sha256=sha(src),original_logo_unchanged_and_uncropped=True,authored_size_m=[cfg['image_width_m'],cfg['image_height_m']],ground_anchor_xyz_m=origin.tolist(),native_texture_size_px=cfg['texture_size_px'],original_image_size_px=list(im.size),resampling_does_not_add_source_detail=True,placement='Grass strip on pit side of spectator fence before tabletop, matching user mark',clearances=clear,in_game_visual_check=False)
    save(O/'qwikchute_validation.json',qa);return qa

def finalize(supports,qwik):
    qa=copy.deepcopy(read(BASE/'source_validation.json'));qa.update(version='v033',source_commit=os.environ.get('GITHUB_SHA','local'),parent_source_commit=PARENT_COMMIT,source_checks_pass=True,scenery_sha256=sha(O/'scenery.fbx'),memorial_support_fix=supports,qwikchute=qwik)
    protected={}
    for p in BASE.rglob('*'):
        if p.is_file() and (p.parent.name in ['materials','masks','facility_textures'] or p.name in ['terrain.raw','main.tcl','start.tcl','route.npz','geometry_spec.json','jump_profiles.json','turns.json','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','v024_pit_gravel.tga']):
            dst=O/p.relative_to(BASE);assert sha(p)==sha(dst),'Changed protected v032 input: '+str(p);protected[str(p.relative_to(BASE))]=sha(dst)
    before,_=parse((BASE/'scenery.fbx').read_bytes());after,_=parse((O/'scenery.fbx').read_bytes())
    old=next(n for n in before if n['name']==b'Objects')['children'];new={values(n)[0]:n for n in next(n for n in after if n['name']==b'Objects')['children']}
    frameid=values(geometry_records(before)[MEMORIAL_FRAME][0])[0];changed=[]
    for n in old:
        if fingerprint(n)!=fingerprint(new[values(n)[0]]):changed.append(values(n)[0])
    assert changed==[frameid],changed
    oldgeom=geometry_records(before)[MEMORIAL_FRAME][0];newgeom=geometry_records(after)[MEMORIAL_FRAME][0]
    child(newgeom,b'Vertices')['props']=child(oldgeom,b'Vertices')['props'];assert fingerprint(oldgeom)==fingerprint(newgeom)
    oldlinks=next(n for n in before if n['name']==b'Connections')['children'];newlinks=next(n for n in after if n['name']==b'Connections')['children']
    assert [fingerprint(n) for n in oldlinks]==[fingerprint(n) for n in newlinks[:len(oldlinks)]]
    qa.update(protected_v032_files_sha256=protected,retained_v032_records_byte_exact_except_memorial_post_vertices=True,unchanged_memorial_art_texture_sha256=sha(O/'facility_textures/v032_pup_whatley_memorial.tga'),unchanged_tested_v030_riding_geometry=True)
    # Existing memorial's face/UV validation remains valid; append support check.
    qa['memorial']['support_fix']=supports
    save(O/'source_validation.json',qa)
    dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in (R/'12_RELEASE/orlandomx_2026_v032').iterdir():
        if not p.is_file() or p.suffix in ['.map','.trh']:continue
        data=p.read_bytes()
        if p.suffix in ['.ini','.amb','.tsc','.cfg','.txt','.rdf']:data=data.replace(b'v032',b'v033').replace(b'V032',b'V033')
        atomic(dest/p.name.replace('v032','v033'),data)
    save(O/'native_unchanged_file_checks.json',dict(expected_trh_sha256='d08962d7469edc5eb967a83d83eadb2fb50bfb6a949c084d0932f080280e4269',expected_files={p.name.replace('v032','v033'):sha(p) for p in (R/'12_RELEASE/orlandomx_2026_v032').iterdir() if p.suffix in ['.tga','.tl'] or p.name=='marshals.cfg'}))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');args=ap.parse_args()
    baseqa=read(BASE/'source_validation.json');assert baseqa['version']=='v032' and baseqa['source_checks_pass']
    assert sha(BASE/'scenery.fbx')==baseqa['scenery_sha256'] and sha(BASE/'terrain.raw')==baseqa['terrain_sha256']
    if O.exists():shutil.rmtree(O)
    for p in BASE.rglob('*'):
        if p.is_file():copy_exact(p,O/p.relative_to(BASE))
    supports=fix_memorial();qwik=add_qwikchute();finalize(supports,qwik)
    print('v033 source verified: 24 support vertices recessed; Qwikchute placed; all unrelated v032 records/assets preserved.',flush=True)
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v033.py')],cwd=R,check=True)

if __name__=='__main__':main()
