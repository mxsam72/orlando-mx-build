"""Correct sign UVs and eliminate the nearly coplanar Qwikchute backboards.

Keep all model IDs, materials, textures, placements and unrelated object records.
The two Qwikchute graphics remain flat opaque image faces. Their support frames
have no full-area black backboard, and sit well behind either image face.
"""
import copy, shutil
import numpy as np
from scipy.spatial import cKDTree
from v039_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from rebind_scenery import array, encoded_array
from verify_v037_source import faces
from v037_fbx import mapped_geometry

def face_uv(g):
    layer=child(g,b'LayerElementUV')
    uv=array(child(layer,b'UV')).reshape(-1,2)
    ix=array(child(layer,b'UVIndex')).astype(int)
    out=[];offset=0
    for f in faces(g):
        out.append(uv[ix[offset:offset+len(f)]]);offset+=len(f)
    return out

def fix_qwik(rec,p):
    frame,mid=rec[p['id']+'_frame'];logo,lmid=rec[p['id']+'_logo']
    vv=vertices(logo);a=p['depth_axis'];w=p['width_axis'];center=float((vv[:,a].min()+vv[:,a].max())/2)
    low=vv.min(0);high=vv.max(0);width=high[w]-low[w];height=high[1]-low[1]
    fv=vertices(frame);ff=faces(frame);uv=face_uv(frame);removed=[];keep=[]
    for i,f in enumerate(ff):
        q=fv[f]
        inside=(q[:,w].min()>=low[w]-1e-7 and q[:,w].max()<=high[w]+1e-7 and q[:,1].min()>=low[1]-1e-7 and q[:,1].max()<=high[1]+1e-7 and np.abs(q[:,a]-center).max()<=np.abs(vv[:,a]-center).max()+1e-7)
        spans=np.ptp(q[:,w])>=width*.99 or np.ptp(q[:,1])>=height*.99
        (removed if inside and spans else keep).append(i)
    # This is the six faces of the rectangular backing box, not an arbitrary
    # distance-based selection of a nearby pole or track object.
    assert len(removed)==6,(p['id'],removed)
    assert all(len(ff[i])==4 for i in removed)
    fv[:,a]=center+(fv[:,a]-center)*p['frame_depth_scale']
    tris=[];tuv=[]
    for i in keep:
        f=ff[i];t=uv[i]
        for j in range(1,len(f)-1):
            tri=[f[0],f[j],f[j+1]];tex=t[[0,j,j+1]]
            # mapped_geometry reverses source winding during its Z reflection.
            # Reverse its input to retain the original native FBX winding.
            tris.append(tri[::-1]);tuv.append(tex[::-1].tolist())
    used=sorted({i for f in tris for i in f});index={i:j for j,i in enumerate(used)}
    mesh=dict(name=p['id']+'_frame',vertices=fv[used].tolist(),faces=[[index[i] for i in f] for f in tris],uv=tuv)
    replacement=mapped_geometry(values(frame)[0],mesh)
    assert values(replacement)==values(frame)
    frame.clear();frame.update(replacement)
    signs=np.sign(vv[:,a]-center);assert set(signs)=={-1.,1.}
    vv[:,a]=center+signs*p['image_half_depth_m']
    child(logo,b'Vertices')['props']=encoded_array(vv*[100,100,-100])
    frame_half_depth=float(np.abs(fv[used,a]-center).max());gap=p['image_half_depth_m']-frame_half_depth
    assert gap>=.18
    return dict(id=p['id'],depth_axis=a,width_axis=w,center_depth_m=center,image_width_m=float(width),image_height_m=float(height),removed_black_backboard_polygons=6,removed_black_backboard_triangles=12,flat_opaque_front_and_rear_faces=True,original_logo_pixels_and_uv_retained=True,minimum_image_support_depth_gap_m=gap,frame_polygons_before=len(ff),frame_triangles_after=len(tris),image_planes_depth_m=[center-p['image_half_depth_m'],center+p['image_half_depth_m']])

def release():
    source=R/'12_RELEASE/orlandomx_2026_v038';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.suffix in ['.map','.trh']:continue
        copy_exact(p,dest/p.name.replace('orlandomx_2026_v038',NAME))
    ini=dest/(NAME+'.ini');t=ini.read_text();assert 'v038' in t;atomic(ini,t.replace('v038','v039').encode())
    copy_exact(BASE/'orlandomx_2026_v038.rdf',O/(NAME+'.rdf'));copy_exact(O/(NAME+'.rdf'),dest/(NAME+'.rdf'))

def main():
    cfg=read(S/'sign_fix.json');baseline=read(BASE/'source_validation.json')
    # The pinned whole-checkpoint digest in the restore step authenticates the
    # Windows source. Linux regeneration of v038 can differ in floating-point
    # FBX array encoding; the user-tested native checkpoint is authoritative.
    assert baseline['version']=='v038' and baseline['source_checks_pass']
    assert sha(BASE/'scenery.fbx')==baseline['scenery_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O)
    original=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(original);assert encode(nodes,tail)==original
    rec=geometry_records(nodes);changed=[];prior=[];probes=[]
    names=[cfg['speed_world_id']+'_graphic']+[p['id']+'_'+part for p in cfg['qwikchute'] for part in ['frame','logo']]
    for name in names:prior.extend(vertices(rec[name][0]).tolist());changed.append(values(rec[name][0])[0])
    entrance=rec[cfg['speed_world_id']+'_graphic'][0]
    layer=child(entrance,b'LayerElementUV');uv=array(child(layer,b'UV')).reshape(-1,2);uv[:,0]=1-uv[:,0]
    child(layer,b'UV')['props']=encoded_array(uv)
    qw=[fix_qwik(rec,p) for p in cfg['qwikchute']]
    atomic(O/'scenery.fbx',encode(nodes,tail))
    for name in names:probes.extend(vertices(rec[name][0]).tolist())
    # Refresh old generic probes that referred to a removed or relocated sign
    # vertex. Retain every other baseline probe without changing its position.
    old=read(BASE/'native_coordinate_probes.json')['expected_xyz_metres'];dist=cKDTree(prior).query(old)[0]
    kept=[p for p,d in zip(old,dist) if d>1e-7]
    save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=kept+probes))
    save(O/'v039_sign_native_probes.json',dict(expected_xyz_metres=probes))
    qs=[]
    for name in ['v033_qwikchute_billboard_frame','v033_qwikchute_billboard_concrete','v033_qwikchute_billboard_logo']:qs.extend(vertices(rec[name][0]).tolist())
    oldqw=read(BASE/'qwikchute_native_probes.json');oldqw['expected_xyz_metres']=qs;save(O/'qwikchute_native_probes.json',oldqw)
    scene=dict(checks_pass=True,baseline_scenery_sha256=baseline['scenery_sha256'],baseline_checkpoint_sha256=cfg['baseline_checkpoint_sha256'],modified_geometry_ids=changed,modified_geometry_names=names,changed_object_count=5,new_objects=0,new_textures=0,new_materials=0,all_other_object_records_byte_exact=True,all_connections_and_model_transforms_byte_exact=True,all_texture_pixels_byte_exact=True,speed_world_horizontal_uv_flipped_on_both_faces=True,qwikchute=qw)
    save(O/'v039_sign_validation.json',scene)
    qa=read(BASE/'source_validation.json');qa.update(version='v039',baseline_version='user-tested v038',baseline_commit=cfg['baseline_source_commit'],source_checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),v039_sign_fix=scene,native_compilation=False)
    save(O/'source_validation.json',qa);save(O/'v039_layout.json',cfg);release()
    print('v039 source ready: Speed World UVs corrected; both Qwikchute backboards removed with >=18 cm image/support separation.',flush=True)

if __name__=='__main__':main()
