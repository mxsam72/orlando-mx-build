"""Protect normal-header parsing and reject incorrect roles/digests/bounds."""
import struct,tempfile,unittest
from pathlib import Path
from PIL import Image
from validate_native_textures_v024 import bitmap_signature,texture_record

class NormalRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'pine_bark_n.tga'
        Image.new('RGBA',(2,2),(112,140,250,2)).save(self.path)
        w,h,d=bitmap_signature(self.path);name=self.path.stem.encode()
        self.prefix=name+bytes(100-len(name));self.dimensions=struct.pack('<2I',w,h);self.digest=d
        # Normal headers observed in the saved official EDF omit the diffuse
        # flag before dimensions; their payload begins at byte 140.
        self.raw=self.prefix+self.dimensions+d+struct.pack('<4I',0,9,0,0)+b'123456789'
    def tearDown(self):self.tmp.cleanup()
    def test_exact_normal_record(self):
        q=texture_record(self.raw,self.path,normal_map=True)
        self.assertEqual(q['native_header_bytes'],140);self.assertEqual(q['payload_bytes'],9)
        self.assertEqual(q['native_record_kind'],'normal_map')
    def test_normal_requires_explicit_role(self):
        with self.assertRaises(RuntimeError):texture_record(self.raw,self.path)
    def test_pixel_digest_required(self):
        raw=bytearray(self.raw);raw[108]^=1
        with self.assertRaises(RuntimeError):texture_record(raw,self.path,normal_map=True)
    def test_payload_bounds_required(self):
        with self.assertRaises(RuntimeError):texture_record(self.raw[:-1],self.path,normal_map=True)
    def test_dimensions_required(self):
        raw=bytearray(self.raw);struct.pack_into('<I',raw,100,4)
        with self.assertRaises(RuntimeError):texture_record(raw,self.path,normal_map=True)

if __name__=='__main__':unittest.main()
