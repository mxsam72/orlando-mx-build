"""Controls using the real captured exporter packet, including corruption cases."""
import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from native_specular_v052 import specular_records
NAME=b'v052_foliage_specular'
# First 142 bytes of the actual named record in native probe run 38536643719.
FIXTURE=NAME+bytes(100-len(NAME))+bytes.fromhex('1000000010000000348a9791dc41b89796ec3808b5b5262f0e0000000200000000000000636018d90000')
class TestNativeSpecular(unittest.TestCase):
 def setUp(self):
  self.dir=tempfile.TemporaryDirectory();self.path=Path(self.dir.name)/'v052_foliage_specular.tga'
  self.rgba=np.zeros((16,16,4),np.uint8);self.rgba[:,:,:3]=[127,127,255];Image.fromarray(self.rgba).save(self.path)
 def tearDown(self):self.dir.cleanup()
 def test_real_exported_alpha_decodes_exactly(self):
  q=specular_records(FIXTURE,self.path);r=q['records'][0]
  self.assertEqual(r['decoded_alpha_bytes'],256);self.assertEqual(r['decoded_alpha_max'],0)
 def test_colour_is_not_the_specular_intensity(self):
  self.rgba[:,:,:3]=[1,230,64];Image.fromarray(self.rgba).save(self.path)
  self.assertTrue(specular_records(FIXTURE,self.path)['checks_pass'])
 def test_nonzero_source_alpha_rejected(self):
  self.rgba[:,:,3]=2;Image.fromarray(self.rgba).save(self.path)
  with self.assertRaises(RuntimeError):specular_records(FIXTURE,self.path)
 def test_corrupt_packet_rejected(self):
  raw=bytearray(FIXTURE);raw[138]^=0x55
  with self.assertRaises(Exception):specular_records(raw,self.path)
 def test_truncated_packet_rejected(self):
  with self.assertRaises(RuntimeError):specular_records(FIXTURE[:-1],self.path)
if __name__=='__main__':unittest.main()
