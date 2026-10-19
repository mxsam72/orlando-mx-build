"""Generic native line/arc export math. No track geometry is embedded."""
from pathlib import Path
import math
import numpy as np

def native_segments(q, station_spacing=2.0):
    """Approximate the sampled curve with G1-continuous lines/circular fillets.

    TrackEd supports straights and circular arcs. Small fillets applied to a
    densely sampled polygon give variable curvature and exact geometric loop
    closure without an invented straight. The terrain remains spline-based.
    """
    L = q[-1, 3]
    stations = np.linspace(0, L, max(16, math.ceil(L / station_spacing)), endpoint=False)
    p = np.c_[np.interp(stations, q[:, 3], q[:, 0]), np.interp(stations, q[:, 3], q[:, 1])]
    edges = np.roll(p, -1, axis=0) - p
    lengths = np.linalg.norm(edges, axis=1)
    unit = edges / lengths[:, None]
    prev = np.roll(unit, 1, axis=0)
    angles = np.arctan2(prev[:, 0] * unit[:, 1] - prev[:, 1] * unit[:, 0], np.sum(prev * unit, axis=1))
    trim = np.minimum(np.roll(lengths, 1), lengths) * .24
    trim[np.abs(angles) < 1e-8] = 0
    entries = p - prev * trim[:, None]
    exits = p + unit * trim[:, None]
    segments = []
    for i in range(len(p)):
        d = float(np.linalg.norm(entries[(i + 1) % len(p)] - exits[i]))
        if d > 1e-8:
            segments.append((0, d, 0., 0.))
        j = (i + 1) % len(p)
        if trim[j] > 0:
            a = float(angles[j])
            radius = float(trim[j] / math.tan(abs(a) / 2))
            segments.append((1, abs(a) * radius, -math.copysign(radius, a), abs(math.degrees(a))))
    theta = math.atan2(unit[0, 1], unit[0, 0])
    return exits[0], theta, segments


def sample_native(origin, theta, segments, spacing=.25):
    """Independently reconstruct the emitted native centerline for comparison."""
    pos = np.asarray(origin, dtype=float).copy()
    rows = [[*pos, theta, 0.]]
    s = 0.
    for typ, length, radius, degrees in segments:
        start = pos.copy()
        oldtheta = theta
        for u in np.linspace(0, 1, math.ceil(length / spacing) + 1)[1:]:
            if typ == 0:
                pos = start + length * u * np.array([math.cos(oldtheta), math.sin(oldtheta)])
                theta = oldtheta
            else:
                sign = -np.sign(radius)
                a = math.radians(degrees) * sign
                theta = oldtheta + u * a
                center = start + sign * abs(radius) * np.array([-math.sin(oldtheta), math.cos(oldtheta)])
                pos = center - sign * abs(radius) * np.array([-math.sin(theta), math.cos(theta)])
            rows.append([*pos, theta, s + u * length])
        s += length
    return np.asarray(rows)


def write_tcl(path, origin, theta, segments):
    angle = (90 - math.degrees(theta)) % 360
    text = f'x = {origin[0]:.9f}\nz = {origin[1]:.9f}\nangle = {angle:.9f}\nnumsegment = {len(segments)}\n'
    for i, (typ, length, radius, ang) in enumerate(segments):
        text += f'segment{i}\n{{\n type = {typ}\n length = {length:.9f}\n radius = {radius:.9f}\n angle = {ang:.9f}\n height = 0\n heightlock = 0\n}}\n'
    Path(path).write_text(text)

