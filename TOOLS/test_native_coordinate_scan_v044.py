"""Check native vertex scan behavior against the existing validated probe."""
import struct, unittest
import numpy as np
from build_windows_v037 import probe
from native_coordinate_scan_v044 import scan_points

class CoordinateScanRegression(unittest.TestCase):
    def test_exact_rounded_missing_negative_and_boundary_vertices(self):
        raw=bytearray(np.random.default_rng(440044).integers(0,256,100003,dtype=np.uint8).tobytes())
        points=[[100.125,2.75,200.875],[300.25,1.0,400.5],[250.3234,1.5,450.125],[555.5,2.0,123.0],[-2.0,3.0,4.0]]
        for point,offset in zip(points[:2],[31,1001]):raw[offset:offset+12]=struct.pack('<3f',*point)
        near=points[2].copy();near[0]=float(np.nextafter(np.float32(near[0]),np.float32(np.inf)))
        raw[12302:12314]=struct.pack('<3f',*near);raw[173:185]=struct.pack('<3f',*points[-1])
        expected=[probe(raw,point) for point in points]
        actual=scan_points(raw,points,chunk_words=32)
        self.assertEqual([e is not None for e in expected],[e is not None for e in actual])
        self.assertTrue(all(e is None or e<.0001 for e in actual))
        self.assertEqual(actual[:2],[0.,0.]);self.assertIsNone(actual[3]);self.assertEqual(actual[-1],0.)

    def test_changed_vertex_outside_tolerance_is_rejected(self):
        point=[140.1,2.,250.]
        raw=b'padding'+struct.pack('<3f',140.1,2.001,250.)+bytes(40)
        self.assertIsNone(scan_points(raw,[point],chunk_words=8)[0])

    def test_all_byte_alignments_and_duplicate_points(self):
        point=[120.125,3.25,280.5]
        for offset in range(4):
            raw=bytes(offset)+struct.pack('<3f',*point)+bytes(80)
            self.assertEqual(scan_points(raw,[point,point],chunk_words=8),[0.,0.])

if __name__=='__main__':unittest.main()
