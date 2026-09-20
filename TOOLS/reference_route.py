#!/usr/bin/env python3
"""Build a sampled MX Bikes centerline from an explicitly traced closed route.

This replaces v004's hand-picked angles/straight lengths. Input control points
must be placed in metres using an external reference, with provenance retained.
It does not infer a current Orlando layout from a turn-count or force an open
trace to close. No example circuit is embedded in the production input.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.spatial import cKDTree


class UnresolvedRoute(ValueError):
    pass


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def load_trace(path):
    data = json.loads(Path(path).read_text())
    points = data.get('points', [])
    if len(points) < 8 or data.get('route_status') != 'resolved':
        raise UnresolvedRoute('Current route is unresolved; supply a complete reference trace.')
    if data.get('coordinate_system') != 'game_xz_metres':
        raise UnresolvedRoute('Image pixels must be registered/scaled before building terrain.')
    if not data.get('source_registration'):
        raise UnresolvedRoute('Missing source registration/provenance.')
    p = np.array([[v['x_m'], v['z_m'], v['width_m']] for v in points], dtype=float)
    if not np.isfinite(p).all() or (p[:, 2] <= 0).any():
        raise ValueError('Every position and width must be finite, with positive width.')
    if np.linalg.norm(p[-1, :2] - p[0, :2]) > .01:
        raise UnresolvedRoute('Trace must explicitly end at its starting point; no closure extension is added.')
    if np.any(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1) < .01):
        raise ValueError('Duplicate consecutive trace points.')
    if abs(p[-1, 2] - p[0, 2]) > .001:
        raise ValueError('Width must be continuous at the lap seam.')
    p[-1] = p[0]  # Remove tolerated numerical rounding at the explicit seam.
    return data, p


def sample_trace(p, spacing=.25):
    """Periodic curve through the traced points, with arc-length sampling.

    Intermediate controls should describe real bend shape, not only apexes.
    The curve is C2 continuous at the start/finish seam. Its footprint must
    still be checked against the source after interpolation.
    """
    if spacing <= 0:
        raise ValueError('Sample spacing must be positive.')
    knots = np.r_[0., np.cumsum(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1))]
    spline = CubicSpline(knots, p[:, :2], bc_type='periodic')
    tt = np.linspace(0, knots[-1], max(5000, math.ceil(knots[-1] / .05)))
    dense = spline(tt)
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    ss = np.linspace(0, arc[-1], math.ceil(arc[-1] / spacing) + 1)
    t = np.interp(ss, arc, tt)
    xz = spline(t)
    velocity = spline(t, 1)
    acceleration = spline(t, 2)
    speed = np.linalg.norm(velocity, axis=1)
    if np.min(speed) < 1e-5:
        raise ValueError('Degenerate spline tangent; inspect neighboring trace points.')
    heading = np.unwrap(np.arctan2(velocity[:, 1], velocity[:, 0]))
    curvature = (velocity[:, 0] * acceleration[:, 1] - velocity[:, 1] * acceleration[:, 0]) / speed ** 3
    width = PchipInterpolator(knots, p[:, 2])(t)
    xz[-1] = xz[0]
    width[-1] = width[0]
    q = np.c_[xz, heading, ss, np.zeros(len(ss))]
    return q, width, curvature, np.interp(knots, tt, arc)


def validate_route(q, width, canvas=600):
    """Detect geometry faults; this is not a claim of real-world fidelity."""
    if (q[:, :2].min() < 0 or q[:, :2].max() > canvas):
        raise ValueError('Route lies outside the terrain canvas.')
    clearance = np.minimum(q[:, :2], canvas - q[:, :2]).min(axis=1) - width / 2
    if clearance.min() < 3:
        raise ValueError('Racing surface reaches the terrain border.')
    # Test non-local portions, excluding adjacent samples and lap seam.
    step = max(1, int(round(1.0 / np.median(np.diff(q[:, 3])))))
    sub = q[:-1:step]
    subwidth = width[:-1:step]
    pairs = cKDTree(sub[:, :2]).query_pairs(float(subwidth.max() + 3), output_type='ndarray')
    conflicts = []
    for i, j in pairs:
        separation = abs(sub[j, 3] - sub[i, 3])
        separation = min(separation, q[-1, 3] - separation)
        required = (subwidth[i] + subwidth[j]) / 2 + 1
        if separation < max(30, 3 * required):
            continue
        distance = float(np.linalg.norm(sub[j, :2] - sub[i, :2]))
        if distance < required:
            conflicts.append([float(sub[i, 3]), float(sub[j, 3]), distance, float(required)])
    if conflicts:
        raise ValueError(f'Non-local racing corridors overlap: {conflicts[:8]}')
    return {'sample_count': len(q), 'model_lap_length_m': float(q[-1, 3]),
            'loop_closure_m': float(np.linalg.norm(q[-1, :2] - q[0, :2])),
            'width_range_m': [float(width.min()), float(width.max())],
            'minimum_terrain_border_clearance_m': float(clearance.min()),
            'corridor_conflicts': 0, 'real_world_fidelity_verified': False}


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


def build(input_path, output):
    data, p = load_trace(input_path)
    q, width, curvature, control_s = sample_trace(p)
    qa = validate_route(q, width, data.get('canvas_m', 600))
    origin, theta, segments = native_segments(q)
    native = sample_native(origin, theta, segments)
    qa['native_closure_m'] = float(np.linalg.norm(native[-1, :2] - native[0, :2]))
    qa['native_to_spline_max_m'] = float(cKDTree(q[:, :2]).query(native[:, :2])[0].max())
    qa['native_centerline_length_m'] = float(native[-1, 3])
    qa['native_segment_count'] = len(segments)
    qa['native_compilation'] = False
    if qa['native_closure_m'] > .02 or qa['native_to_spline_max_m'] > .4:
        raise ValueError(f'Native centerline approximation failed: {qa}')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'route.npz', q=q, width=width, curvature=curvature, control_s=control_s, native=native)
    with (out / 'centerline.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['x_m', 'z_m', 'heading_rad', 'source_chainage_m', 'width_m', 'curvature_per_m'])
        writer.writerows(np.c_[q[:, :4], width, curvature])
    write_tcl(out / 'main.tcl', origin, theta, segments)
    (out / 'route_validation.json').write_text(json.dumps(qa, indent=2) + '\n')
    return qa


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('trace')
    parser.add_argument('output')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.trace, args.output), indent=2))
    except UnresolvedRoute as exc:
        parser.exit(2, f'REBUILD INCOMPLETE: {exc}\n')



