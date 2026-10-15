"""Decode and compare complete native MAP/TRH height fields, not source claims.

Formats calibrated against every 2049x2049 sample in delivered v054 and v055.
TRH stores bias-32768 unsigned heights in flipped row order; MAP stores the
unbiased flipped RAW after two little-endian dimensions. All bytes are checked.
"""
import mmap
import struct
import numpy as np
from v057_inputs import PREV, O, save, sha
from v056_geometry import corner_checks


def collision_heights(path):
    with open(path, 'rb') as stream:
        assert stream.read(4) == b'TRH\0'
        assert struct.unpack('<2I', stream.read(8)) == (2049,2049)
    encoded = np.memmap(path, mode='r', dtype='<u2', offset=12, shape=(2049,2049))
    return ((encoded.astype(np.uint32)-32768)&65535).astype('<u2')[::-1].copy()


def map_heights(path, expected):
    flipped = np.ascontiguousarray(expected[::-1]).tobytes()
    prefix = struct.pack('<2I',2049,2049)+flipped[:512]
    with open(path,'rb') as stream, mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
        assert data[:4] == b'MP2\0'
        start = 0
        while True:
            pos = data.find(prefix, start)
            assert pos >= 0, 'MAP does not contain the exact source ground grid'
            offset = pos+8
            if data[offset:offset+len(flipped)] == flipped:
                break
            start = pos+1
        decoded = np.frombuffer(data[offset:offset+len(flipped)],'<u2').reshape(2049,2049)[::-1].copy()
    return decoded, offset


def validate_native_heights(map_path, trh_path):
    expected = np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)
    baseline = np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049)
    assert np.array_equal(expected,baseline), 'v057 source ground changed from tested v056'
    collision = collision_heights(trh_path)
    visual, offset = map_heights(map_path, expected)
    assert np.array_equal(collision,expected), 'Native collision differs from source terrain'
    assert np.array_equal(visual,expected), 'Native visual ground differs from source terrain'
    route = dict(np.load(PREV/'route.npz'))
    _, corners = corner_checks(baseline,collision,route['q'],route['v054_old_station'])
    assert len(corners)==14 and all(t['raw_grid_exact'] and t['max_height_difference_m']==0 for t in corners)
    report = dict(checks_pass=True, native_MAP_entire_grid_exact_source=True,
        native_TRH_entire_grid_exact_source=True, native_visual_collision_grids_exact=True,
        samples_checked_per_grid=int(expected.size), map_grid_offset=offset,
        native_all_14_corner_grids_exact_v054=True, entire_native_visual_and_collision_ground_exact_v056=True, corners=corners,
        samples_differ_from_v056=int(np.count_nonzero(collision!=baseline)),
        source_raw_sha256=sha(O/'terrain.raw'), map_sha256=sha(map_path), trh_sha256=sha(trh_path))
    save(O/'native_height_validation.json',report)
    return report
