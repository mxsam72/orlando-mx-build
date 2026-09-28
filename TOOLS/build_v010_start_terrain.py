"""Grade the separate gate apron and taper into T05; retain the lap approach."""
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
from v010_common import *

def fields(H, shape=(N, N)):
    cfg = read(O/'facility_layout.json'); q, w = route(); sa = np.load(O/'route.npz')['start']
    stree = cKDTree(sa[:, :2]); mtree = cKDTree(q[:, :2]); old = np.load(R/'V009_SOURCE/baseline_route.npz')['start']; otree = cKDTree(old[:, :2])
    rows, cols = shape; xx, zz = np.meshgrid(np.linspace(0, SIZE, cols), np.linspace(SIZE, 0, rows)); pts = np.c_[xx.ravel(), zz.ravel()]
    sd, si = stree.query(pts, workers=2); md, mi = mtree.query(pts, workers=2); od, oi = otree.query(pts, workers=2)
    st = sa[si, 3]; widths = np.interp(st, *np.array(cfg['start_width_knots']).T)
    # Restrict the origin cap behind the gates; allow a smooth merging cap.
    alpha = (1-ease((sd-widths/2)/4)) * ease((pts[:, 1]-cfg['start_origin_xz'][1]+4)/4)
    core = (1-ease((sd-widths/2+.4)/1.2)) * ease((pts[:, 1]-cfg['start_origin_xz'][1]+2)/2)
    distance_end = sa[-1, 3]-st
    # Match the complete existing T05 cross-section in the last 22 m.
    grade_blend = ease(distance_end/cfg['merge_blend_length_m'])
    main_guard = ease((md-w[mi]/2-1)/3)
    weight = alpha*grade_blend*main_guard
    # Constant flat gate bed, then smooth longitudinal elevation interpolation.
    start_h = float(ground(H, np.array([cfg['grid_center_xz']]))[0])
    end_h = float(ground(H, sa[-1:, :2])[0])
    desired = start_h+(end_h-start_h)*ease((st-28)/max(sa[-1, 3]-28, 1))
    old_width = 10.5+25.5*(1-ease((old[oi, 3]-12)/43))
    retire = (1-ease((od-old_width/2)/2))*(1-ease((236-pts[:, 0])/2))
    return {k: v.reshape(shape) for k, v in dict(weight=weight, desired=desired, start=core, retire=retire, main_distance=md, main_width=w[mi], start_station=st, start_distance=sd).items()}

def main():
    source = O/'main_terrain.raw'
    base = np.fromfile(source, '<u2').reshape(N, N).astype(np.float32)/65535*SCALE
    f = fields(base); H = base+(f['desired']-base)*f['weight']
    encoded = np.round(H/SCALE*65535).astype('<u2'); H = encoded.astype(np.float32)/65535*SCALE
    assert np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
    encoded.tofile(O/'terrain.raw'); Image.fromarray(encoded).save(O/'terrain_16bit.png'); np.save(O/'height_metres.npy', H)
    np.savez_compressed(O/'facility_fields.npz', **{k:v.astype(np.float32) for k,v in f.items() if k!='desired'})
    dz, dx = np.gradient(H, SIZE/(N-1)); grades = np.hypot(dx, dz); cfg = read(O/'facility_layout.json')
    grid = np.array([[s['x'], s['z']] for s in cfg['grid']]); levels = ground(H, grid)
    delta = abs(H-base); main = f['main_distance']<f['main_width']/2+1
    qa = dict(raw_sha256=sha(O/'terrain.raw'), gate_height_spread_m=float(np.ptp(levels)), gate_max_grade=float(ground(grades, grid).max()), main_lap_max_delta_m=float(delta[main].max()), start_max_grade=float(grades[f['start']>.9].max()), changed_max_grade=float(grades[delta>.001].max()), changed_nodes=int((delta>.001).sum()), retired_start_surface=True, native_compilation=False, in_game_riding=False)
    qa['start_terrain_checks_pass'] = qa['gate_height_spread_m']<.01 and qa['gate_max_grade']<.02 and qa['main_lap_max_delta_m']<.001 and qa['changed_max_grade']<.84
    save(R/'DOCUMENTATION/v010_start_validation.json', qa); print(qa)
    if not qa['start_terrain_checks_pass']: raise RuntimeError('Start terrain QA failed')
if __name__ == '__main__': main()
