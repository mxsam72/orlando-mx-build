"""v024 targeted QA: T05 sweeping hill, T06 smoother right, T13 right-fade into rollers."""
import json, numpy as np
from scipy.ndimage import label
from v024_common import *
from pit_roads_v024 import road_field, grass_field

def main():
    now=read(S/'v024_geometry_spec.json');old=read(R/'V023_SOURCE/v023_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};po={p['id']:p for p in old['profiles']}
    bn={b['id']:b for b in now['berms']};bo={b['id']:b for b in old['berms']}
    checks={}
    for rid in pn:checks['preserve_'+rid]=pn[rid]==po[rid]
    for tid in bn:
        if tid not in ['T05','T06','T13']:checks['preserve_'+tid]=bn[tid]==bo[tid]

    # Keep the post-R10 T09 exact v023/v021 reverted shape.
    checks['T09_still_preserved']=bn['T09']==bo['T09']

    t05,t06,t13=bn['T05'],bn['T06'],bn['T13']
    checks['T05_wider_sweep']=t05['effective_width_m']>bo['T05']['effective_width_m']
    checks['T05_bank_not_oversteepened']=t05['outer_rise_m']<=bo['T05']['outer_rise_m']+.10
    hills=now.get('longitudinal_hills',[])
    checks['T05_hill_authored']=len(hills)==1 and hills[0]['id']=='T05_sweeping_hill' and hills[0]['height_m']>=1.25
    h=hills[0]
    checks['T05_hill_descends_before_T06']=h['station_end_m']<497.69412320955183

    # T06 should undo the v023 over-steep treatment and remain broad/flowing.
    checks['T06_lower_than_v023']=t06['outer_rise_m']<bo['T06']['outer_rise_m']-.4
    checks['T06_wide']=t06['effective_width_m']>=9.0
    checks['T06_shallower_pocket']=t06['pocket_depth_m']<bo['T06']['pocket_depth_m']
    checks['T06_smoother_load']=t06['entry_load']<bo['T06']['entry_load'] and t06['exit_load']>bo['T06']['exit_load']

    # T13 needs actual path shape, not just a wider berm.
    adj=now.get('route_adjustments',[])
    checks['T13_route_adjustment_authored']=len(adj)==1 and adj[0]['id']=='T13_right_fade'
    checks['T13_right_fade_magnitude']=adj[0]['max_right_offset_m']>=3.0
    checks['T13_broader_softer_berm']=t13['effective_width_m']>=10.0 and t13['outer_rise_m']<bo['T13']['outer_rise_m'] and t13['entry_load']<bo['T13']['entry_load']

    q,w=route();base=np.load(R/'V009_SOURCE/baseline_route.npz')['q']
    delta=q[:,:2]-base[:,:2];left=np.c_[-np.sin(base[:,2]),np.cos(base[:,2])]
    lateral=(delta*left).sum(1);s=base[:,3]
    zone=(s>=adj[0]['station_start_m'])&(s<=adj[0]['station_end_m'])
    outside=~zone
    checks['T13_route_moves_right']=float(lateral[zone].min())<-3.0
    checks['route_unchanged_outside_T13_zone']=float(np.abs(delta[outside]).max())<1e-6

    # Verify the authored T05 longitudinal hill is actually present in encoded terrain.
    H=np.fromfile(O/'main_terrain.raw','<u2').reshape(N,N)/65535*SCALE
    ss=np.array([h['station_start_m'],h['station_peak_m'],h['station_end_m']])
    pts=np.array([[np.interp(x,q[:,3],q[:,0]),np.interp(x,q[:,3],q[:,1])] for x in ss])
    elev=ground(H,pts);chord=np.interp(ss,[ss[0],ss[-1]],[elev[0],elev[-1]])
    checks['T05_encoded_hill_visible']=float(elev[1]-chord[1])>.75

    checks['facilities_unchanged']=read(S/'facilities.json')==read(R/'V023_SOURCE/facilities.json')
    checks['start_layout_unchanged']=read(S/'start_layout.json')==read(R/'V023_SOURCE/start_layout.json')
    checks['pit_facilities_unchanged']=read(S/'pit_facilities.json')==read(R/'V023_SOURCE/pit_facilities.json')
    checks['vehicles_unchanged']=read(S/'vehicles.json')==read(R/'V023_SOURCE/vehicles.json')
    pit=read(S/'pit_facilities.json');roads=road_field((768,768));grass=grass_field((768,768));_,count=label(roads>.30)
    checks['pit_road_network_still_connected']=int(count)==1
    checks['grass_preserved']=float((grass>.5).sum())>0
    sign=next(a for a in pit['assets'] if a['id']=='bithlo_sticker_stop')
    oldsign=next(a for a in read(R/'V023_SOURCE/pit_facilities.json')['assets'] if a['id']=='bithlo_sticker_stop')
    checks['approved_stop_sign_unchanged']=sign==oldsign

    report=dict(
      version='v024',scope=['T05 sweeping hill','T06 smoother right','T13 right-fade into rollers'],
      checks=checks,all_checks_pass=all(checks.values()),
      T05=dict(v023=bo['T05'],v024=t05,hill=h,encoded_elevation_m=elev.tolist(),encoded_peak_above_endpoint_chord_m=float(elev[1]-chord[1])),
      T06=dict(v023=bo['T06'],v024=t06),
      T13=dict(v023=bo['T13'],v024=t13,route_adjustment=adj[0],measured_max_right_shift_m=float(-lateral[zone].min())),
      R07_preserved=pn['R07']==po['R07'],R10_preserved=pn['R10']==po['R10'],T09_preserved=bn['T09']==bo['T09'],
      reference_context='v023 ride footage plus Orlando MX GoPro ~43s/51s reference and user-marked screenshots',
      native_compilation=False,in_game_riding=False)
    save(R/'DOCUMENTATION/v024_user_request_validation.json',report)
    print(json.dumps(report,indent=2))
    if not report['all_checks_pass']:raise RuntimeError('v024 user-request QA failed: '+str([k for k,v in checks.items() if not v]))
if __name__=='__main__':main()
