"""Remove the four verified scenery obstructions in the relocated v026 sector.

Tree selection checks low mesh vertices against the T09 riding corridor and
v026 terrain. Marker selection checks anchors inside the authored track edge.
An explicit, coordinate-checked object list prevents a broad scenery cleanup.
All retained FBX records and unaffected connections are verified byte for byte.
"""
from pathlib import Path
from collections import Counter
import json, struct, hashlib
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from apply_scenery_patch import parse, encode, property_values
from rebind_scenery import array

R = Path(__file__).resolve().parents[1]
O = R/'V027_OUTPUT'
S = R/'V027_SOURCE'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def values(node):
    return property_values(node['props'], node['count'])

def child(node, name):
    return next(n for n in node['children'] if n['name'] == name)

def fingerprint(node):
    """Hash complete raw node records, excluding rewritten absolute offsets."""
    h = hashlib.sha256()
    h.update(struct.pack('<III', len(node['name']), node['count'], len(node['props'])))
    h.update(node['name']); h.update(node['props']); h.update(node['sentinel'])
    h.update(struct.pack('<I', len(node['children'])))
    for item in node['children']:
        h.update(bytes.fromhex(fingerprint(item)))
    return h.hexdigest()

def geometry_records(nodes):
    objects = next(n for n in nodes if n['name'] == b'Objects')
    connections = next(n for n in nodes if n['name'] == b'Connections')
    models = {values(n)[0]: values(n)[1].split(b'\x00')[0].decode('utf-8')
              for n in objects['children'] if n['name'] == b'Model'}
    g2m = {values(n)[1]: values(n)[2] for n in connections['children']
           if len(values(n)) > 2 and values(n)[2] in models}
    return {models[g2m[values(n)[0]]]: (n, g2m[values(n)[0]])
            for n in objects['children']
            if n['name'] == b'Geometry' and values(n)[0] in g2m}

def vertices(geom):
    # Source FBX uses centimetres and negative Z; PiBoSo exports metre +Z.
    return array(child(geom, b'Vertices')).reshape(-1, 3)*[.01, .01, -.01]

def identify(nodes, output, spec):
    data = dict(np.load(output/'route.npz'))
    q, width = data['q'], data['width']
    tree = cKDTree(q[:-1, :2])
    turns = read(output/'turns.json')
    profiles = read(output/'jump_profiles.json')
    t09 = next(t for t in turns if t['id'] == 'T09')
    r10 = next(p for p in profiles if p['id'] == 'R10')
    r11 = next(p for p in profiles if p['id'] == 'R11')
    berm = next(b for b in read(output/'geometry_spec.json')['berms'] if b['id'] == 'T09')
    half = berm['effective_width_m']/2 + spec['tree_rider_margin_m']
    height = np.fromfile(output/'terrain.raw', '<u2').reshape(2049, 2049)/65535*18
    bounds = np.array(read(output/'geometry_validation.json')['patch_bounds_xz_m'], dtype=float)
    margin = spec['patch_margin_m']
    bounds += [-margin, -margin, margin, margin]
    tree_stations = [t09['arc_start']-5, t09['arc_end']+5]
    marker_stations = [r10['station_end_m']-10, r11['station_end_m']+5]
    candidates = []
    for name, (geom, mid) in geometry_records(nodes).items():
        if not name.startswith(('tree_', 'SOFTCPLAS_marker_')):
            continue
        v = vertices(geom)
        low = v[v[:, 1] < v[:, 1].min()+.55]
        anchor = low[:, [0, 2]].mean(axis=0)
        if not (bounds[0] <= anchor[0] <= bounds[2] and
                bounds[1] <= anchor[1] <= bounds[3]):
            continue
        dist, i = tree.query(anchor)
        station = float(q[i, 3])
        edge = float(dist-width[i]/2)
        item = dict(name=name, geometry_id=values(geom)[0], model_id=mid,
                    anchor_xz_m=anchor.tolist(), station_m=station,
                    centerline_distance_m=float(dist), track_edge_clearance_m=edge,
                    removed=False)
        if name.startswith('tree_'):
            d, idx = tree.query(v[:, [0, 2]])
            in_corridor = ((d < half) & (q[idx, 3] >= tree_stations[0]) &
                           (q[idx, 3] <= tree_stations[1]))
            vv = v[in_corridor]
            if len(vv):
                ground = map_coordinates(height, [(600-vv[:, 2])/600*2048,
                                                    vv[:, 0]/600*2048], order=1, mode='nearest')
                clearance = vv[:, 1]-ground
                intruding = int(np.count_nonzero(clearance < spec['rider_headroom_m']))
                item.update(corridor_vertices=len(vv), low_intruding_vertices=intruding,
                            minimum_headroom_m=float(clearance.min()))
                item['removed'] = intruding > 0
            else:
                item.update(corridor_vertices=0, low_intruding_vertices=0)
        else:
            item['removed'] = marker_stations[0] <= station <= marker_stations[1] and edge < 0
        candidates.append(item)
    limits = dict(patch_bounds_xz_m=bounds.tolist(), tree_station_range_m=tree_stations,
                  marker_station_range_m=marker_stations, tree_riding_half_width_m=half,
                  rider_headroom_m=spec['rider_headroom_m'], marker_track_edge_threshold_m=0)
    return candidates, limits

def check_selection(candidates, spec):
    removed = [c for c in candidates if c['removed']]
    expected = {x['name']: x for x in spec['expected_removals']}
    actual = {x['name']: x for x in removed}
    if set(actual) != set(expected):
        raise RuntimeError('Scenery selection differs from video/source review: '+
                           repr(dict(expected=sorted(expected), actual=sorted(actual))))
    for name, item in actual.items():
        if np.linalg.norm(np.array(item['anchor_xz_m'])-expected[name]['anchor_xz_m']) > .02:
            raise RuntimeError('Unexpected source position for '+name)
    return removed

def remove_objects(before, removed):
    nodes, tail = parse(before)
    if encode(nodes, tail) != before:
        raise RuntimeError('Source FBX does not round-trip byte for byte')
    objects = next(n for n in nodes if n['name'] == b'Objects')
    connections = next(n for n in nodes if n['name'] == b'Connections')
    definitions = next(n for n in nodes if n['name'] == b'Definitions')
    remove_ids = {x[k] for x in removed for k in ('geometry_id', 'model_id')}
    original_records = {values(n)[0]: fingerprint(n) for n in objects['children']}
    original_types = Counter(n['name'] for n in objects['children'] if values(n)[0] in remove_ids)
    unaffected = {n['name']: fingerprint(n) for n in nodes
                  if n['name'] not in (b'Objects', b'Connections', b'Definitions')}
    expected_connections = [fingerprint(n) for n in connections['children']
                            if not any(v in remove_ids for v in values(n)[1:3])]
    objects['children'] = [n for n in objects['children'] if values(n)[0] not in remove_ids]
    connections['children'] = [n for n in connections['children']
                              if not any(v in remove_ids for v in values(n)[1:3])]
    # Definitions include one GlobalSettings record outside Objects. Preserve it.
    for item in definitions['children']:
        if item['name'] == b'Count':
            item['props'] = b'I'+struct.pack('<i', values(item)[0]-len(remove_ids))
        elif item['name'] == b'ObjectType':
            count_removed = original_types[values(item)[0]]
            if count_removed:
                count = child(item, b'Count')
                count['props'] = b'I'+struct.pack('<i', values(count)[0]-count_removed)
    expected_definitions = fingerprint(definitions)
    output = encode(nodes, tail)
    check, _ = parse(output)
    objects2 = next(n for n in check if n['name'] == b'Objects')
    connections2 = next(n for n in check if n['name'] == b'Connections')
    actual_records = {values(n)[0]: fingerprint(n) for n in objects2['children']}
    expected_records = {k: v for k, v in original_records.items() if k not in remove_ids}
    assert actual_records == expected_records, 'Retained FBX object properties/topology changed'
    assert [fingerprint(n) for n in connections2['children']] == expected_connections
    assert {n['name']: fingerprint(n) for n in check if n['name'] in unaffected} == unaffected
    assert fingerprint(next(n for n in check if n['name'] == b'Definitions')) == expected_definitions
    assert not remove_ids.intersection(actual_records)
    return output, dict(retained_object_records_verified=len(actual_records),
                        object_records_removed=len(original_records)-len(actual_records),
                        retained_object_properties_unchanged=True,
                        retained_connections_unchanged=True, global_axes_metadata_unchanged=True,
                        definition_counts_corrected=True)

def main():
    spec = read(S/'scenery_fix.json')
    path = O/'scenery.fbx'
    before = path.read_bytes()
    assert digest(before) == spec['v026_scenery_sha256'], 'Unexpected accepted v026 scenery source'
    nodes, _ = parse(before)
    candidates, limits = identify(nodes, O, spec)
    save(R/'DOCUMENTATION/v027_scenery_candidates.json', dict(
        limits=limits, candidates=candidates,
        proposed_removals=[x for x in candidates if x['removed']]))
    removed = check_selection(candidates, spec)
    output, preservation = remove_objects(before, removed)
    check, _ = parse(output)
    after, _ = identify(check, O, spec)
    conflicts = [x for x in after if x['removed']]
    assert not conflicts, 'Verified corridor obstructions remain after removal'
    probes = []
    for name, (geom, _) in sorted(geometry_records(check).items()):
        v = vertices(geom)
        for p in v[::max(1, len(v)//5)]:
            if np.isfinite(p).all() and p[0] > .001 and p[2] > .001:
                probes.append(p.tolist()); break
        if len(probes) >= 32:
            break
    assert len(probes) >= 24, 'Insufficient retained scenery native coordinate probes'
    path.write_bytes(output)
    save(O/'native_coordinate_probes.json', dict(expected_xyz_metres=probes))
    qa = dict(version='v027', baseline_commit=spec['baseline_commit'],
              source_scenery_sha256=digest(before), output_scenery_sha256=digest(output),
              selection_limits=limits, removed=removed,
              removed_tree_count=sum(x['name'].startswith('tree_') for x in removed),
              removed_marker_count=sum(x['name'].startswith('SOFTCPLAS_marker_') for x in removed),
              targeted_candidates=candidates, remaining_conflicts=conflicts,
              coordinate_probes=len(probes), **preservation,
              in_game_riding=False, scenery_checks_pass=True)
    save(R/'DOCUMENTATION/v027_scenery_validation.json', qa)
    print(json.dumps({k: v for k, v in qa.items() if k != 'targeted_candidates'}, indent=2), flush=True)

if __name__ == '__main__':
    main()
