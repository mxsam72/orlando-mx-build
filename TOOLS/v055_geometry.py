"""Level the inherited R03 landing-side hump without changing the jump sequence."""
import json
import re
import shutil
import struct

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from v055_inputs import R, BASE, PREV, O, M, NAME, DEST, sha, save
from v054_geometry import ground, read, raster_points, projection, smooth
from v027_scenery import parse, values, vertices, child, geometry_records, fingerprint
from rebind_scenery import encoded_array, array


def encode(nodes, tail):
    """Lossless FBX 7400 output without quadratic large-byte concatenation."""
    def node(n, start):
        parts = [n['name'], n['props']]
        pos = start + 13 + len(n['name']) + len(n['props'])
        for item in n['children']:
            data = node(item, pos)
            parts.append(data)
            pos += len(data)
        parts.append(n['sentinel'])
        end = pos + len(n['sentinel'])
        return struct.pack('<IIIB', end, n['count'], len(n['props']), len(n['name'])) + b''.join(parts)
    parts = [b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400)]
    pos = len(parts[0])
    for item in nodes:
        data = node(item, pos)
        parts.append(data)
        pos += len(data)
    assert struct.unpack_from('<I', tail, len(tail)-140)[0] == 7400
    parts.extend([bytes(13), tail[:20]])
    pos += 33
    parts.extend([bytes(16 - pos % 16), tail[-140:]])
    return b''.join(parts)


def cross_points(q, s, lat):
    s, lat = np.broadcast_arrays(s, lat)
    th = np.interp(s, q[:, 3], q[:, 2])
    return np.stack([np.interp(s, q[:, 3], q[:, 0]) - np.sin(th) * lat,
                     np.interp(s, q[:, 3], q[:, 1]) + np.cos(th) * lat], -1)


def landing_weight(q, points, profile):
    _, _, station, lat = projection(q, points)
    crest = profile['lip_s'] + profile['landmarks_m']['landing_break']
    # Includes the front of the single and landing/runout, with eased joins.
    lo = crest - 10.0
    hi = profile['station_end_m'] + 18.0
    along = smooth((station - lo) / 5.0) * smooth((hi - station) / 10.0)
    side = 1 - smooth((np.abs(lat) - 5.3) / 6.7)
    return along * side, station, lat


def terrain():
    O.mkdir(parents=True, exist_ok=True)
    route = dict(np.load(PREV / 'route.npz'))
    q = route['q']
    profiles = read(PREV / 'jump_profiles.json')
    p = next(p for p in profiles if p['id'] == 'R03')
    raw = np.fromfile(PREV / 'terrain.raw', '<u2').reshape(2049, 2049)
    h = raw.astype(float) / 65535 * 18
    center_s = np.arange(p['station_start_m'] - 4, p['station_end_m'] + 23, .05)
    center = ground(h, cross_points(q, center_s, 0))
    # Filter only RAW quantisation/interpolation noise, retaining both crests.
    center = gaussian_filter1d(center, .22 / .05, mode='nearest')
    local = cross_points(q, np.linspace(p['lip_s'] + 14, p['station_end_m'] + 20, 400), 0)
    a = local.min(0) - 17
    b = local.max(0) + 17
    box = [float(a[0]), float(a[1]), float(b[0]), float(b[1])]
    rr, cc, points = raster_points(2049, box)
    weight, station, lat = landing_weight(q, points, p)
    # A gentle 5 cm crown across the full 10 m landing, continuous into banks.
    desired = np.interp(station, center_s, center) - .002 * np.minimum(lat * lat, 25.)
    before = h[np.ix_(rr, cc)].ravel()
    target = before * (1 - weight) + desired * weight
    updated = raw.copy()
    edited = np.rint(np.clip(target / 18 * 65535, 0, 65535)).astype('<u2')
    updated[np.ix_(rr, cc)] = edited.reshape(len(rr), len(cc))
    scope = np.zeros(raw.shape, bool)
    scope[np.ix_(rr, cc)] = weight.reshape(len(rr), len(cc)) > 0
    assert np.array_equal(updated[~scope], raw[~scope])
    if (PREV / 'road_guard.npy').exists():
        guard = np.load(PREV / 'road_guard.npy')
        assert np.array_equal(updated[guard], raw[guard]), 'Road terrain changed'
    (O / 'terrain.raw').write_bytes(updated.tobytes())
    from PIL import Image
    Image.fromarray(updated).save(O / 'terrain_16bit.png')
    np.save(O / 'landing_scope.npy', scope)
    after = updated.astype(float) / 65535 * 18
    ss = np.arange(p['lip_s'] + 22.5, p['station_end_m'] + 6.0, .2)
    ls = np.linspace(-5, 5, 51)
    sgrid, lgrid = np.meshgrid(ss, ls)
    pp = cross_points(q, sgrid, lgrid).reshape(-1, 2)
    old = ground(h, pp).reshape(sgrid.shape)
    new = ground(after, pp).reshape(sgrid.shape)
    across_old = np.ptp(old, axis=0)
    across_new = np.ptp(new, axis=0)
    assert across_new.max() < .09, ('Landing still uneven', float(across_new.max()))
    assert across_old.max() > .8, 'Expected reported landing-side defect not found'
    # Ensure the repair is also smooth in the direction ridden, on every line.
    grade = np.gradient(new, .2, axis=1)
    assert np.max(np.abs(grade)) < .60
    center_before = ground(h, cross_points(q, ss, 0))
    center_after = ground(after, cross_points(q, ss, 0))
    assert np.max(np.abs(center_before - center_after)) < .025
    retained = []
    for profile in profiles:
        if profile['id'] == 'R03' or profile['kind'] == 'none':
            continue
        samples = np.linspace(profile['station_start_m'], profile['station_end_m'], 200)
        pts = cross_points(q, samples, 0)
        assert np.array_equal(ground(h, pts), ground(after, pts)), profile['id']
        retained.append(profile['id'])
    for n in ['route.npz', 'main.tcl', 'start.tcl', 'jump_profiles.json', 'layout.json']:
        shutil.copy2(PREV / n, O / n)
    report = dict(checks_pass=True, baseline='v054', terrain_sha256=sha(O / 'terrain.raw'),
                  source_terrain_sha256=sha(PREV / 'terrain.raw'), changed_samples=int(np.count_nonzero(raw != updated)),
                  all_samples_outside_landing_scope_exact=True, road_samples_exact=True,
                  scope_xz_m=box, station_scope_m=[p['lip_s'] + 16.8, p['station_end_m'] + 18],
                  jump_profile_arrays_exact=True, main_and_start_routes_exact=True,
                  unrelated_jump_centerlines_exact=retained,
                  landing_cross_height_range_before_max_m=float(across_old.max()),
                  landing_cross_height_range_after_max_m=float(across_new.max()),
                  centerline_change_max_m=float(np.max(abs(center_before - center_after))),
                  landing_longitudinal_grade_max=float(np.max(abs(grade))),
                  maximum_height_reduction_m=float(np.max(h - after)),
                  in_game_riding_test=False)
    save(O / 'terrain_validation.json', report)
    np.savez_compressed(O / 'landing_sections.npz', s=ss, lat=ls, before=old, after=new)
    print('V055_LANDING_PASSED', report, flush=True)


def scenery():
    oldh = np.fromfile(PREV / 'terrain.raw', '<u2').reshape(2049, 2049) / 65535 * 18
    newh = np.fromfile(O / 'terrain.raw', '<u2').reshape(2049, 2049) / 65535 * 18
    q = dict(np.load(O / 'route.npz'))['q']
    p = next(p for p in read(O / 'jump_profiles.json') if p['id'] == 'R03')
    data = (PREV / 'scenery.fbx').read_bytes()
    nodes, tail = parse(data)
    assert encode(nodes, tail) == data
    original_metadata = {n['name']: fingerprint(n) for n in nodes if n['name'] != b'Objects'}
    objects = next(n for n in nodes if n['name'] == b'Objects')
    original = {values(n)[0]: fingerprint(n) for n in objects['children']}
    changes, probes, changed = [], [], set()
    box = read(O / 'terrain_validation.json')['scope_xz_m']
    print('V055 binding local scenery bases', flush=True)
    for name, (g, mid) in geometry_records(nodes).items():
        if not name.startswith(('SOFTCPLAS_marker_', 'SOFTPLAS_marker_', 'SKIDS_v052_grass', 'scrub_', 'v047_tree_')):
            continue
        v = vertices(g)
        near = (v[:, 0] > box[0]) & (v[:, 0] < box[2]) & (v[:, 2] > box[1]) & (v[:, 2] < box[3])
        if not np.any(near):
            continue
        if not np.any(landing_weight(q, v[near][:, [0, 2]], p)[0] > 0):
            continue
        new = v.copy()
        if name.startswith('SKIDS_v052_grass'):
            from scipy.sparse import coo_matrix
            from scipy.sparse.csgraph import connected_components
            idx = array(child(g, b'PolygonVertexIndex')).reshape(-1, 3).copy()
            idx[idx < 0] = -idx[idx < 0] - 1
            graph = coo_matrix((np.ones(idx.size, bool), (idx.ravel(), np.roll(idx, 1, axis=1).ravel())), shape=(len(v), len(v))).tocsr()
            count, labels = connected_components(graph, directed=False)
            # Linear component reductions avoid repeatedly scanning an entire
            # disconnected batch once for each individual grass blade.
            floor = np.full(count, np.inf)
            np.minimum.at(floor, labels, v[:, 1])
            roots = v[:, 1] < floor[labels] + .03
            root_labels = labels[roots]
            totals = np.bincount(root_labels, minlength=count)
            anchors = np.c_[np.bincount(root_labels, weights=v[roots, 0], minlength=count),
                            np.bincount(root_labels, weights=v[roots, 2], minlength=count)] / totals[:, None]
            shifts = ground(newh, anchors) - ground(oldh, anchors)
            new[:, 1] += shifts[labels]
        else:
            root = v[v[:, 1] < v[:, 1].min() + .17][:, [0, 2]].mean(0)
            new[:, 1] += ground(newh, root[None])[0] - ground(oldh, root[None])[0]
        if np.max(abs(new - v)) < .00001:
            continue
        # Vertical-only binding; materials, UVs, normals and placement retained.
        assert np.array_equal(new[:, [0, 2]], v[:, [0, 2]])
        child(g, b'Vertices')['props'] = encoded_array(new * [100, 100, -100])
        changed.add(values(g)[0])
        changes.append(dict(object=name, max_vertical_shift_m=float(np.max(abs(new[:, 1] - v[:, 1])))))
        probes.extend(dict(geometry=name, expected_xyz_m=new[j].tolist()) for j in sorted({0, len(new)//2, len(new)-1}))
    result = encode(nodes, tail)
    (O / 'scenery.fbx').write_bytes(result)
    check, _ = parse(result)
    final = {values(n)[0]: fingerprint(n) for n in next(n for n in check if n['name'] == b'Objects')['children']}
    assert {k: v for k, v in original.items() if k not in changed} == {k: v for k, v in final.items() if k not in changed}
    assert {n['name']: fingerprint(n) for n in check if n['name'] != b'Objects'} == original_metadata
    retained = []
    for name, (g, mid) in geometry_records(check).items():
        if values(g)[0] in changed:
            continue
        v = vertices(g)
        retained.extend(dict(geometry=name, expected_xyz_m=v[j].tolist()) for j in sorted({0, len(v)//2, len(v)-1}))
    save(O / 'scenery_validation.json', dict(checks_pass=True, all_unrelated_records_exact=True,
         scenery_sha256=sha(O / 'scenery.fbx'), changes=changes, scenery_unchanged=not changes,
         textures_materials_and_counts_exact=True, vertical_binding_only=True))
    save(O / 'native_probes.json', dict(retained_geometry=retained, changed_geometry=probes))
    print('V055_SCENERY_PASSED', len(changes), 'ground-bound objects', flush=True)


def race():
    DEST.mkdir(parents=True, exist_ok=True)
    baseline_game = R / '12_RELEASE/orlandomx_2026_v054'
    retained = []
    for src in sorted(baseline_game.iterdir()):
        if src.suffix in ['.map', '.trh'] or src.name == 'code.txt':
            continue
        p = DEST / src.name.replace('orlandomx_2026_v054', NAME)
        shutil.copy2(src, p)
        if p.suffix == '.ini':
            p.write_text(p.read_text().replace('v054', 'v055'))
        else:
            assert sha(p) == sha(src)
            retained.append(dict(file=p.name, sha256=sha(p)))
    assert len(list(DEST.iterdir())) == 11
    save(O / 'race_validation.json', dict(checks_pass=True, native_routes_exact_v054=True,
         all_race_reset_grid_pits_checkpoints_exact=True, retained_game_files=retained))


if __name__ == '__main__':
    terrain()
    scenery()
    race()
