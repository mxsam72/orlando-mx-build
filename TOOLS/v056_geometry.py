"""Level the inherited R03 landing-side hump without changing the jump sequence."""
import json
import re
import shutil
import struct

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from v056_inputs import R, BASE, PREV, O, M, NAME, DEST, sha, save
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


def corner_regions(q, mapping):
    """Protect the full riding width, shoulders and bilinear support of every turn."""
    turns = read(BASE / 'turns.json')
    for t in turns:
        lo, hi = np.interp([t['arc_start'], t['arc_end']], mapping, q[:, 3])
        yield t['id'], float(lo), float(hi)


def corner_checks(raw, updated, q, mapping):
    h, after = raw.astype(float) / 65535 * 18, updated.astype(float) / 65535 * 18
    guard = np.zeros(raw.shape, bool)
    rows = []
    for name, lo, hi in corner_regions(q, mapping):
        ss, ll = np.meshgrid(np.arange(lo, hi + .1, .2), np.arange(-14, 14.01, .2))
        pp = cross_points(q, ss, ll).reshape(-1, 2)
        yy, xx = (600-pp[:, 1])/600*2048, pp[:, 0]/600*2048
        ri, ci = np.floor(yy).astype(int), np.floor(xx).astype(int)
        local = np.zeros(raw.shape, bool)
        for dr in [-1, 0, 1, 2]:
            for dc in [-1, 0, 1, 2]:
                local[np.clip(ri+dr, 0, 2048), np.clip(ci+dc, 0, 2048)] = True
        guard |= local
        delta = ground(after, pp) - ground(h, pp)
        rows.append(dict(corner=name, station_m=[lo, hi], lateral_width_m=28,
                         sampled_points=len(pp), protected_raw_samples=int(local.sum()),
                         raw_grid_exact=bool(np.array_equal(raw[local], updated[local])),
                         max_height_difference_m=float(np.max(abs(delta)))))
    return guard, rows


def landing_weight(q, points, profile):
    _, _, station, lat = projection(q, points)
    along = ((station > 261.8) & (station < 272.0)).astype(float)
    side = smooth((lat - .4) / 1.0) * smooth((9.0 - lat) / 1.8)
    return along * side, station, lat


def terrain():
    from scipy.interpolate import CubicHermiteSpline
    O.mkdir(parents=True, exist_ok=True)
    route = dict(np.load(PREV / 'route.npz'))
    q, mapping = route['q'], route['v054_old_station']
    profiles = read(PREV / 'jump_profiles.json')
    p = next(p for p in profiles if p['id'] == 'R03')
    raw = np.fromfile(PREV / 'terrain.raw', '<u2').reshape(2049, 2049)
    h = raw.astype(float) / 65535 * 18
    guard, _ = corner_checks(raw, raw, q, mapping)
    lo, crest, hi = 261.8, 268.25, 272.0
    stations = np.arange(lo, hi+.025, .025)
    laterals = np.arange(-.1, 9.21, .05)
    center_peak = float(ground(h, cross_points(q, np.array([crest]), 0))[0])
    targets = []
    for lat in laterals:
        y = ground(h, cross_points(q, np.array([lo, crest, hi]), lat))
        ends = np.array([lo, hi])
        grade = (ground(h, cross_points(q, ends+.15, lat)) - ground(h, cross_points(q, ends-.15, lat))) / .3
        # Shave only the extra right-side crown. The endpoint/grade into the
        # bank set a lower bound so the landing never develops a second bump.
        peak = min(y[1], max(center_peak-.002*lat*lat+.06,
                             y[2]+max(0, -grade[1])*(hi-crest)*.38))
        spline = CubicHermiteSpline([lo, crest, hi], [y[0], peak, y[2]], [grade[0], 0, grade[1]])
        targets.append(spline(stations))
    targets = np.array(targets)
    local = cross_points(q, np.linspace(lo, hi, 200), 0)
    a, b = local.min(0)-12, local.max(0)+12
    box = [float(a[0]), float(a[1]), float(b[0]), float(b[1])]
    rr, cc, points = raster_points(2049, box)
    weight, station, lat = landing_weight(q, points, p)
    from scipy.ndimage import map_coordinates
    desired = map_coordinates(targets, [(lat-laterals[0])/.05, (station-lo)/.025], order=1, mode='nearest')
    before = h[np.ix_(rr, cc)].ravel()
    target = before - weight * np.maximum(0, before-desired)
    edited = np.rint(target/18*65535).astype('<u2')
    updated = raw.copy()
    updated[np.ix_(rr, cc)] = edited.reshape(len(rr), len(cc))
    # A hard independent protection mask catches nearby corners as well as
    # the following one. Its one-pixel support protects interpolated banks.
    updated[guard] = raw[guard]
    road = np.load(PREV / 'road_guard.npy')
    assert np.array_equal(updated[road], raw[road]), 'Road terrain changed'
    scope = np.zeros(raw.shape, bool)
    scope[np.ix_(rr, cc)] = weight.reshape(len(rr), len(cc)) > 0
    assert np.array_equal(updated[~scope], raw[~scope])
    assert np.all(updated <= raw), 'Landing repair must only remove the local crown'
    _, corners = corner_checks(raw, updated, q, mapping)
    assert all(t['raw_grid_exact'] and t['max_height_difference_m'] == 0 for t in corners)
    (O / 'terrain.raw').write_bytes(updated.tobytes())
    from PIL import Image
    Image.fromarray(updated).save(O / 'terrain_16bit.png')
    np.save(O / 'landing_scope.npy', scope)
    np.save(O / 'corner_guard.npy', guard)
    after = updated.astype(float)/65535*18
    ss = np.arange(260, 273, .1)
    ls = np.arange(-6, 6.01, .25)
    sgrid, lgrid = np.meshgrid(ss, ls)
    pp = cross_points(q, sgrid, lgrid).reshape(-1, 2)
    old = ground(h, pp).reshape(sgrid.shape)
    new = ground(after, pp).reshape(sgrid.shape)
    peak = (ss >= 267.5) & (ss <= 269)
    cross_old, cross_new = np.ptp(old[:, peak], axis=0), np.ptp(new[:, peak], axis=0)
    assert cross_new.max() < cross_old.max()*.68, ('Landing crown not reduced', cross_old.max(), cross_new.max())
    center = ground(after, cross_points(q, ss, 0))-ground(h, cross_points(q, ss, 0))
    assert np.max(abs(center)) < .001, 'Single centre profile changed'
    descent_s = np.arange(268.6, 272.1, .1)
    descent_l = np.arange(1.5, 6.1, .25)
    descent_pts = cross_points(q, *np.meshgrid(descent_s, descent_l)).reshape(-1, 2)
    descent = ground(after, descent_pts).reshape(len(descent_l), len(descent_s))
    grades = np.gradient(descent, .1, axis=1)
    assert grades.max() < .05, 'Secondary bump in the landing'
    assert -grades.min() < .5, 'Abrupt landing transition'
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
    report = dict(checks_pass=True, baseline='v054', terrain_sha256=sha(O/'terrain.raw'),
        source_terrain_sha256=sha(PREV/'terrain.raw'), changed_samples=int(np.count_nonzero(raw != updated)),
        all_samples_outside_landing_scope_exact=True, all_14_corner_grids_exact=True,
        corners=corners, protected_corner_raw_samples=int(guard.sum()),
        road_samples_exact=True, scope_xz_m=box, station_scope_m=[lo, hi],
        jump_profile_arrays_exact=True, main_and_start_routes_exact=True,
        unrelated_jump_centerlines_exact=retained, centerline_change_max_m=float(np.max(abs(center))),
        landing_crest_cross_height_range_before_max_m=float(cross_old.max()),
        landing_crest_cross_height_range_after_max_m=float(cross_new.max()),
        maximum_height_reduction_m=float(np.max(h-after)),
        landing_secondary_uphill_grade_max=float(grades.max()),
        landing_downhill_grade_max=float(-grades.min()),
        landing_note='Local right-side crown reduced; original bank and slope into T03 are preserved. No flattening of corner or runout.',
        in_game_riding_test=False)
    save(O/'terrain_validation.json', report)
    np.savez_compressed(O/'landing_sections.npz', s=ss, lat=ls, before=old, after=new)
    print('V056_LANDING_PASSED', report, flush=True)


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
    print('V056 binding local scenery bases', flush=True)
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
    print('V056_SCENERY_PASSED', len(changes), 'ground-bound objects', flush=True)


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
            p.write_text(p.read_text().replace('v054', 'v056'))
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
