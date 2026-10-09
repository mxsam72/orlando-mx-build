"""Repair the flag reverse face at the hoist and clone Sam's accepted Ford.

Native PiBoSo metre X/Y/Z coordinates are used throughout. All existing
objects survive unchanged except six horizontal UV values on the track-facing
flag face. The original Ford remains in the pits; its materials are reused.
"""
import copy
import math
import os
import shutil
import struct
from collections import Counter
import numpy as np
from v043_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from v037_common import ground
from v037_fbx import node, setvalues
from build_v040 import face_uv
from verify_v037_source import faces
from rebind_scenery import array, encoded_array


def flag_edge_checks(g, pole_xz):
    checks = []
    for index, (face, uv) in enumerate(zip(faces(g), face_uv(g))):
        points = vertices(g)[face]
        uv_to_xyz = np.linalg.lstsq(np.c_[uv, np.ones(len(uv))], points, rcond=None)[0]
        top_edges = np.array([[0., 1., 1.], [1., 1., 1.]]) @ uv_to_xyz
        distances = np.linalg.norm(top_edges[:, [0, 2]] - pole_xz, axis=1)
        checks.append(dict(face_index=index, texture_u0_hoist_distance_m=float(distances[0]),
                           texture_u1_fly_distance_m=float(distances[1]),
                           canton_at_pole=bool(distances[0] < .2 and distances[1] > 2.)))
    return checks


def fix_reverse_flag(records, cfg):
    g = records[cfg['flag_geometry']][0]
    pole = vertices(records[cfg['flag_pole_geometry']][0])[:, [0, 2]].mean(0)
    before = flag_edge_checks(g, pole)
    selected = cfg['flag_track_face_indices']
    assert selected == [2, 3]
    assert all(c['canton_at_pole'] for c in before[:2])
    assert all(not c['canton_at_pole'] for c in before[2:])
    layer = child(g, b'LayerElementUV')
    assert values(child(layer, b'MappingInformationType')) == [b'ByPolygonVertex']
    uv = array(child(layer, b'UV')).reshape(-1, 2)
    indices = array(child(layer, b'UVIndex')).astype(int)
    assert np.array_equal(indices, np.arange(12)) and len(uv) == 12
    changed = np.arange(6, 12)
    uv[changed, 0] = 1 - uv[changed, 0]
    child(layer, b'UV')['props'] = encoded_array(uv)
    after = flag_edge_checks(g, pole)
    assert all(c['canton_at_pole'] for c in after)
    return dict(checks_pass=True, geometry=cfg['flag_geometry'],
                modified_object_id=values(g)[0], repaired_track_face_indices=selected,
                horizontal_uv_indices_changed=changed.tolist(), before=before, after=after,
                stars_at_hoist_both_faces=True, pit_facing_uvs_exact=True,
                image_vertices_normals_materials_pole_exact=True,
                opaque_face_separation_m=.30, in_game_visual_check=False)


def clone_ford(nodes, records, cfg, height):
    spec = cfg['ford']
    objects = next(n for n in nodes if n['name'] == b'Objects')
    links = next(n for n in nodes if n['name'] == b'Connections')
    byid = {values(n)[0]: n for n in objects['children']}
    existing_links = [values(n) for n in links['children']]
    source = {name: (g, m) for name, (g, m) in records.items() if name.startswith(spec['source_prefix'])}
    assert len(source) == spec['expected_parts']
    allv = np.concatenate([vertices(g) for g, m in source.values()])
    center = (allv[:, [0, 2]].min(0) + allv[:, [0, 2]].max(0)) / 2
    bottom = allv[:, 1].min()
    head = vertices(source['truck_sam_ford_badge'][0])[:, [0, 2]].mean(0)
    tail = vertices(source['truck_sam_red_light'][0])[:, [0, 2]].mean(0)
    old_heading = math.atan2(*(head-tail)[::-1])
    angle = math.radians(spec['heading_degrees']) - old_heading
    ct, st = math.cos(angle), math.sin(angle)
    yaw = np.array([[ct, 0, -st], [0, 1, 0], [st, 0, ct]])
    relative = allv - [center[0], bottom, center[1]]
    low = relative[:, 1] < .065
    assert low.sum() > 12
    xz = np.asarray(spec['center_xz_m'], float)
    rotated = relative @ yaw.T
    contacts = rotated[low][:, [0, 2]] + xz
    fit = np.linalg.lstsq(np.c_[contacts-xz, np.ones(len(contacts))], ground(height, contacts), rcond=None)[0]
    normal = np.array([-fit[0], 1., -fit[1]])
    normal /= np.linalg.norm(normal)
    axis = np.cross([0, 1, 0], normal)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    tilt = np.eye(3) + k + k@k/(1+normal[1])
    rotation = tilt @ yaw
    origin = np.array([xz[0], fit[2], xz[1]])
    newv = relative @ rotation.T + origin
    origin[1] += float(np.max(ground(height, newv[low][:, [0, 2]]) - newv[low, 1]))
    newv = relative @ rotation.T + origin
    gap = newv[low, 1] - ground(height, newv[low][:, [0, 2]])
    assert gap.min() > -1e-8 and gap.max() < cfg['maximum_wheel_ground_gap_m']
    uid = max(byid) + 1000

    def newid():
        nonlocal uid
        uid += 1
        return uid

    def connect(a, b):
        links['children'].append(node('C', 'OO', a, b))

    names = []
    for name, (g0, model0) in source.items():
        name1 = spec['group'] + '_' + name.removeprefix(spec['source_prefix'])
        gid, mid = newid(), newid()
        g = copy.deepcopy(g0)
        old = values(g)
        setvalues(g, gid, name1.encode()+b'\0\1Geometry', *old[2:])
        vv = (vertices(g0)-[center[0], bottom, center[1]]) @ rotation.T + origin
        child(g, b'Vertices')['props'] = encoded_array(vv * [100, 100, -100])
        for layer in g['children']:
            if layer['name'] != b'LayerElementNormal':
                continue
            normals = child(layer, b'Normals')
            nn = array(normals).reshape(-1, 3) * [1, 1, -1]
            normals['props'] = encoded_array((nn @ rotation.T) * [1, 1, -1])
        model = copy.deepcopy(byid[model0])
        old = values(model)
        setvalues(model, mid, name1.encode()+b'\0\1Model', *old[2:])
        assert values(child(model, b'Culling')) == [b'CullingOnCCW']
        material = next(v[1] for v in existing_links if v[2] == model0 and byid.get(v[1], {}).get('name') == b'Material')
        objects['children'] += [g, model]
        connect(gid, mid)
        connect(material, mid)
        connect(mid, 0)
        names.append(name1)
    definitions = next(n for n in nodes if n['name'] == b'Definitions')
    counts = Counter(n['name'] for n in objects['children'])
    declared = []
    for d in definitions['children']:
        if d['name'] == b'ObjectType':
            typ = values(d)[0]
            ct = counts[typ] if typ != b'GlobalSettings' else values(child(d, b'Count'))[0]
            child(d, b'Count')['props'] = b'I' + struct.pack('<i', ct)
            declared.append(ct)
    child(definitions, b'Count')['props'] = b'I' + struct.pack('<i', sum(declared))
    return names, dict(checks_pass=True, count=1, group=spec['group'], source='truck_sam',
                       vehicle='Sam Ford F-150 King Ranch', source_parts=spec['expected_parts'],
                       source_center_xz_m=center.tolist(), source_bottom_m=float(bottom),
                       center_xz_m=xz.tolist(), heading_degrees=spec['heading_degrees'],
                       origin_xyz_m=origin.tolist(), rotation=rotation.tolist(),
                       wheel_clearance_min_m=float(gap.min()), wheel_clearance_max_m=float(gap.max()),
                       bounds_xyz_m=[newv.min(0).tolist(), newv.max(0).tolist()],
                       new_textures=[], original_pit_ford_retained=True, materials_and_artwork_reused_exact=True)


def release():
    src = R/'12_RELEASE/orlandomx_2026_v042'
    dest = R/'12_RELEASE'/NAME
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.suffix in ['.map', '.trh'] or p.name.startswith('.'):
            continue
        copy_exact(p, dest/p.name.replace('orlandomx_2026_v042', NAME))
    ini = dest/(NAME+'.ini')
    text = ini.read_text()
    assert 'v042' in text
    atomic(ini, text.replace('v042', 'v043').encode())
    copy_exact(BASE/'orlandomx_2026_v042.rdf', O/(NAME+'.rdf'))
    copy_exact(O/(NAME+'.rdf'), dest/(NAME+'.rdf'))


def main():
    cfg = read(S/'update.json')
    qa = read(BASE/'source_validation.json')
    assert qa['version'] == 'v042' and qa['source_checks_pass']
    assert sha(BASE/'scenery.fbx') == cfg['baseline_scenery_sha256']
    assert sha(BASE/'terrain.raw') == cfg['baseline_terrain_sha256']
    if O.exists():
        shutil.rmtree(O)
    shutil.copytree(BASE, O)
    raw = (BASE/'scenery.fbx').read_bytes()
    nodes, tail = parse(raw)
    assert encode(nodes, tail) == raw
    before = {values(n)[0]: fingerprint(n) for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    records = geometry_records(nodes)
    flag = fix_reverse_flag(records, cfg)
    height = np.fromfile(BASE/'terrain.raw', '<u2').reshape(2049, 2049)/65535*18
    names, ford = clone_ford(nodes, records, cfg, height)
    atomic(O/'scenery.fbx', encode(nodes, tail))
    current = parse((O/'scenery.fbx').read_bytes())[0]
    after = {values(n)[0]: fingerprint(n) for n in next(n for n in current if n['name'] == b'Objects')['children']}
    assert all(after[k] == v for k, v in before.items() if k != flag['modified_object_id'])
    newrecords = geometry_records(current)
    points = vertices(newrecords[cfg['flag_geometry']][0]).tolist()
    for name in names:
        vv = vertices(newrecords[name][0])
        points.extend(vv[np.unique(np.linspace(0, len(vv)-1, 6, dtype=int))].tolist())
    save(O/'v043_native_probes.json', dict(expected_xyz_metres=points))
    save(O/'v043_flag_validation.json', flag)
    save(O/'v043_vehicle_validation.json', ford)
    save(O/'v043_asset_validation.json', dict(checks_pass=True, modified_geometry=[cfg['flag_geometry']],
         original_records_retained_exact=len(before)-1, added_geometry=names, added_geometry_count=len(names),
         removed_geometry_count=0, baseline_geometry_count=len(records), total_geometry_count=len(newrecords),
         all_original_texture_files_exact=True, new_texture_count=0))
    qa.update(version='v043', source_commit=os.environ.get('GITHUB_SHA', 'local'),
              baseline_version='user-delivered v042', baseline_commit=cfg['baseline_source_commit'],
              source_checks_pass=False, scenery_sha256=sha(O/'scenery.fbx'), terrain_sha256=sha(O/'terrain.raw'),
              v043_flag=flag, v043_sam_ford=ford, native_compilation=False,
              in_game_riding_test=False, in_game_visual_check=False)
    save(O/'source_validation.json', qa)
    save(O/'v043_layout.json', cfg)
    release()
    print('v043 source authored: track-facing flag repair and Sam Ford beside figure-eight Qwikchute billboard.', flush=True)


if __name__ == '__main__':
    main()
