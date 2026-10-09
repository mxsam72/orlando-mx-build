"""Independent native-camera flag and complete source/parking preservation audit."""
import copy
from collections import Counter
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import MultiPoint, LineString, box
from v042_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from verify_v037_source import faces
from build_v040 import face_uv
from v037_common import ground
from rebind_scenery import array

def camera_checks(g):
    """Use outward triangle winding in native X/Z/Y, independent of builder."""
    v = vertices(g)
    checks = []
    for f, uv in zip(faces(g), face_uv(g)):
        native = v[f]
        rendered = native[:, [0, 2, 1]]
        normal = np.cross(rendered[1]-rendered[0], rendered[2]-rendered[0])
        normal /= np.linalg.norm(normal)
        camera = rendered.mean(0) + normal * 30
        forward = rendered.mean(0) - camera
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, [0., 0., 1.])
        right /= np.linalg.norm(right)
        uv_to_world = np.linalg.lstsq(np.c_[uv, np.ones(len(uv))], rendered, rcond=None)[0]
        checks.append(dict(screen_right_u=float(right @ uv_to_world[0]),
                           screen_up_v=float(uv_to_world[1, 2]),
                           front_facing=float(normal @ (camera-rendered.mean(0)))))
    return checks

def grid(poly, spacing=.20):
    x0, z0, x1, z1 = poly.bounds
    xx, zz = np.meshgrid(np.arange(x0, x1+spacing/2, spacing), np.arange(z0, z1+spacing/2, spacing))
    p = np.c_[xx.ravel(), zz.ravel()]
    return p[shapely.covers(poly, shapely.points(p))]

def alpha_at(name, points):
    a = np.asarray(Image.open(O/'masks'/name).getchannel('A'))
    return map_coordinates(a, [(600-points[:, 1])/600*(a.shape[0]-1), points[:, 0]/600*(a.shape[1]-1)], order=1)

def main():
    cfg = read(S/'update.json')
    qa = read(O/'source_validation.json')
    braw = (BASE/'scenery.fbx').read_bytes()
    nraw = (O/'scenery.fbx').read_bytes()
    bn, bt = parse(braw)
    nn, nt = parse(nraw)
    assert encode(nn, nt) == nraw
    rb, rn = geometry_records(bn), geometry_records(nn)
    assert set(rb).issubset(rn) and len(rn)-len(rb) == 33
    bo = {values(n)[0]: n for n in next(n for n in bn if n['name'] == b'Objects')['children']}
    no = {values(n)[0]: n for n in next(n for n in nn if n['name'] == b'Objects')['children']}
    flagid = values(rb[cfg['flag_geometry']][0])[0]
    assert set(bo).issubset(no)
    changed = {i for i in bo if fingerprint(bo[i]) != fingerprint(no[i])}
    assert changed == {flagid}
    original = rb[cfg['flag_geometry']][0]
    current = rn[cfg['flag_geometry']][0]
    for c in original['children']:
        if c['name'] != b'LayerElementUV':
            assert fingerprint(c) == fingerprint(child(current, c['name'])), c['name']
    l0, l1 = child(original, b'LayerElementUV'), child(current, b'LayerElementUV')
    for c in l0['children']:
        if c['name'] != b'UV':
            assert fingerprint(c) == fingerprint(child(l1, c['name']))
    uv0, uv1 = array(child(l0, b'UV')).reshape(-1, 2), array(child(l1, b'UV')).reshape(-1, 2)
    assert np.array_equal(uv0[:, 1], uv1[:, 1])
    assert np.array_equal(1-uv0[:, 0], uv1[:, 0])
    before, after = camera_checks(original), camera_checks(current)
    assert len(after) == 4
    assert all(c['screen_right_u'] < 0 for c in before)
    assert all(c['screen_right_u'] > 0 and c['screen_up_v'] > 0 and c['front_facing'] > 0 for c in after)
    fv = vertices(current)
    center = (fv.min(0)+fv.max(0))/2
    normals = []
    for f in faces(current):
        v = fv[f]
        cross = np.cross(v[1]-v[0], v[2]-v[0])
        assert cross @ (v.mean(0)-center) < 0
        normals.append(-cross/np.linalg.norm(cross))
    assert np.isclose(np.ptp(fv @ normals[0]), .30)
    with Image.open(O/'facility_textures/v040_american_flag.tga') as im:
        assert im.mode == 'RGB' and im.size == (2048, 1024)
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
    textures = 0
    for folder in ['masks', 'materials', 'facility_textures']:
        for p in (BASE/folder).iterdir():
            if p.is_file():
                assert sha(p) == sha(O/folder/p.name), (folder, p.name)
                if p.suffix == '.tga':
                    textures += 1
    preserved = len(rb)-1
    for name in rb:
        if name != cfg['flag_geometry']:
            assert fingerprint(rb[name][0]) == fingerprint(rn[name][0]), name
    truckqa = read(O/'v042_vehicle_validation.json')
    assert truckqa['count'] == 3 and truckqa['color_order'] == ['pink', 'orange', 'yellow']
    h = np.fromfile(O/'terrain.raw', '<u2').reshape(2049, 2049)/65535*18
    d = dict(np.load(O/'route.npz'))
    a = dict(np.load(O/'practice_access.npz'))
    # The whole new truck footprint is outside all protected riding corridors.
    corridors = [('MX course', LineString(d['q'][:, :2]).buffer(float(d['width'].max()/2)+1.5)),
                 ('race start', LineString(d['start'][:, :2]).buffer(13)),
                 ('practice', LineString(a['lane'][:, :2]).buffer(5.5)),
                 ('pit connector', LineString(a['connector'][:, :2]).buffer(5.0))]
    old_obstacles = []
    for name, (g, mid) in rb.items():
        if name.startswith(('TRK', 'drainage_water', 'v037_oval_mark')):
            continue
        v = vertices(g)
        low = v[v[:, 1]-ground(h, v[:, [0, 2]]) < 3.2]
        if len(low):
            old_obstacles.append((name, box(*low[:, [0, 2]].min(0), *low[:, [0, 2]].max(0))))
    footprints = []
    parking = []
    links = [values(n) for n in nl]
    for spec, entry in zip(cfg['new_trucks'], truckqa['vehicles']):
        group = entry['group']
        parts = {n: (g, mid) for n, (g, mid) in rn.items() if n.startswith(group+'_')}
        assert len(parts) == 11 and entry['color'] == spec['color']
        rotation = np.asarray(entry['rotation'])
        assert np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-10) and np.isclose(np.linalg.det(rotation), 1)
        allv = np.concatenate([vertices(g) for g, mid in parts.values()])
        footprint = MultiPoint(allv[:, [0, 2]]).convex_hull
        assert box(245, 90, 375, 170).covers(footprint), group
        footprints.append(footprint)
        samples = grid(footprint.buffer(.30))
        road_max = int(alpha_at('v024_pit_roads.tga', samples).max())
        assert road_max < 32, (group, 'gravel road conflict', road_max)
        assert int(alpha_at('grass.tga', samples).min()) > 180, (group, 'not on grass')
        nearest_name, nearest_dist = min(((n, footprint.distance(p)) for n, p in old_obstacles), key=lambda item: item[1])
        assert nearest_dist > cfg['minimum_obstacle_clearance_m'], (group, nearest_name, nearest_dist)
        route_distances = {name: float(footprint.distance(poly)) for name, poly in corridors}
        assert min(route_distances.values()) > cfg['minimum_route_clearance_m'], (group, route_distances)
        srcv = np.concatenate([vertices(g) for n, (g, mid) in rb.items() if n.startswith('truck_jordan_')])
        src_center = (srcv[:, [0, 2]].min(0)+srcv[:, [0, 2]].max(0))/2
        src_bottom = srcv[:, 1].min()
        low = srcv[:, 1]-src_bottom < .065
        transformed = (srcv-[src_center[0], src_bottom, src_center[1]]) @ rotation.T + entry['origin_xyz_m']
        assert np.allclose(transformed, allv, atol=1e-9)
        gap = allv[low, 1]-ground(h, allv[low][:, [0, 2]])
        assert gap.min() > -1e-8 and gap.max() < cfg['maximum_wheel_ground_gap_m']
        for n, (g, mid) in parts.items():
            suffix = n.removeprefix(group+'_')
            g0 = rb['truck_jordan_'+suffix][0]
            for layer in [b'PolygonVertexIndex', b'LayerElementUV', b'LayerElementMaterial']:
                assert fingerprint(child(g0, layer)) == fingerprint(child(g, layer)), (n, layer)
            assert values(child(no[mid], b'Culling')) == [b'CullingOnCCW']
            if suffix == 'cyber_steel':
                material = next(no[v[1]] for v in links if v[2] == mid and no.get(v[1], {}).get('name') == b'Material')
                assert values(material)[1].split(b'\0')[0] == ('v042_cybertruck_'+spec['color']).encode()
        head = vertices(parts[group+'_headlight'][0])[:, [0, 2]].mean(0)
        tail = vertices(parts[group+'_red_light'][0])[:, [0, 2]].mean(0)
        heading = np.degrees(np.arctan2(*(head-tail)[::-1]))
        error = abs((heading-spec['heading_degrees']+180)%360-180)
        assert error < 1.5
        parking.append(dict(group=group, color=spec['color'], center_xz_m=spec['center_xz_m'],
                            nearest_existing_obstacle=nearest_name, obstacle_clearance_m=float(nearest_dist),
                            riding_corridor_clearance_m=route_distances, gravel_road_alpha_max=road_max,
                            wheel_ground_clearance_min_m=float(gap.min()), wheel_ground_clearance_max_m=float(gap.max()),
                            heading_error_degrees=float(error)))
        with Image.open(O/'facility_textures'/('v042_cybertruck_'+spec['color']+'.tga')) as im:
            assert im.mode == 'RGB' and im.size == (256, 256)
            assert np.allclose(np.asarray(im).mean((0, 1)), cfg['truck_paint_rgb'][spec['color']], atol=1)
    assert min(footprints[i].distance(footprints[j]) for i in range(3) for j in range(i+1, 3)) > 10
    # Each inherited baseline probe still addresses retained geometry; no old
    # probe coordinates need changing for a UV-only repair and added models.
    current_vertices = np.concatenate([vertices(g) for g, mid in rn.values()])
    tree = cKDTree(current_vertices)
    for filename in ['native_coordinate_probes.json', 'v041_native_probes.json', 'v042_native_probes.json',
                     'memorial_support_native_probes.json', 'qwikchute_native_probes.json', 'holeshot_native_probes.json']:
        points = read(O/filename)['expected_xyz_metres']
        assert tree.query(points)[0].max() < 1e-7, filename
    report = dict(checks_pass=True, preserved_original_geometry_records=preserved,
                  retained_original_object_records_exact=len(bo)-1,
                  only_flag_horizontal_uv_array_changed=True, flag_native_camera_orientation_checks=after,
                  flag_both_faces_screen_right_u_positive=True, flag_opaque_faces_separated_m=.30,
                  all_original_texture_files_exact=textures, new_truck_count=3,
                  added_truck_colors=['pink', 'orange', 'yellow'], color_sequence_continued=True,
                  parking_checks=parking, all_three_trucks_on_grass_clear_of_roads_and_routes=True,
                  cloned_truck_topology_uvs_and_opaque_materials_retained=True,
                  original_four_pit_displays_and_all_existing_trucks_unchanged=True,
                  v041_gap_fill_grandstands_crocodile_unchanged=True,
                  memorial_qwikchute_speed_world_signs_and_restroom_unchanged=True,
                  entire_MX_heightmap_freestyle_soils_race_and_start_unchanged=True,
                  optimized_texture_resolutions_preserved=True,
                  in_game_visual_check=False, in_game_riding_test=False)
    save(O/'v042_independent_validation.json', report)
    qa.update(source_checks_pass=True, independent_v042=report)
    save(O/'source_validation.json', qa)
    print('v042 independent flag orientation, preservation and parking checks passed.', flush=True)

if __name__ == '__main__':
    main()
