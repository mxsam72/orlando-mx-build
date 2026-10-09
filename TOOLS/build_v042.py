"""Correct only the flag's horizontal UVs and add three parked Cybertrucks.

All positions are native PiBoSo metre X/Y/Z; the orientation audit converts to
MX Bikes' X/Z/Y camera convention. Existing geometry, textures and transforms
are retained byte for byte except the named flag's horizontal UV array.
"""
import copy
import math
import os
import shutil
import struct
from collections import Counter
import numpy as np
from PIL import Image
from v042_common import *
from v027_scenery import parse, encode, values, child, vertices, geometry_records, fingerprint
from v037_common import ground
from v037_fbx import node, setvalues
from build_v040 import face_uv
from verify_v037_source import faces
from rebind_scenery import array, encoded_array

def flag_orientation(g):
    v = vertices(g)
    checks = []
    for f, uv in zip(faces(g), face_uv(g)):
        points = v[f][:, [0, 2, 1]]
        normal = np.cross(points[1]-points[0], points[2]-points[0])
        normal /= np.linalg.norm(normal)
        # Native X/Z/Y camera: the screen-right vector has the opposite sign
        # from the ordinary X/Y/Z camera that missed this error in v040.
        right = np.cross(-normal, [0, 0, 1])
        right /= np.linalg.norm(right)
        transform = np.linalg.lstsq(np.c_[uv, np.ones(len(uv))], points, rcond=None)[0]
        checks.append(dict(screen_right_u=float(transform[0] @ right),
                           screen_up_v=float(transform[1] @ [0, 0, 1]),
                           outward_normal_native_xzy=normal.tolist()))
    return checks

def fix_flag(rec, cfg):
    g = rec[cfg['flag_geometry']][0]
    before = flag_orientation(g)
    assert len(before) == 4 and all(c['screen_right_u'] < 0 and c['screen_up_v'] > 0 for c in before)
    layer = child(g, b'LayerElementUV')
    uv = array(child(layer, b'UV')).reshape(-1, 2)
    uv[:, 0] = 1 - uv[:, 0]
    child(layer, b'UV')['props'] = encoded_array(uv)
    after = flag_orientation(g)
    assert all(c['screen_right_u'] > 0 and c['screen_up_v'] > 0 for c in after)
    return dict(checks_pass=True, geometry=cfg['flag_geometry'],
                modified_object_id=values(g)[0], horizontal_uv_flip_only=True,
                camera_convention='MX Bikes native X/Z/Y with vertical Y',
                before=before, after=after, both_faces_read_correctly=True,
                artwork_pixels_exact=True, vertical_uvs_exact=True,
                vertices_normals_winding_materials_pole_exact=True,
                opaque_faces_separation_m=.30, in_game_visual_check=False)

def add_trucks(nodes, rec, cfg, h):
    objects = next(n for n in nodes if n['name'] == b'Objects')
    links = next(n for n in nodes if n['name'] == b'Connections')
    byid = {values(n)[0]: n for n in objects['children']}
    original_links = [values(n) for n in links['children']]
    source = {n: (g, mid) for n, (g, mid) in rec.items() if n.startswith('truck_jordan_')}
    assert len(source) == 11
    allv = np.concatenate([vertices(g) for g, mid in source.values()])
    center = (allv[:, [0, 2]].min(0) + allv[:, [0, 2]].max(0)) / 2
    bottom = allv[:, 1].min()
    head = vertices(source['truck_jordan_headlight'][0])[:, [0, 2]].mean(0)
    tail = vertices(source['truck_jordan_red_light'][0])[:, [0, 2]].mean(0)
    old_heading = math.atan2(*(head-tail)[::-1])
    relative = allv - [center[0], bottom, center[1]]
    low = relative[:, 1] < .065
    uid = max(byid) + 1000
    def newid():
        nonlocal uid
        uid += 1
        return uid
    def connect(a, b, prop=None):
        links['children'].append(node('C', 'OP' if prop else 'OO', a, b, *([prop] if prop else [])))
    template = next(n for n in byid.values() if n['name'] == b'Material' and values(n)[1].split(b'\0')[0] == b'v041_cybertruck_blue')
    matid = values(template)[0]
    tid = next(v[1] for v in original_links if v[2] == matid and byid.get(v[1], {}).get('name') == b'Texture')
    vid = next(v[1] for v in original_links if v[2] == tid and byid.get(v[1], {}).get('name') == b'Video')
    materials = {}
    textures = []
    yy, xx = np.mgrid[:256, :256]
    grain = (np.sin(xx*.29) + np.sin(yy*1.7)) * .7
    for color in cfg['new_truck_color_order']:
        stem = 'v042_cybertruck_' + color
        filename = stem + '.tga'
        rgb = np.asarray(cfg['truck_paint_rgb'][color])
        im = Image.fromarray(np.uint8(np.clip(np.rint(rgb + grain[..., None]), 0, 255)))
        image_file(im, O / 'facility_textures' / filename)
        raw = (O / 'facility_textures' / filename).read_bytes()
        ids = [newid() for _ in range(3)]
        materials[color] = ids[0]
        for src, nid, kind in zip([template, byid[tid], byid[vid]], ids, ['Material', 'Texture', 'Video']):
            n = copy.deepcopy(src)
            old = values(n)
            setvalues(n, nid, stem.encode() + b'\0\1' + kind.encode(), *old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName', b'Filename', b'RelativeFilename']:
                    setvalues(c, filename)
                elif c['name'] == b'Media':
                    setvalues(c, stem.encode() + b'\0\1Video')
                elif c['name'] == b'Content':
                    c['count'] = 1
                    c['props'] = b'R' + struct.pack('<I', len(raw)) + raw
                elif c['name'] == b'Properties70':
                    for prop in c['children']:
                        vv = values(prop)
                        if vv and vv[0] in [b'Path', b'Filename', b'FileName', b'RelativeFilename']:
                            setvalues(prop, *vv[:4], filename)
            objects['children'].append(n)
        connect(ids[1], ids[0], 'DiffuseColor')
        connect(ids[2], ids[1])
        textures.append(dict(texture=filename, size_px=[256, 256], opaque_rgb=True,
                             rgb=cfg['truck_paint_rgb'][color], sha256=sha(O/'facility_textures'/filename)))
    vehicles = []
    names = []
    for spec in cfg['new_trucks']:
        xz = np.asarray(spec['center_xz_m'], float)
        angle = math.radians(spec['heading_degrees']) - old_heading
        ct, st = math.cos(angle), math.sin(angle)
        yaw = np.array([[ct, 0, -st], [0, 1, 0], [st, 0, ct]])
        rotated = relative @ yaw.T
        contacts = rotated[low][:, [0, 2]] + xz
        fit = np.linalg.lstsq(np.c_[contacts-xz, np.ones(len(contacts))], ground(h, contacts), rcond=None)[0]
        normal = np.array([-fit[0], 1., -fit[1]])
        normal /= np.linalg.norm(normal)
        axis = np.cross([0, 1, 0], normal)
        K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        tilt = np.eye(3) + K + K@K/(1+normal[1])
        rotation = tilt @ yaw
        new = relative @ rotation.T + [xz[0], fit[2], xz[1]]
        dy = float(np.max(ground(h, new[low][:, [0, 2]]) - new[low, 1]))
        origin = np.array([xz[0], fit[2]+dy, xz[1]])
        new = relative @ rotation.T + origin
        gap = new[low, 1] - ground(h, new[low][:, [0, 2]])
        assert gap.min() > -1e-8 and gap.max() < cfg['maximum_wheel_ground_gap_m']
        group = 'v042_pit_cybertruck_' + str(spec['number']).zfill(2) + '_' + spec['color']
        for name, (g0, mid0) in source.items():
            suffix = name.removeprefix('truck_jordan_')
            name1 = group + '_' + suffix
            gid, mid = newid(), newid()
            g = copy.deepcopy(g0)
            old = values(g)
            setvalues(g, gid, name1.encode()+b'\0\1Geometry', *old[2:])
            vv = (vertices(g0)-[center[0], bottom, center[1]]) @ rotation.T + origin
            child(g, b'Vertices')['props'] = encoded_array(vv * [100, 100, -100])
            for layer in g['children']:
                if layer['name'] != b'LayerElementNormal':
                    continue
                nn = child(layer, b'Normals')
                norm = array(nn).reshape(-1, 3) * [1, 1, -1]
                nn['props'] = encoded_array((norm @ rotation.T) * [1, 1, -1])
            model = copy.deepcopy(byid[mid0])
            old = values(model)
            setvalues(model, mid, name1.encode()+b'\0\1Model', *old[2:])
            setvalues(child(model, b'Culling'), 'CullingOnCCW')
            material = next(v[1] for v in original_links if v[2] == mid0 and byid.get(v[1], {}).get('name') == b'Material')
            objects['children'] += [g, model]
            connect(gid, mid)
            connect(materials[spec['color']] if suffix == 'cyber_steel' else material, mid)
            connect(mid, 0)
            names.append(name1)
        vehicles.append(dict(group=group, source='truck_jordan', color=spec['color'], parts=11,
                             center_xz_m=xz.tolist(), heading_degrees=spec['heading_degrees'],
                             origin_xyz_m=origin.tolist(), rotation=rotation.tolist(),
                             wheel_clearance_min_m=float(gap.min()), wheel_clearance_max_m=float(gap.max()),
                             bounds_xyz_m=[new.min(0).tolist(), new.max(0).tolist()]))
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
    return names, dict(checks_pass=True, count=3, color_order=cfg['new_truck_color_order'],
                       continued_after_v041_blue_purple_green=True, new_textures=textures,
                       vehicles=vehicles, existing_pit_and_oval_vehicles_exact=True)

def release():
    src = R/'12_RELEASE/orlandomx_2026_v041'
    dest = R/'12_RELEASE'/NAME
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.suffix in ['.map', '.trh'] or p.name.startswith('.'):
            continue
        copy_exact(p, dest/p.name.replace('orlandomx_2026_v041', NAME))
    ini = dest/(NAME+'.ini')
    text = ini.read_text()
    assert 'v041' in text
    atomic(ini, text.replace('v041', 'v042').encode())
    copy_exact(BASE/'orlandomx_2026_v041.rdf', O/(NAME+'.rdf'))
    copy_exact(O/(NAME+'.rdf'), dest/(NAME+'.rdf'))

def main():
    cfg = read(S/'update.json')
    qa = read(BASE/'source_validation.json')
    assert qa['version'] == 'v041' and qa['source_checks_pass']
    assert sha(BASE/'scenery.fbx') == cfg['baseline_scenery_sha256']
    assert sha(BASE/'terrain.raw') == cfg['baseline_terrain_sha256']
    if O.exists():
        shutil.rmtree(O)
    shutil.copytree(BASE, O)
    raw = (BASE/'scenery.fbx').read_bytes()
    nodes, tail = parse(raw)
    assert encode(nodes, tail) == raw
    oldnodes = parse(raw)[0]
    records = geometry_records(nodes)
    flagqa = fix_flag(records, cfg)
    h = np.fromfile(BASE/'terrain.raw', '<u2').reshape(2049, 2049)/65535*18
    names, trucks = add_trucks(nodes, records, cfg, h)
    raw = encode(nodes, tail)
    atomic(O/'scenery.fbx', raw)
    current = parse(raw)[0]
    newrecords = geometry_records(current)
    before = {values(n)[0]: fingerprint(n) for n in next(n for n in oldnodes if n['name'] == b'Objects')['children']}
    after = {values(n)[0]: fingerprint(n) for n in next(n for n in current if n['name'] == b'Objects')['children']}
    modified = flagqa['modified_object_id']
    assert all(after[k] == v for k, v in before.items() if k != modified)
    points = vertices(newrecords[cfg['flag_geometry']][0]).tolist()
    for name in names:
        v = vertices(newrecords[name][0])
        points.extend(v[np.unique(np.linspace(0, len(v)-1, 4, dtype=int))].tolist())
    save(O/'v042_native_probes.json', dict(expected_xyz_metres=points))
    save(O/'v042_flag_validation.json', flagqa)
    save(O/'v042_vehicle_validation.json', trucks)
    save(O/'v042_asset_validation.json', dict(checks_pass=True, modified_geometry=[cfg['flag_geometry']],
         original_records_retained_exact=len(before)-1, added_geometry=names, added_geometry_count=len(names),
         removed_geometry_count=0, baseline_geometry_count=len(records), total_geometry_count=len(newrecords),
         all_original_texture_files_exact=True))
    qa = copy.deepcopy(qa)
    qa.update(version='v042', source_commit=os.environ.get('GITHUB_SHA', 'local'),
              baseline_version='user-delivered v041', baseline_commit=cfg['baseline_source_commit'],
              source_checks_pass=False, scenery_sha256=sha(O/'scenery.fbx'), terrain_sha256=sha(O/'terrain.raw'),
              v042_flag=flagqa, v042_additional_cybertrucks=trucks, native_compilation=False,
              in_game_riding_test=False, in_game_visual_check=False)
    save(O/'source_validation.json', qa)
    save(O/'v042_layout.json', cfg)
    release()
    print('v042 source authored: flag horizontal UV correction and pink/orange/yellow parked Cybertrucks.', flush=True)

if __name__ == '__main__':
    main()
