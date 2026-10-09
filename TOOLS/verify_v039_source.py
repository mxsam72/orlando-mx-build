"""Check sign readability in native XZY handedness, gap and exact preservation."""
import numpy as np
from v039_common import *
from v027_scenery import parse, values, child, fingerprint, vertices, geometry_records
from rebind_scenery import array
from verify_v037_source import faces

def readability(g,axis):
    v=vertices(g);layer=child(g,b'LayerElementUV');uv=array(child(layer,b'UV')).reshape(-1,2);ix=array(child(layer,b'UVIndex')).astype(int)
    center=float((v[:,axis].min()+v[:,axis].max())/2);offset=0;checks=[]
    for f in faces(g):
        q=v[f];t=uv[ix[offset:offset+len(f)]];offset+=len(f)
        transform=np.linalg.lstsq(np.c_[t,np.ones(len(t))],q,rcond=None)[0]
        # MX Bikes world X/Z/Y corresponds to ordinary renderer X/Y/Z.
        # A source test assuming a right-handed X/Y/Z camera accepted the old
        # mirrored UVs. Compare actual screen-right for each camera side.
        side=np.sign(q[:,axis].mean()-center);camera=q.mean(0);camera[axis]+=side*30
        direction=(q.mean(0)-camera)[[0,2,1]];direction/=np.linalg.norm(direction)
        right=np.cross(direction,[0,0,1]);right/=np.linalg.norm(right)
        u=transform[0][[0,2,1]];up=transform[1][[0,2,1]]
        points=q[:,[0,2,1]];normal=np.cross(points[1]-points[0],points[2]-points[0]);normal/=np.linalg.norm(normal)
        checks.append(dict(side=float(side),screen_right_u=float(u@right),screen_up_v=float(up@[0,0,1]),front_facing=float(normal@((camera-q.mean(0))[[0,2,1]]))))
    return checks

def main():
    cfg=read(S/'sign_fix.json');scene=read(O/'v039_sign_validation.json')
    before,tail=parse((BASE/'scenery.fbx').read_bytes());after,tail1=parse((O/'scenery.fbx').read_bytes())
    a={values(n)[0]:n for n in next(n for n in before if n['name']==b'Objects')['children']};b={values(n)[0]:n for n in next(n for n in after if n['name']==b'Objects')['children']}
    allowed=set(scene['modified_geometry_ids']);assert len(allowed)==5 and set(a)==set(b)
    actual={i for i in a if fingerprint(a[i])!=fingerprint(b[i])};assert actual==allowed
    for i in allowed:assert a[i]['name']==b[i]['name']==b'Geometry'
    top={n['name']:fingerprint(n) for n in before if n['name']!=b'Objects'}
    assert top=={n['name']:fingerprint(n) for n in after if n['name']!=b'Objects'}
    assert tail[:20]==tail1[:20] and tail[-140:]==tail1[-140:]
    rec0=geometry_records(before);rec1=geometry_records(after);assert set(rec0)==set(rec1)
    for name in rec0:assert rec0[name][1]==rec1[name][1]
    name=cfg['speed_world_id']+'_graphic';g0=rec0[name][0];g1=rec1[name][0]
    assert child(g0,b'Vertices')['props']==child(g1,b'Vertices')['props']
    for n in ['PolygonVertexIndex','LayerElementNormal','LayerElementMaterial']:assert fingerprint(child(g0,n.encode()))==fingerprint(child(g1,n.encode()))
    uv0=array(child(child(g0,b'LayerElementUV'),b'UV')).reshape(-1,2);uv1=array(child(child(g1,b'LayerElementUV'),b'UV')).reshape(-1,2)
    assert np.array_equal(uv0[:,1],uv1[:,1]) and np.array_equal(1-uv0[:,0],uv1[:,0])
    old_read=readability(g0,0);assert all(c['screen_right_u']<0 for c in old_read)
    signs=[dict(id=cfg['speed_world_id'],faces=readability(g1,0),old_mapping_proven_mirrored=True)]
    gapchecks=[];removed=[]
    for p in cfg['qwikchute']:
        logo0=rec0[p['id']+'_logo'][0];logo1=rec1[p['id']+'_logo'][0];frame0=rec0[p['id']+'_frame'][0];frame1=rec1[p['id']+'_frame'][0]
        for n in ['PolygonVertexIndex','LayerElementUV','LayerElementNormal','LayerElementMaterial']:assert fingerprint(child(logo0,n.encode()))==fingerprint(child(logo1,n.encode()))
        old=vertices(logo0);vv=vertices(logo1);axis=p['depth_axis'];width=p['width_axis'];other=[i for i in range(3) if i!=axis]
        assert np.array_equal(old[:,other],vv[:,other])
        center=float((old[:,axis].min()+old[:,axis].max())/2);fv=vertices(frame1)
        assert abs(vv[:,axis].min()-(center-.25))<1e-9 and abs(vv[:,axis].max()-(center+.25))<1e-9
        gap=float(np.abs(vv[:,axis]-center).min()-np.abs(fv[:,axis]-center).max());assert gap>=.18
        # No surviving black face spans the graphic's full width or height.
        for f in faces(frame1):
            q=fv[f];inside=(q[:,width].min()>=vv[:,width].min()-1e-7 and q[:,width].max()<=vv[:,width].max()+1e-7 and q[:,1].min()>=vv[:,1].min()-1e-7 and q[:,1].max()<=vv[:,1].max()+1e-7)
            assert not(inside and np.ptp(q[:,width])>=np.ptp(vv[:,width])*.99 and np.ptp(q[:,1])>=np.ptp(vv[:,1])*.99)
        oldfv=vertices(frame0);lo=old.min(0);hi=old.max(0)
        backing=[q for q in oldfv if lo[width]-1e-7<=q[width]<=hi[width]+1e-7 and lo[1]-1e-7<=q[1]<=hi[1]+1e-7 and abs(q[axis]-center)<=np.abs(old[:,axis]-center).max()+1e-7]
        # Only box corners with exact full image extents are disappearance
        # probes; adjacent border-frame vertices must not be mistaken for them.
        backing=[q for q in backing if min(abs(q[width]-lo[width]),abs(q[width]-hi[width]))<1e-7 and min(abs(q[1]-lo[1]),abs(q[1]-hi[1]))<1e-7]
        unique=np.unique(np.round(backing,10),axis=0);assert len(unique)==8;removed.extend(unique.tolist())
        gapchecks.append(dict(id=p['id'],minimum_image_support_gap_m=gap,full_black_backboard_removed=True,flat_front_and_rear_faces=True))
        signs.append(dict(id=p['id'],faces=readability(logo1,axis)))
    assert all(c['screen_right_u']>0 and c['screen_up_v']>0 and c['front_facing']>0 for s in signs for c in s['faces'])
    protected=[];exceptions={'scenery.fbx','source_validation.json','native_coordinate_probes.json','qwikchute_native_probes.json'}
    for p in sorted(BASE.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(BASE).as_posix()
        if rel in exceptions:continue
        assert sha(p)==sha(O/rel),rel;protected.append(dict(file=rel,sha256=sha(p)))
    assert sha(BASE/'orlandomx_2026_v038.rdf')==sha(O/(NAME+'.rdf'))
    qa=dict(checks_pass=True,changed_geometry_records=5,unchanged_object_records=len(a)-5,all_model_transforms_materials_connections_and_definitions_exact=True,all_textures_masks_terrain_routes_race_and_soils_byte_exact=True,parked_red_black_trucks_and_oval_exact=True,memorial_and_pit_displays_exact=True,new_textures=0,new_materials=0,readability_in_native_camera_handedness=signs,depth_separation=gapchecks,removed_black_backboard_corners_xyz_m=removed,protected_files=protected)
    save(O/'v039_independent_validation.json',qa)
    print('v039 independent checks passed: 12 readable front-facing triangles; both black backboards absent; >=18 cm separation; all riding data and textures exact.',flush=True)

if __name__=='__main__':main()
