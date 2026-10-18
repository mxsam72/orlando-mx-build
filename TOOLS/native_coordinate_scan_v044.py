"""Check every byte alignment for required native vertices in one bounded scan."""
import struct, time
import numpy as np
def probe(raw, point, tolerance=.0001):
    """Find signed float triples; negative IEEE-754 bit order runs backwards."""
    point = tuple(map(float, point))
    if raw.find(struct.pack('<3f', *point)) >= 0:
        return 0.
    bounds = [struct.unpack('<I', struct.pack('<f', point[0] + delta))[0]
              for delta in (-tolerance, tolerance)]
    lo, hi = sorted(bounds)
    if hi - lo <= 65536:
        for bits in range(lo, hi + 1):
            needle = struct.pack('<I', bits)
            offset = raw.find(needle)
            while offset >= 0 and offset + 12 <= len(raw):
                got = struct.unpack_from('<3f', raw, offset)
                if all(np.isfinite(got)):
                    error = max(abs(a-b) for a, b in zip(point, got))
                    if error < tolerance:
                        return error
                offset = raw.find(needle, offset + 1)
        return None
    # A tolerance interval crossing zero has distant unsigned endpoints.
    # Scan bounded blocks numerically rather than iterating billions of bits.
    for alignment in range(4):
        count = max(0, (len(raw) - alignment) // 4)
        words = np.frombuffer(raw, dtype='<f4', offset=alignment, count=count)
        for start in range(0, max(0, count - 2), 1048576):
            stop = min(start + 1048576, count - 2)
            with np.errstate(invalid='ignore', over='ignore'):
                positions = np.flatnonzero(abs(words[start:stop].astype(float) - point[0]) < tolerance)
            for index in positions:
                got = tuple(float(v) for v in words[start + int(index):start + int(index) + 3])
                if all(np.isfinite(got)):
                    error = max(abs(a-b) for a, b in zip(point, got))
                    if error < tolerance:
                        return error
    return None


def scan_points(raw, points, tolerance=.0001, chunk_words=1048576):
    points = [tuple(map(float, point)) for point in points]
    errors = [None] * len(points)
    packed = [struct.pack('<3f', *point) for point in points]
    wanted = {}
    fallback = []
    for index, point in enumerate(points):
        assert all(np.isfinite(point)), ('Invalid source vertex', point)
        if point[0] <= tolerance:
            fallback.append(index)
            continue
        lo = struct.unpack('<I', struct.pack('<f', point[0] - tolerance))[0]
        hi = struct.unpack('<I', struct.pack('<f', point[0] + tolerance))[0]
        if hi - lo > 65536:
            fallback.append(index)
            continue
        bits = set(range(lo, hi + 1))
        bits.add(struct.unpack_from('<I', packed[index])[0])
        for value in bits:
            wanted.setdefault(value, []).append(index)
    for index in fallback:
        errors[index] = probe(raw, points[index], tolerance)
    if not wanted:
        return errors
    lower = min(wanted)
    upper = max(wanted)
    table = None
    sorted_bits = np.array(sorted(wanted), dtype=np.uint32)
    if upper - lower <= 100000000:
        table = np.zeros(upper - lower + 1, dtype=bool)
        table[sorted_bits - lower] = True
    last_report = time.monotonic()
    for alignment in range(4):
        count = max(0, (len(raw) - alignment) // 4)
        words = np.frombuffer(raw, dtype='<u4', offset=alignment, count=count)
        for start in range(0, count, chunk_words):
            chunk = words[start:start + chunk_words]
            positions = np.flatnonzero((chunk >= lower) & (chunk <= upper))
            values = chunk[positions]
            if table is not None:
                positions = positions[table[values - lower]]
            else:
                found = np.searchsorted(sorted_bits, values)
                valid = found < len(sorted_bits)
                valid[valid] &= sorted_bits[found[valid]] == values[valid]
                positions = positions[valid]
            for position in positions:
                offset = alignment + 4 * (start + int(position))
                if offset + 12 > len(raw):
                    continue
                triple = raw[offset:offset + 12]
                xyz = struct.unpack('<3f', triple)
                for index in wanted[int(chunk[position])]:
                    if errors[index] == 0:
                        continue
                    if triple == packed[index]:
                        errors[index] = 0.
                        continue
                    error = max(abs(a-b) for a, b in zip(points[index], xyz))
                    if error < tolerance and (errors[index] is None or error < errors[index]):
                        errors[index] = error
            if time.monotonic() - last_report >= 15:
                print('Native vertex scan: alignment ' + str(alignment) + ', ' + str(sum(e is not None for e in errors)) + '/' + str(len(points)) + ' points found', flush=True)
                last_report = time.monotonic()
    return errors
