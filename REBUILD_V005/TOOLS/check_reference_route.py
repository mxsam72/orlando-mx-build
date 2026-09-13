#!/usr/bin/env python3
"""Focused math checks; these are synthetic fixtures, not Orlando geometry."""
import tempfile
import json
from pathlib import Path
import numpy as np
from reference_route import build, load_trace, sample_trace, validate_route, UnresolvedRoute

def main():
    checks = {}
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        t = np.linspace(0, 2 * np.pi, 49)
        points = [{'x_m': float(300 + 130 * np.cos(a)), 'z_m': float(300 + 80 * np.sin(a)), 'width_m': 10.} for a in t]
        trace = dict(route_status='resolved', coordinate_system='game_xz_metres', source_registration={'type': 'SYNTHETIC_TEST_ONLY'}, points=points)
        path = root / 'fixture.json'
        path.write_text(json.dumps(trace))
        result = build(path, root / 'result')
        assert result['native_closure_m'] < 1e-6
        assert result['native_to_spline_max_m'] < .15
        checks['native_geometry_matches_spline'] = result
        trace['points'] = points[:-1]
        path.write_text(json.dumps(trace))
        try: load_trace(path)
        except UnresolvedRoute: checks['open_route_rejected'] = True
        else: raise AssertionError('Open route was silently closed')
        trace['points'] = []
        trace['route_status'] = 'unresolved'
        path.write_text(json.dumps(trace))
        try: load_trace(path)
        except UnresolvedRoute: checks['unresolved_route_rejected'] = True
        else: raise AssertionError('Unresolved route was replaced with a default')
        # A figure-eight has two non-local racing corridors at its crossing.
        p = np.c_[300 + 100 * np.sin(t), 300 + 80 * np.sin(2 * t), np.full(len(t), 10.)]
        q, w, _, _ = sample_trace(p)
        try: validate_route(q, w)
        except ValueError as exc:
            assert 'overlap' in str(exc)
            checks['crossed_racing_corridors_rejected'] = True
        else: raise AssertionError('Self-crossing route passed geometry checks')
    print(json.dumps(checks, indent=2))

if __name__ == '__main__': main()
