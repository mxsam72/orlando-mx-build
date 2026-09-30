"""Move the native shared gate/grid, start-only checkpoints and 30s board together.

TrackEd documents Start/Both checkpoint intent:
https://docs.piboso.com/wiki/index.php/TrackEd#Race_Data
The candidate still requires TrackEd and in-game verification of first-lap behavior.
"""
import re, math, struct, shutil
import numpy as np
from v016_common import *
from build_race_data import block

def span(text, name):
    m = re.search(r'(?m)^'+re.escape(name)+r'\s*\n\{', text)
    if not m: raise ValueError('Missing RDF block '+name)
    start = m.start(); pos = text.index('{', m.start()); depth = 1; end = pos+1
    while depth:
        depth += (text[end]=='{')-(text[end]=='}'); end += 1
    return start, end
def replace_block(text, name, replacement):
    a,b = span(text, name); return text[:a]+replacement.rstrip()+text[b:]
def formatted(d):
    return {k: f'{v:.9f}' if isinstance(v, float) else v for k,v in d.items()}

def main():
    cfg = read(O/'facility_layout.json'); q,w = route(); sa = np.load(O/'route.npz')['start']; L = q[-1,3]
    sources = [R/'BUILD/v009_work/12_RELEASE/orlandomx_2026_v008/orlandomx_2026_v008.rdf', R/'BUILD/v007_extract/12_RELEASE/orlandomx_2026_v007/orlandomx_2026_v007.rdf']
    source = next(p for p in sources if p.exists()); text = source.read_text(encoding='utf-8'); original = text
    gx,gz = cfg['grid_center_xz']; stalls = cfg['grid']; count = len(stalls)
    grid = block('starting_grid', formatted(dict(numstalls=count,type=1,posx=gx,posz=gz,angle=cfg['grid_angle_deg'],numstallsperrow=count,distfromstartline=0,lanespacing=0,rowspacing=0,difflat=0,lanewidth=cfg['stall_spacing_m'],latshift=0,side=1)))[:-2]
    errors = []
    for i,st in enumerate(stalls):
        projected = project(q,st['x'],st['z'],st['angle']); grid += block(f' stall{i}', formatted(projected))
        p = route_point(q, projected['long']); reconstructed = p[:2]+projected['lat']*np.array([np.sin(p[2]),-np.cos(p[2])])
        errors.append(float(np.linalg.norm(reconstructed-np.array([st['x'],st['z']]))))
    text = replace_block(text,'starting_grid',grid+'}\n')
    a = re.search(r'(?m)^num_checkpoints\s*=', text).start(); b = text.index('30secondsboard_posx', a)
    cps = []
    for s in cfg['start_checkpoint_stations_m']:
        half = float(np.interp(s,*np.array(cfg['start_width_knots']).T))/2+1
        cps.append(dict(long=s,left=-half,right=half,penalty=5,line=2,start=cfg['native_checkpoint_modes']['start_only']))
    finish = cfg['finish_station_m']; merge = cfg['merge_station_m']
    for t in read(R/'V009_SOURCE/baseline_geometry.json')['turns']:
        s = t['mid']; on_start = (s-merge)%L < (finish-merge)%L
        cps.append(dict(long=s,left=-t['width']/2-1,right=t['width']/2+1,penalty=5,line=0,start=cfg['native_checkpoint_modes']['both' if on_start else 'normal']))
    cps_text = f'num_checkpoints = {len(cps)}\n'+''.join(block(f'checkpoint{i}',formatted(c)) for i,c in enumerate(cps))
    text = text[:a]+cps_text+text[b:]
    # Board outside the last stall, ahead of the grid, facing back at the riders.
    bx,bz,ba = gx-count*cfg['stall_spacing_m']/2-3,gz+7,180.
    for key,value in [('posx',bx),('posz',bz),('angle',ba)]:
        text = re.sub(r'(?m)^30secondsboard_'+key+r'\s*=.*$',f'30secondsboard_{key} = {value:.9f}',text)
    text = replace_block(text,'30seconds_board',block('30seconds_board',formatted(project(q,bx,bz,ba))))
    (O/(NAME+'.rdf')).write_text(text,encoding='utf-8')
    # Main-circuit reset boundaries remain station-compatible and are copied
    # byte-for-byte; start-area resets depend on the newly merged start TCL.
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
        src=source.parent/name; raw=src.read_bytes(); assert raw[:4]==b'TL \0'
        n=struct.unpack_from('<I',raw,4)[0]; assert len(raw)==8+8*n
        shutil.copy2(src,O/name)
    preserved={}
    for name in ['finish_line','split1','split2','pit_lane','pit_board']:
        a,b=span(original,name); c,d=span(text,name); preserved[name]=original[a:b]==text[c:d]
    qa=dict(grid_stalls=count,grid_reconstruction_max_error_m=max(errors),preserved=preserved,start_checkpoints=sum(c['line']==2 for c in cps),both_checkpoints=sum(c['start']==2 for c in cps),normal_only_checkpoints=sum(c['start']==0 for c in cps),first_lap_expected_turns=['T06','T07','T08','T09','T10','T11','T12','T13','T14'],board_xyz_angle=[bx,bz,ba],shared_gate_placement='Native shared gate follows RDF grid; no fixed collision gate added',start_reset_runtime_check_pending=True,first_lap_runtime_check_pending=True)
    qa['race_source_checks_pass']=max(errors)<.03 and all(preserved.values()) and qa['both_checkpoints']==9 and qa['normal_only_checkpoints']==5 and qa['start_checkpoints']==3
    save(O/'race_positions.json',dict(grid=stalls,checkpoints=cps,board=dict(x=bx,z=bz,angle=ba)))
    save(R/'DOCUMENTATION/v016_race_validation.json',qa); print(qa)
    if not qa['race_source_checks_pass']: raise RuntimeError('Race-data QA failed')
if __name__=='__main__': main()
