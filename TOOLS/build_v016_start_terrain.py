"""Grade the separate gate apron and loop outside T05 and merge before T06; retain the lap approach."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from PIL import Image
from v016_common import *

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
    # General apron blend preserves the normal lap. A separate, limited opening
    # below cuts the outside entry bank where the start must pass through it.
    grade_blend = ease(distance_end/cfg['merge_blend_length_m'])
    main_guard = ease((md-w[mi]/2-1)/3)
    weight = alpha*grade_blend*main_guard
    dv=pts-q[mi,:2];th=q[mi,2]
    left_offset=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th)
    main_station=q[mi,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th)
    opening_long=ease((st-(sa[-1,3]-28))/6)*(1-ease((st-(sa[-1,3]-5))/4))
    # T05 is a left turn: negative left-offset is its outside. Keep the native
    # centerline and inside line intact, and open only the outside shoulder on the final convergence to T06.
    outside=ease((-left_offset-.4)/.7)
    local=(main_station>cfg['merge_station_m']-24)&(main_station<cfg['merge_station_m']+3)
    opening=alpha*opening_long*outside*local
    weight=np.maximum(weight,opening)
    # Constant flat gate bed, then smooth longitudinal elevation interpolation.
    start_h = float(ground(H, np.array([cfg['grid_center_xz']]))[0])
    end_h = float(ground(H, sa[-1:, :2])[0])
    desired = start_h+(end_h-start_h)*ease((st-28)/max(sa[-1, 3]-28, 1))
    old_width = 10.5+25.5*(1-ease((old[oi, 3]-12)/43))
    retire = (1-ease((od-old_width/2)/2))*(1-ease((236-pts[:, 0])/2))
    return {k: v.reshape(shape) for k, v in dict(weight=weight, desired=desired, start=core, retire=retire, main_distance=md, main_width=w[mi], start_station=st, start_distance=sd, merge_opening=opening, main_station=main_station).items()}

def main():
    source = O/'main_terrain.raw'
    base = np.fromfile(source, '<u2').reshape(N, N).astype(np.float32)/65535*SCALE
    f = fields(base); H = base+(f['desired']-base)*f['weight']
    # Round the shoulder where the new bank opening meets its retained wall.
    # Do not expand the edit footprint across the normal centerline.
    changed=f['weight']>1e-5;passes=0
    for _ in range(50):
        dz,dx=np.gradient(H,SIZE/(N-1));bad=(np.hypot(dx,dz)>.76)&changed
        if not bad.any():break
        blend=np.clip(gaussian_filter(bad.astype(np.float32),1.2)*5,0,1)*changed
        H=H+(gaussian_filter(H,1.5)-H)*blend;passes+=1
    encoded = np.round(H/SCALE*65535).astype('<u2'); H = encoded.astype(np.float32)/65535*SCALE
    assert np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
    encoded.tofile(O/'terrain.raw'); Image.fromarray(encoded).save(O/'terrain_16bit.png'); np.save(O/'height_metres.npy', H)
    np.savez_compressed(O/'facility_fields.npz', **{k:v.astype(np.float32) for k,v in f.items() if k!='desired'})
    dz, dx = np.gradient(H, SIZE/(N-1)); grades = np.hypot(dx, dz); cfg = read(O/'facility_layout.json')
    grid = np.array([[s['x'], s['z']] for s in cfg['grid']]); levels = ground(H, grid)
    delta = abs(H-base); main = f['main_distance']<f['main_width']/2+1
    q,w=route();sa=np.load(O/'route.npz')['start'];along=ground(H,sa[:,:2]);start_slope=np.gradient(along,sa[:,3])
    protected=main&(f['weight']<=1e-5)
    qa = dict(raw_sha256=sha(O/'terrain.raw'), gate_height_spread_m=float(np.ptp(levels)), gate_max_grade=float(ground(grades, grid).max()), main_centerline_max_delta_m=float(abs(ground(H,q[:,:2])-ground(base,q[:,:2])).max()), normal_lap_outside_merge_max_delta_m=float(delta[protected].max()), merge_bank_max_lower_m=float(np.maximum(base-H,0)[f['merge_opening']>.1].max()), start_max_grade=float(grades[f['start']>.9].max()), start_centerline_max_grade=float(abs(start_slope).max()), changed_max_grade=float(grades[delta>.001].max()), changed_nodes=int((delta>.001).sum()), retired_start_surface=True, native_compilation=False, in_game_riding=False)
    qa['start_terrain_checks_pass'] = qa['gate_height_spread_m']<.01 and qa['gate_max_grade']<.02 and qa['main_centerline_max_delta_m']<.001 and qa['normal_lap_outside_merge_max_delta_m']<.001 and qa['changed_max_grade']<.84 and qa['start_centerline_max_grade']<.22
    qa['merge_shoulder_relaxation_passes']=passes
    save(R/'DOCUMENTATION/v016_start_validation.json', qa); print(qa)
    if not qa['start_terrain_checks_pass']: raise RuntimeError('Start terrain QA failed')
if __name__ == '__main__': main()
