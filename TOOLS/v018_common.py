"""Shared metric layout, serialization and sampling for the v018 candidate."""
from pathlib import Path
import json, hashlib, math
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.interpolate import CubicHermiteSpline
from reference_route import sample_native, write_tcl

R = Path(__file__).resolve().parents[1]
O = R / 'V018_OUTPUT'
S = R / 'V018_SOURCE'
N, SIZE, SCALE = 2049, 600., 18.
NAME = 'orlandomx_2026_v018'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p, value):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_plot(fig,path,**kwargs):
    """Buffer and verify PNGs before replacing a checkpoint preview."""
    import io
    from PIL import Image
    buffer=io.BytesIO();fig.savefig(buffer,format='png',**kwargs);raw=buffer.getvalue()
    Image.open(io.BytesIO(raw)).verify();path=Path(path);temporary=path.with_suffix('.png.tmp')
    temporary.write_bytes(raw);Image.open(temporary).verify();temporary.replace(path)
def ease(t):
    t = np.clip(t, 0, 1)
    return t**3*(10-15*t+6*t*t)
def ground(H, xz):
    xz = np.asarray(xz)
    return map_coordinates(H, [(SIZE-xz[..., 1])/SIZE*(N-1), xz[..., 0]/SIZE*(N-1)], order=1, mode='nearest')
def route():
    d = np.load(R/'V009_SOURCE/baseline_route.npz')
    return d['q'], d['width']
def route_point(q, s):
    return np.array([np.interp(s, q[:, 3], q[:, k]) for k in range(3)])

def start_path(cfg, q):
    """Fit an open native line/arc chain with exact origin and end tangents."""
    end = route_point(q, cfg['merge_station_m'])
    direction = np.array([math.cos(end[2]), math.sin(end[2])])
    controls = np.array(cfg['start_controls_xz'] + [(end[:2]-3*direction).tolist()])
    knots = np.r_[0, np.cumsum(np.linalg.norm(np.diff(controls, axis=0), axis=1))]
    tangent = np.gradient(controls, knots, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    tangent[0] = [0, 1]; tangent[-1] = direction
    sp = CubicHermiteSpline(knots, controls, tangent)
    pp = np.vstack([cfg['start_origin_xz'], sp(np.linspace(0, knots[-1], 45)), end[:2]])
    v = np.diff(pp, axis=0); lens = np.linalg.norm(v, axis=1); u = v/lens[:, None]
    angles = np.arctan2(u[:-1, 0]*u[1:, 1]-u[:-1, 1]*u[1:, 0], (u[:-1]*u[1:]).sum(1))
    trim = np.minimum(lens[:-1], lens[1:])*.24
    entries = pp.copy(); exits = pp.copy()
    entries[1:-1] -= u[:-1]*trim[:, None]; exits[1:-1] += u[1:]*trim[:, None]
    segs = []
    for i in range(len(pp)-1):
        segs.append((0, float(np.linalg.norm(entries[i+1]-exits[i])), 0., 0.))
        if i < len(angles) and abs(angles[i]) > 1e-9:
            radius = trim[i]/math.tan(abs(angles[i])/2)
            segs.append((1, float(abs(angles[i])*radius), float(-math.copysign(radius, angles[i])), float(abs(math.degrees(angles[i])))))
    theta = math.atan2(u[0, 1], u[0, 0])
    return sample_native(pp[0], theta, segs, .2), segs, theta

def project(q, x, z, absangle):
    """Invert native Frenet coordinates; important for absolute grid stalls."""
    from scipy.optimize import minimize_scalar
    target = np.array([x, z]); a = q[:-1, :2]; v = q[1:, :2]-a
    uv = np.clip(((target-a)*v).sum(1)/(v*v).sum(1), 0, 1)
    i = int(np.argmin(np.linalg.norm(a+uv[:, None]*v-target, axis=1)))
    s0 = q[i, 3]+uv[i]*(q[i+1, 3]-q[i, 3])
    def f(s):
        p = route_point(q, s); return ((target-p[:2])@np.array([np.cos(p[2]), np.sin(p[2])]))**2
    s = minimize_scalar(f, bounds=(max(0, s0-3), min(q[-1, 3], s0+3)), method='bounded', options={'xatol':1e-11}).x
    p = route_point(q, s); lat = (target-p[:2])@np.array([np.sin(p[2]), -np.cos(p[2])])
    angle = (90-math.degrees(p[2])) % 360
    return {'long': float(s), 'lat': float(lat), 'angle': float((absangle-angle+180)%360-180)}

def main():
    O.mkdir(exist_ok=True); cfg = read(S/'facilities.json'); q, w = route()
    sa, segs, theta = start_path(cfg, q)
    write_tcl(O/'start.tcl', sa[0, :2], theta, segs)
    data = dict(np.load(R/'V009_SOURCE/baseline_route.npz')); data['start'] = sa
    np.savez_compressed(O/'route.npz', **data)
    merge = route_point(q, cfg['merge_station_m'])
    err = abs((sa[-1, 2]-merge[2]+np.pi)%(2*np.pi)-np.pi)
    assert np.linalg.norm(sa[-1, :2]-merge[:2]) < .001 and err < .001
    center = np.array(cfg['grid_center_xz']); spacing = cfg['stall_spacing_m']
    grid = [dict(x=float(center[0]+(i-(cfg['grid_stalls']-1)/2)*spacing), z=float(center[1]), angle=cfg['grid_angle_deg']) for i in range(cfg['grid_stalls'])]
    save(O/'facility_layout.json', dict(**cfg, start_length_m=float(sa[-1, 3]), start_segments=segs, grid=grid, merge_xz=merge[:2].tolist(), merge_heading_error_deg=math.degrees(err)))
    print('v018 start line:', len(segs), 'native segments;', round(sa[-1, 3], 2), 'm; merge before T06 exact')
if __name__ == '__main__': main()
