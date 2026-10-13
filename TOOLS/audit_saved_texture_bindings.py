"""Inspect real source material use and embedded bitmap pixels without compiling."""
import base64, hashlib, io, json
from collections import Counter, defaultdict
from PIL import Image
from v044_common import R, O, save
from v044_source import api, blob
from inspect_native_bitmap_records import restore_source
from v027_scenery import parse, values
from rebind_scenery import array
from scene_texture_bindings_v044 import filename_fields

def main():
    restore_source()
    nodes = parse((O / 'scenery.fbx').read_bytes())[0]
    objects = {values(n)[0]: n for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    links = [values(n) for n in next(n for n in nodes if n['name'] == b'Connections')['children']]
    model_materials = defaultdict(list)
    for link in links:
        if objects.get(link[1], {}).get('name') == b'Material' and objects.get(link[2], {}).get('name') == b'Model':
            model_materials[link[2]].append(link[1])
    used_faces = Counter()
    material_model_samples = defaultdict(list)
    mappings = Counter()
    anomalies = []
    for geometry_id, geometry in objects.items():
        if geometry['name'] != b'Geometry':
            continue
        layers = [n for n in geometry['children'] if n['name'] == b'LayerElementMaterial']
        polygons = next((n for n in geometry['children'] if n['name'] == b'PolygonVertexIndex'), None)
        if polygons is None:
            continue
        face_count = int((array(polygons) < 0).sum())
        if layers:
            layer = layers[0]
            info = {c['name']: values(c)[0] for c in layer['children'] if c['name'] in [b'MappingInformationType', b'ReferenceInformationType']}
            data = next((c for c in layer['children'] if c['name'] == b'Materials'), None)
            indices = array(data).astype(int) if data is not None else [0]
            mapping = info.get(b'MappingInformationType', b'Unknown')
            mappings[mapping.decode()] += 1
            counts = Counter(map(int, indices))
            if mapping == b'AllSame' and len(indices) == 1:
                counts = Counter({int(indices[0]): face_count})
            elif mapping != b'ByPolygon':
                anomalies.append(dict(geometry_id=geometry_id, mapping=str(mapping), material_index_count=len(indices), polygon_count=face_count))
        else:
            counts = Counter({0: face_count})
            mappings['No material layer; default slot 0'] += 1
        models = [link[2] for link in links if link[1] == geometry_id and objects.get(link[2], {}).get('name') == b'Model']
        for model in models:
            materials = model_materials[model]
            for index, count in counts.items():
                if not (0 <= index < len(materials)):
                    anomalies.append(dict(geometry_id=geometry_id, model=model, index=index, materials=materials))
                    continue
                material = materials[index]
                used_faces[material] += count
                if len(material_model_samples[material]) < 4:
                    material_model_samples[material].append(values(objects[model])[1].split(b'\0')[0].decode())
    diagnostics_blob = api('/git/blobs/04750d6a883b018beb92b24debce38812ba25661')
    diagnostics = json.loads(base64.b64decode(diagnostics_blob['content']))
    native = {r['texture']: r for r in diagnostics['textures']}
    records = []
    for texture_id, texture in objects.items():
        if texture['name'] != b'Texture':
            continue
        fields = filename_fields(texture)
        names = set(fields.values())
        if not names.intersection(native):
            continue
        related = [link for link in links if link[1] == texture_id and objects.get(link[2], {}).get('name') == b'Material']
        if not any(link[2] in model_materials[model] for model in model_materials for link in related):
            continue
        video_rows = []
        for link in links:
            if link[2] != texture_id or objects.get(link[1], {}).get('name') != b'Video':
                continue
            video = objects[link[1]]
            contents = [values(n)[0] for n in video['children'] if n['name'] == b'Content']
            row = dict(video_id=link[1], filename_fields=filename_fields(video))
            if contents:
                content = contents[0]
                row['content_sha256'] = hashlib.sha256(content).hexdigest()
                try:
                    with Image.open(io.BytesIO(content)) as image:
                        rgba = image.convert('RGBA')
                        row['size'] = list(rgba.size)
                        row['pixel_md5'] = hashlib.md5(rgba.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()).hexdigest()
                except Exception as error:
                    row['content_decode_error'] = str(error)
            video_rows.append(row)
        row = dict(texture_id=texture_id, texture_fields=fields,
                   native_diagnostics={name: dict(edf_signature_offset=native[name]['edf_signature_offset'], map_signature_offset=native[name]['map_signature_offset'], source_pixel_md5=native[name]['pixel_md5']) for name in names if name in native},
                   material_links=[dict(type=link[0].decode(), property=link[3].decode() if len(link)>3 else None,
                                        material_id=link[2], material_name=values(objects[link[2]])[1].split(b'\0')[0].decode(),
                                        assigned_polygons=used_faces[link[2]], model_samples=material_model_samples[link[2]]) for link in related],
                   embedded_videos=video_rows)
        records.append(row)
        print('SOURCE_BITMAP_BINDING ' + json.dumps(row), flush=True)
    report = dict(records=records, mapping_counts=dict(mappings), material_mapping_anomalies=anomalies,
                  source_unchanged=True, compiler_invoked=False)
    save(R / 'DOCUMENTATION/v044_material_bitmap_source_audit.json', report)
    print('CODEX_V044_MATERIAL_BITMAP_AUDIT_BLOB ' + blob(json.dumps(report)), flush=True)

if __name__ == '__main__':
    main()
