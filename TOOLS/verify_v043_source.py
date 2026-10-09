"""Independent hoist alignment, Ford parking, and complete preservation audit."""
import copy
from collections import Counter
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import MultiPoint, Polygon, LineString, box
from v043_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from verify_v037_source import faces
from verify_v042_source import camera_checks, grid, alpha_at
from build_v040 import face_uv
from v037_common import ground
from rebind_scenery import array


def main():
    cfg = read(S/'update.json')
    qa = read(O/'source_validation.json')
    oldraw = (BASE/'scenery.fbx').read_bytes()
    newraw = (O/'scenery.fbx').read_bytes()
    bn, bt = parse(oldraw)
    nn, nt = parse(newraw)
    assert encode(nn, nt) == newraw
    rb, rn = geometry_records(bn), geometry_records(nn)
    assert set(rb).issubset(rn) and len(rn)-len(rb) == cfg['ford']['expected_parts']
    bo = {values(n)[0]: n for n in next(n for n in bn if n['name'] == b'Objects')['children']}
    no = {values(n)[0]: n for n in next(n for n in nn if n['name'] == b'Objects')['children']}
    assert set(bo).issubset(no)
    original = rb[cfg['flag_geometry']][0]
    current = rn[cfg['flag_geometry']][0]
    flagid = values(original)[0]
    assert {i for i in bo if fingerprint(bo[i]) != fingerprint(no[i])} == {flagid}
    for c in original['children']:
        if c['name'] != b'LayerElementUV':
            assert fingerprint(c) == fingerprint(child(current, c['name']))
    l0, l1 = child(original, b'LayerElementUV'), child(current, b'LayerElementUV')
    for c in l0['children']:
        if c['name'] != b'UV':
            assert fingerprint(c) == fingerprint(child(l1, c['name']))
    uv0, uv1 = array(child(l0, b'UV')).reshape(-1, 2), array(child(l1, b'UV')).reshape(-1, 2)
    assert np.array_equal(uv0[:6], uv1[:6])
    assert np.array_equal(uv0[:, 1], uv1[:, 1])
    assert np.array_equal(1-uv0[6:, 0], uv1[6:, 0])
    # Check the physical hoist, independent of a preferred screen-left image.
    # On a real reverse flag the canton is screen-right when its pole is right.
    fv = vertices(current)
    polev = vertices(rn[cfg['flag_pole_geometry']][0])
    pole = (polev[:, [0, 2]].min(0) + polev[:, [0, 2]].max(0))/2
    flagchecks = []
    for i, (face, uv) in enumerate(zip(faces(current), face_uv(current))):
        points = fv[face]
        hoist = points[np.isclose(uv[:, 0], 0)]
        fly = points[np.isclose(uv[:, 0], 1)]
        assert len(hoist) and len(fly)
        near = np.linalg.norm(hoist[:, [0, 2]]-pole, axis=1)
        far = np.linalg.norm(fly[:, [0, 2]]-pole, axis=1)
        assert near.max() < .2 and far.min() > 2.
        top = points[np.isclose(uv[:, 1], 1)]
        bottom = points[np.isclose(uv[:, 1], 0)]
        assert np.isclose(top[:, 1].min()-bottom[:, 1].max(), 1.196)
        flagchecks.append(dict(face=i, canton_hoist_distance_max_m=float(near.max()),
                               fly_distance_min_m=float(far.min()), stars_beside_pole=True))
    cams = camera_checks(current)
    assert all(c['screen_right_u'] > 0 for c in cams[:2])
    assert all(c['screen_right_u'] < 0 for c in cams[2:])
    assert all(c['screen_up_v'] > 0 and c['front_facing'] > 0 for c in cams)
    center = (fv.min(0)+fv.max(0))/2
    normals = []
    for f in faces(current):
        p = fv[f]
        cross = np.cross(p[1]-p[0], p[2]-p[0])
        assert cross @ (p.mean(0)-center) < 0
        normals.append(-cross/np.linalg.norm(cross))
    assert np.isclose(np.ptp(fv@normals[0]), .30)
    with Image.open(O/'facility_textures/v040_american_flag.tga') as im:
        assert im.mode == 'RGB' and im.size == (2048, 1024)
        pixels = np.asarray(im).astype(int)
        blue = (pixels[:, :, 2] > pixels[:, :, 0]+15) & (pixels[:, :, 2] > pixels[:, :, 1]+5)
        yy, xx = np.where(blue)
        assert len(xx)>100000 and xx.max()<im.width*.45 and yy.max()<im.height*.6
    bl = next(n for n in bn if n['name'] == b'Connections')['children']
    nl = next(n for n in nn if n['name'] == b'Connections')['children']
    assert [fingerprint(n) for n in nl[:len(bl)]] == [fingerprint(n) for n in bl]
    for n in bn:
        if n['name'] not in [b'Objects', b'Connections', b'Definitions']:
            assert fingerprint(n) == fingerprint(next(a for a in nn if a['name'] == n['name']))
    counts = Counter(n['name'] for n in no.values())
    defs = next(n for n in nn if n['name'] == b'Definitions')
    total = 0
    for d in defs['children']:
        if d['name'] == b'ObjectType':
            typ = values(d)[0]
            ct = values(child(d, b'Count'))[0]
            total += ct
            if typ != b'GlobalSettings':
                assert counts[typ] == ct
    assert values(child(defs, b'Count'))[0] == total
    exact = ['terrain.raw', 'height_metres.npy', 'terrain_16bit.png', 'main.tcl', 'start.tcl', 'route.npz',
             'jump_profiles.json', 'compiled_track.hmf', 'minrace.tl', 'maxrace.tl', 'checkleft.tl',
             'checkright.tl', 'v024_pit_gravel.tga', 'practice_access.npz']
    for name in exact:
        assert sha(BASE/name) == sha(O/name), name
    texturecount = 0
    for folder in ['masks', 'materials', 'facility_textures']:
        assert {p.name for p in (BASE/folder).iterdir()} == {p.name for p in (O/folder).iterdir()}
        for p in (BASE/folder).iterdir():
            if p.is_file():
                assert sha(p) == sha(O/folder/p.name), (folder, p.name)
                texturecount += p.suffix == '.tga'
    for name in rb:
        if name != cfg['flag_geometry']:
            assert fingerprint(rb[name][0]) == fingerprint(rn[name][0]), name
    ford = read(O/'v043_vehicle_validation.json')
    group = cfg['ford']['group']
    parts = {n:(g,m) for n,(g,m) in rn.items() if n.startswith(group+'_')}
    source = {n:(g,m) for n,(g,m) in rb.items() if n.startswith(cfg['ford']['source_prefix'])}
    assert len(parts) == len(source) == 14 and ford['count'] == 1
    rot = np.asarray(ford['rotation'])
    assert np.allclose(rot@rot.T, np.eye(3), atol=1e-10) and np.isclose(np.linalg.det(rot), 1)
    links = [values(n) for n in nl]
    for name,(g,mid) in parts.items():
        srcname = 'truck_sam_'+name.removeprefix(group+'_')
        g0,mid0 = source[srcname]
        for layer in [b'PolygonVertexIndex', b'LayerElementUV', b'LayerElementMaterial']:
            assert fingerprint(child(g0,layer)) == fingerprint(child(g,layer)), (name,layer)
        expected = (vertices(g0)-[ford['source_center_xz_m'][0],ford['source_bottom_m'],ford['source_center_xz_m'][1]])@rot.T + ford['origin_xyz_m']
        assert np.allclose(vertices(g), expected, atol=1e-9)
        for layer in g0['children']:
            if layer['name'] == b'LayerElementNormal':
                before = array(child(layer,b'Normals')).reshape(-1,3)*[1,1,-1]
                after = array(child(child(g,b'LayerElementNormal'),b'Normals')).reshape(-1,3)*[1,1,-1]
                assert np.allclose(after,before@rot.T,atol=1e-10)
        assert values(child(no[mid],b'Culling')) == [b'CullingOnCCW']
        clone = copy.deepcopy(no[mid])
        clone['props'] = bo[mid0]['props']
        assert fingerprint(clone) == fingerprint(bo[mid0])
        mat0 = [v[1] for v in links if v[2] == mid0 and no.get(v[1],{}).get('name') == b'Material']
        mat1 = [v[1] for v in links if v[2] == mid and no.get(v[1],{}).get('name') == b'Material']
        assert mat0 == mat1 and len(mat1) == 1
    height = np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    allv = np.concatenate([vertices(g) for g,m in parts.values()])
    srcv = np.concatenate([vertices(source['truck_sam_'+n.removeprefix(group+'_')][0]) for n in parts])
    low = srcv[:,1]-ford['source_bottom_m'] < .065
    gap = allv[low,1]-ground(height,allv[low][:,[0,2]])
    assert gap.min()>-1e-8 and gap.max()<cfg['maximum_wheel_ground_gap_m']
    footprint = MultiPoint(allv[:,[0,2]]).convex_hull
    samples = grid(footprint.buffer(.30))
    # alpha_at reads the same authenticated v042 masks; exact copies above
    # prove those values also apply to the v043 output.
    grassmin = int(alpha_at('grass.tga',samples).min())
    gravelmax = int(alpha_at('v024_pit_roads.tga',samples).max())
    assert grassmin >= cfg['minimum_grass_mask_alpha'] and gravelmax < 32
    roadpolys=[]
    obstacles=[]
    for name,(g,mid) in rb.items():
        v=vertices(g)
        if name.startswith('TRKASPH'):
            for f in faces(g):
                p=Polygon(v[f][:,[0,2]])
                if p.area>1e-8:roadpolys.append(p)
        if name.startswith(('TRK','drainage_water','v037_oval_mark')):
            continue
        lowv=v[v[:,1]-ground(height,v[:,[0,2]])<3.2]
        if len(lowv):obstacles.append((name,box(*lowv[:,[0,2]].min(0),*lowv[:,[0,2]].max(0))))
    roaddist=float(footprint.distance(shapely.union_all(roadpolys)))
    nearest,obstacledist=min(((n,float(footprint.distance(p))) for n,p in obstacles),key=lambda v:v[1])
    assert roaddist>cfg['minimum_route_clearance_m'] and obstacledist>cfg['minimum_obstacle_clearance_m']
    route=dict(np.load(O/'route.npz'));access=dict(np.load(O/'practice_access.npz'))
    corridors=[('MX',LineString(route['q'][:,:2]).buffer(float(route['width'].max()/2)+1.5)),
               ('start',LineString(route['start'][:,:2]).buffer(13)),
               ('practice',LineString(access['lane'][:,:2]).buffer(5.5)),
               ('connector',LineString(access['connector'][:,:2]).buffer(5.0))]
    routedists={n:float(footprint.distance(p)) for n,p in corridors}
    assert min(routedists.values())>cfg['minimum_route_clearance_m']
    board=np.concatenate([vertices(g) for n,(g,m) in rb.items() if n.startswith(cfg['ford']['billboard_prefix'])])
    boardcenter=(board[:,[0,2]].min(0)+board[:,[0,2]].max(0))/2
    boarddistance=float(footprint.distance(MultiPoint(board[:,[0,2]]).convex_hull))
    assert np.linalg.norm(boardcenter-np.asarray(ford['center_xz_m'])) < 10 and 1.5<boarddistance<5
    head=vertices(parts[group+'_ford_badge'][0])[:,[0,2]].mean(0)
    tail=vertices(parts[group+'_red_light'][0])[:,[0,2]].mean(0)
    heading=float(np.degrees(np.arctan2(*(head-tail)[::-1])))
    headingerror=abs((heading-cfg['ford']['heading_degrees']+180)%360-180)
    assert headingerror<1.5
    tree=cKDTree(np.concatenate([vertices(g) for g,m in rn.values()]))
    for filename in ['native_coordinate_probes.json','v041_native_probes.json','v042_native_probes.json',
                     'v043_native_probes.json','memorial_support_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json']:
        assert tree.query(read(O/filename)['expected_xyz_metres'])[0].max()<1e-7,filename
    report=dict(checks_pass=True, preserved_original_geometry_records=len(rb)-1,
                retained_original_object_records_exact=len(bo)-1,
                existing_flag_pit_face_uvs_exact=True, track_face_horizontal_uv_only_changed=True,
                flag_stars_at_physical_hoist_both_faces=True, flag_hoist_checks=flagchecks,
                native_camera_checks=cams, real_reverse_face_screen_right_canton=True,
                flag_original_opaque_artwork_and_30cm_face_separation_exact=True,
                all_original_texture_files_exact=texturecount, added_texture_count=0,
                added_vehicle_count=1, added_vehicle='Sam Ford F-150 King Ranch',ford_parts=14,
                original_pit_ford_unchanged=True, cloned_topology_uvs_normals_culling_materials_verified=True,
                ford_center_xz_m=ford['center_xz_m'], nearest_existing_obstacle=nearest,
                obstacle_clearance_m=obstacledist, figure_eight_pavement_clearance_m=roaddist,
                billboard_clearance_m=boarddistance, protected_route_clearances_m=routedists,
                grass_alpha_min=grassmin, gravel_road_alpha_max=gravelmax,
                wheel_ground_gap_min_m=float(gap.min()),wheel_ground_gap_max_m=float(gap.max()),
                ford_heading_error_degrees=headingerror, all_accepted_course_and_assets_preserved=True,
                in_game_visual_check=False,in_game_riding_test=False)
    save(O/'v043_independent_validation.json',report)
    qa.update(source_checks_pass=True, independent_v043=report)
    save(O/'source_validation.json',qa)
    print('v043 independent hoist alignment, Ford placement and complete preservation checks passed.',flush=True)


if __name__ == '__main__':
    main()
