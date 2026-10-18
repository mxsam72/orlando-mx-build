"""Signed-coordinate regressions for the native lunar scenery checks."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'TOOLS'))
from native_coordinate_scan_v044 import scan_points


class SignedCoordinateTests(unittest.TestCase):
    def test_negative_roundoff_at_every_byte_alignment(self):
        point = [-521.1099853515625, 53.940086364746094, -460.093017578125]
        actual = [point[0] - .00006, point[1] + .00003, point[2] - .00003]
        for alignment in range(4):
            with self.subTest(alignment=alignment):
                raw = bytes(alignment) + struct.pack('<3f', *actual) + bytes(40)
                error = scan_points(raw, [point], tolerance=.001)[0]
                self.assertIsNotNone(error)
                self.assertLess(error, .001)

    def test_near_zero_roundoff(self):
        for x in [-.00001, 0., .00001]:
            point = [x, 2., 3.]
            raw = b'pad' + struct.pack('<3f', x + .00002, 2., 3.) + bytes(40)
            self.assertIsNotNone(scan_points(raw, [point], tolerance=.001)[0])

    def test_negative_changed_geometry_is_still_rejected(self):
        point = [-521.11, 53.94, -460.093]
        for axis in range(3):
            changed = point.copy()
            changed[axis] += .01
            raw = b'pad' + struct.pack('<3f', *changed) + bytes(40)
            self.assertIsNone(scan_points(raw, [point], tolerance=.001)[0])
