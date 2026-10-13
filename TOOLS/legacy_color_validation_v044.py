"""Authenticate unchanged legacy uniform-color materials from real source data."""
from pathlib import Path
import hashlib
from PIL import Image
from v027_scenery import parse, values
from scene_texture_bindings_v044 import actual_diffuse_bindings

LEGACY_SOURCE_SHA256 = {
    "bark.tga": "ce352b0779d9a1c3a16a98857fc22fe37f081f972cb41deda8ef7277140ab5a0",
    "foliage_dark.tga": "95eaae0a90608ec90218cee84567712bb7c5b9a74d187c964aa35644919ff1b7",
    "foliage_light.tga": "cf04583738f381d469c87a801b547291da24d27abe09f161df7c5bf8ff1b7877",
    "foliage_mid.tga": "67dde3180576c6bad8292b29dbe280c029242c0916d712fb90489094adf44bdb",
    "marker_white.tga": "d76c04392832d244de66243a25587483da1334ef82aae56e496967d7f833d09d",
    "metal.tga": "a42e4c5e2baecc16ee083c45ce38ca01d13cc28b567851130037d885b58d3091",
    "v024_alloy.tga": "f936251338b1c559708ffa645f788ef558cd278d603c298398e52cde3a727486",
    "v024_glass.tga": "3f0ecae6df9a86a0b5303e7315dd875440ee07808c563cfbe8f52bee5cec5c26",
    "v024_gravel.tga": "3910f3c4f6ef6def6a75161c0ecde3dcfa8c26fb0609516a867e6f4166271ad5",
    "v024_leaf1.tga": "62763e3954a2012567666d0ac8a69c1470685df8b2d84a410a47778d2efffebc",
    "v024_leaf2.tga": "af3b1090ea6354768762ce0297db9b3acac96a0461dce5c25914dc45705959bc",
    "v024_leaf3.tga": "d4c4b2ad4e99cf68a9aea7ba75606c04cca6900ff30e56cbe6ffdc16c9fc6ca4",
    "v024_navy.tga": "69004130f8b185662d4fd22a327e4db088ce54071867148aabc3eab016b4d957",
    "v024_red.tga": "0fece113b6b14a8b3b24226c5e1cd2249df4e505550eb1d001e4440a49885117",
    "v024_roof.tga": "6fd6be96b1b339ad109864ab30c9f080c44c03a714a61c11de82ce58c82b7fa6",
    "v024_rubber.tga": "f336ac3923c04f8bab037cd72cf74a3a68c20c920c175017968afb01276123f9",
    "v024_siding.tga": "3103e835b652798a980ccc0a700efc27f2449131d77a2f2d1cb73a9c1a32b9f0",
    "v024_trim.tga": "57c8d7bb8e0d82998a967bbd6f4a838f1442f81dc188472ba033ed79583ae6d0",
    "water.tga": "1753f92d7d47c43ad13ba5a5d4437f822f8f5ba5fe05114b2cdcbdeed847b9ea"
}

def legacy_materials(scene, textures):
    nodes = parse(Path(scene).read_bytes())[0]
    objects = {values(n)[0]: n for n in next(n for n in nodes if n['name'] == b'Objects')['children']}
    links = [values(n) for n in next(n for n in nodes if n['name'] == b'Connections')['children']]
    bindings = actual_diffuse_bindings(nodes)
    source = {Path(p).name: Path(p) for p in textures}
    result = {}
    for name, expected_sha in LEGACY_SOURCE_SHA256.items():
        if name not in source:
            continue
        path = source[name]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha, ('Legacy bitmap source changed', name)
        with Image.open(path) as image:
            rgba = image.convert('RGBA')
            assert all(lo == hi for lo, hi in rgba.getextrema()), ('Legacy bitmap gained detail', name)
            assert rgba.getpixel((0,0))[3] == 255, ('Legacy bitmap alpha changed', name)
            pixel = list(rgba.getpixel((0,0)))
        material_ids = set()
        for binding in bindings['bindings']:
            if binding['texture'] != name:
                continue
            material_ids.update(link[2] for link in links if link[1] == binding['texture_id'] and objects.get(link[2],{}).get('name') == b'Material'
                                and (link[0] != b'OP' or link[3] == b'DiffuseColor'))
        rows = []
        for material_id in sorted(material_ids):
            material = objects[material_id]
            properties = {values(p)[0]: values(p)[4:] for props in material['children'] if props['name'] == b'Properties70' for p in props['children']}
            diffuse = list(map(float, properties[b'DiffuseColor']))
            ambient = list(map(float, properties[b'AmbientColor']))
            assert len(diffuse) == len(ambient) == 3
            rows.append(dict(material_id=material_id, material_name=values(material)[1].split(b'\0')[0].decode(), diffuse_rgb=diffuse, ambient_rgb=ambient))
        assert rows, ('Legacy material assignment missing', name)
        result[name] = dict(source_sha256=expected_sha, constant_pixel_rgba=pixel, materials=rows,
                            source_image_constant=True, original_legacy_source_authenticated=True,
                            official_colour_probe_run=38331283031)
    return result
