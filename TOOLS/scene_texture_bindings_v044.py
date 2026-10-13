"""Resolve actual FBX diffuse bindings and document stale relative filename hints."""
from pathlib import Path
from v027_scenery import parse, values, geometry_records

def filename_fields(node):
    fields = {}
    for child in node['children']:
        if child['name'] not in [b'FileName', b'Filename', b'RelativeFilename']:
            continue
        value = values(child)[0]
        value = value.decode() if isinstance(value, bytes) else str(value)
        fields[child['name'].decode()] = value.replace('\\', '/').split('/')[-1]
    return fields

def actual_diffuse_bindings(nodes):
    objects = {values(n)[0]: n for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    models = {mid for geometry, mid in geometry_records(nodes).values()}
    links = [values(n) for n in next(n for n in nodes if n['name'] == b'Connections')['children']]
    materials = {v[1] for v in links if v[2] in models and objects.get(v[1], {}).get('name') == b'Material'}
    texture_ids = {v[1] for v in links if v[2] in materials and objects.get(v[1], {}).get('name') == b'Texture'
                   and (v[0] != b'OP' or v[3] == b'DiffuseColor')}
    bindings = []
    for texture_id in sorted(texture_ids):
        fields = filename_fields(objects[texture_id])
        primary = {fields[k] for k in ['FileName', 'Filename'] if fields.get(k)}
        assert len(primary) <= 1, ('Conflicting absolute FBX filename declarations', texture_id, fields)
        name = next(iter(primary)) if primary else fields.get('RelativeFilename')
        assert name and name == Path(name).name, ('Unresolved texture name', texture_id, fields)
        videos = [objects[v[1]] for v in links if v[2] == texture_id and objects.get(v[1], {}).get('name') == b'Video']
        video_fields = [filename_fields(video) for video in videos]
        obsolete = sorted({value for value in fields.values() if value and value != name})
        if obsolete:
            # Do not silently pick among differing hints: connected embedded-media
            # declarations must independently confirm the primary texture file.
            video_primary = [{d[k] for k in ['FileName', 'Filename'] if d.get(k)} for d in video_fields]
            assert videos and all(names == {name} for names in video_primary), ('Conflicting embedded-media filename', texture_id, fields, video_fields)
        bindings.append(dict(texture_id=texture_id, texture=name, texture_fields=fields,
                             embedded_video_fields=video_fields, obsolete_relative_filename_hints=obsolete))
    return dict(checks_pass=True, texture_count=len({b['texture'] for b in bindings}), bindings=bindings,
                actual_diffuse_textures=sorted({b['texture'] for b in bindings}),
                obsolete_relative_filename_hints=sorted({n for b in bindings for n in b['obsolete_relative_filename_hints']}))

def inspect(path):
    return actual_diffuse_bindings(parse(Path(path).read_bytes())[0])
