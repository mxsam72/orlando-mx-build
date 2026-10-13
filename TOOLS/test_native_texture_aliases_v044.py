"""Regression checks for exact-pixel aliases and conflicting FBX source hints."""
import hashlib, json, struct, tempfile, unittest
from pathlib import Path
from PIL import Image
from validate_native_textures_v024 import bitmap_signature, verify_files
from scene_texture_bindings_v044 import actual_diffuse_bindings

def fbx_node(name, *values, children=()):
    properties = b''
    for value in values:
        if isinstance(value, int):
            properties += b'L' + struct.pack('<q', value)
        else:
            data = value if isinstance(value, bytes) else value.encode()
            properties += b'S' + struct.pack('<I', len(data)) + data
    return dict(name=name.encode(), count=len(values), props=properties, children=list(children), sentinel=b'')

def binding_fixture(video_name='v028_bark.tga'):
    objects = [fbx_node('Geometry', 1, 'tree_mesh', 'Mesh'), fbx_node('Model', 2, 'tree', 'Mesh'),
               fbx_node('Material', 3, 'bark', ''),
               fbx_node('Texture', 4, 'bark', '', children=[fbx_node('FileName', 'v028_bark.tga'), fbx_node('RelativeFilename', 'bark.tga')]),
               fbx_node('Video', 5, 'bark', '', children=[fbx_node('Filename', video_name), fbx_node('RelativeFilename', 'bark.tga')])]
    links = [fbx_node('C', 'OO', 1, 2), fbx_node('C', 'OO', 3, 2),
             fbx_node('C', 'OP', 4, 3, 'DiffuseColor'), fbx_node('C', 'OO', 5, 4)]
    return [fbx_node('Objects', children=objects), fbx_node('Connections', children=links)]

class NativeTextureRegression(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original = self.root / 'v028_bark.tga'
        self.alias = self.root / 'v024_bark.tga'
        image = Image.new('RGBA', (4, 4), (112, 65, 21, 255))
        image.putpixel((0, 1), (63, 112, 5, 200))
        image.save(self.original)
        image.save(self.alias)
        w, h, digest = bitmap_signature(self.original)
        self.signature = struct.pack('<2I', w, h) + digest
        payload = b'native-bitmap-payload'
        record = self.original.stem.encode().ljust(100, b'\0') + struct.pack('<I', 0) + self.signature + struct.pack('<4I', 0, len(payload), 0, 0) + payload
        self.edf = self.root / 'scenery.edf'
        self.map = self.root / 'track.map'
        self.edf.write_bytes(b'EDF\0' + record)
        self.map.write_bytes(b'MP' + self.signature)

    def verify(self):
        return verify_files(self.edf, self.map, [self.alias, self.original], self.root / 'report.json')

    def test_identical_bitmap_alias_uses_checked_named_record(self):
        result = self.verify()
        alias = next(row for row in result['textures'] if row['texture'] == self.alias.name)
        self.assertTrue(alias['shared_bitmap_alias'])
        self.assertEqual(alias['native_name'], 'v028_bark')
        self.assertEqual(alias['shared_bitmap_texture'], self.original.name)
        self.assertEqual(result['texture_count'], 2)

    def test_changed_alias_pixels_are_rejected(self):
        Image.new('RGBA', (4, 4), (112, 65, 22, 255)).save(self.alias)
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_missing_map_pixels_are_rejected(self):
        self.map.write_bytes(b'MP' + bytes(24))
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_unbounded_native_payload_is_rejected(self):
        data = bytearray(self.edf.read_bytes())
        struct.pack_into('<I', data, 4 + 132, 999999)
        self.edf.write_bytes(data)
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_independent_media_name_confirms_stale_relative_hint(self):
        result = actual_diffuse_bindings(binding_fixture())
        self.assertEqual(result['actual_diffuse_textures'], ['v028_bark.tga'])
        self.assertEqual(result['obsolete_relative_filename_hints'], ['bark.tga'])

    def test_conflicting_media_name_cannot_silently_drop_texture(self):
        with self.assertRaises(AssertionError):
            actual_diffuse_bindings(binding_fixture('bark.tga'))

    def test_authenticated_legacy_colors_require_edf_and_map_values(self):
        diffuse=[.23,.2,.15];ambient=[.05,.05,.05]
        colors=struct.pack('<6f',*(diffuse*2))
        self.edf.write_bytes(b'EDF\0'+colors)
        self.map.write_bytes(b'MP'+colors)
        legacy={self.original.name:dict(source_sha256=hashlib.sha256(self.original.read_bytes()).hexdigest(),
                constant_pixel_rgba=[112,65,21,255],materials=[dict(diffuse_rgb=diffuse,ambient_rgb=ambient)],official_colour_probe_run=38331283031)}
        result=verify_files(self.edf,self.map,[self.original],self.root/'colors.json',legacy_materials=legacy)
        self.assertEqual(result['legacy_uniform_material_texture_count'],1)
        self.map.write_bytes(b'MP'+struct.pack('<6f',.24,.2,.15,.23,.2,.15))
        with self.assertRaises(RuntimeError):
            verify_files(self.edf,self.map,[self.original],self.root/'colors.json',legacy_materials=legacy)

    def test_changed_legacy_source_is_rejected(self):
        diffuse=[.23,.2,.15];ambient=[.05,.05,.05]
        colors=struct.pack('<6f',*(diffuse*2))
        self.edf.write_bytes(b'EDF\0'+colors);self.map.write_bytes(b'MP'+colors)
        legacy={self.original.name:dict(source_sha256='0'*64,constant_pixel_rgba=[112,65,21,255],
                materials=[dict(diffuse_rgb=diffuse,ambient_rgb=ambient)],official_colour_probe_run=38331283031)}
        with self.assertRaises(AssertionError):
            verify_files(self.edf,self.map,[self.original],self.root/'colors.json',legacy_materials=legacy)

if __name__ == '__main__':
    unittest.main()
