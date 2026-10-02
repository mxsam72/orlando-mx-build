"""v022 targeted user-request QA: R07, R10 and T09 only."""
import json, math
import numpy as np
from scipy.ndimage import label
from v022_common import *
from jump_v022 import make_profile
from pit_roads_v022 import road_field, grass_field

def strip_version(obj):
    if isinstance(obj,dict):
        return {k:strip_version(v) for k,v in obj.items() if k not in ['version','metric_status','notes']}
    if isinstance(obj,list):return [strip_version(v) for v in obj]
    return obj

def main():
    now=read(S/'v022_geometry_spec.json')
    old=read(R/'V021_SOURCE/v021_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};po={p['id']:p for p in old['profiles']}
    bn={b['id']:b for b in now['berms']};bo={b['id']:b for b in old['berms']}
    npf={k:make_profile(v) for k,v in pn.items()};opf={k:make_profile(v) for k,v in po.items()}

    checks={}
    for rid in pn:
        if rid not in ['R07','R10']:
            checks['preserve_'+rid]=pn[rid]==po[rid]
    for tid in bn:
        if tid!='T09':
            checks['preserve_'+tid]=bn[tid]==bo[tid]

    r07=pn['R07'];r10=pn['R10'];t09=bn['T09']
    checks['R07_shorter_than_v021']=r07['user_target_length_m']<po['R07']['user_target_length_m']
    checks['R07_lower_peak_than_v021']=r07['crest_height_m']<po['R07']['crest_height_m']
    checks['R07_progressive_face']=r07.get('face_style')=='progressive_lip'
    checks['R07_crest_station_preserved']=abs(r07['lip_s']-po['R07']['lip_s'])<1e-9
    checks['R07_upper_face_steeper']=npf['R07']['takeoff_angle_deg']>opf['R07']['takeoff_angle_deg']
    checks['R07_reduced_side_mass']=r07['wide_support_extra_m']<po['R07']['wide_support_extra_m'] and r07['side_taper_m']<po['R07']['side_taper_m']

    checks['R10_lip_station_preserved']=abs(r10['lip_s']-po['R10']['lip_s'])<1e-9
    checks['R10_landing_end_preserved']=abs(r10['station_end_m']-po['R10']['station_end_m'])<1e-9
    checks['R10_face_shorter']=r10['face_m']<po['R10']['face_m']
    checks['R10_lip_higher']=r10['crest_height_m']>po['R10']['crest_height_m']
    checks['R10_lip_rounding_shorter']=r10['lip_transition_m']<po['R10']['lip_transition_m']
    checks['R10_takeoff_much_steeper']=npf['R10']['takeoff_angle_deg']>opf['R10']['takeoff_angle_deg']+5.0
    checks['R10_clear_settle_after_R09']=r10['station_start_m']>=pn['R09']['station_end_m']+1.5

    checks['T09_narrower_active_width']=t09['effective_width_m']<bo['T09']['effective_width_m']
    checks['T09_outer_wall_stronger']=t09['outer_rise_m']>bo['T09']['outer_rise_m']
    checks['T09_deeper_pocket']=t09['pocket_depth_m']>bo['T09']['pocket_depth_m']
    checks['T09_deeper_ruts']=t09['rut_depth_m']>bo['T09']['rut_depth_m']
    checks['T09_outer_rut_more_defined']=t09['rut_paths'][1]['depth_scale']>bo['T09']['rut_paths'][1]['depth_scale'] and t09['rut_paths'][1]['width_m']<bo['T09']['rut_paths'][1]['width_m']

    # Everything outside geometry spec is intentionally unchanged from v021.
    checks['facilities_unchanged']=read(S/'facilities.json')==read(R/'V021_SOURCE/facilities.json')
    checks['start_layout_unchanged']=read(S/'start_layout.json')==read(R/'V021_SOURCE/start_layout.json')
    checks['pit_facilities_unchanged']=strip_version(read(S/'pit_facilities.json'))==strip_version(read(R/'V021_SOURCE/pit_facilities.json'))
    checks['vehicles_unchanged']=strip_version(read(S/'vehicles.json'))==strip_version(read(R/'V021_SOURCE/vehicles.json'))

    pit=read(S/'pit_facilities.json')
    roads=road_field((768,768));grass=grass_field((768,768))
    _,count=label(roads>.30)
    checks['pit_road_network_still_connected']=int(count)==1
    checks['grass_preserved']=float((grass>.5).sum())>0
    sign=next(a for a in pit['assets'] if a['id']=='bithlo_sticker_stop')
    oldsign=next(a for a in read(R/'V021_SOURCE/pit_facilities.json')['assets'] if a['id']=='bithlo_sticker_stop')
    checks['approved_stop_sign_unchanged']=sign==oldsign

    report={
        'version':'v022',
        'scope':['R07','R10','T09'],
        'checks':checks,
        'all_checks_pass':all(checks.values()),
        'R07':{
            'v021_length_m':po['R07']['user_target_length_m'],'v022_length_m':r07['user_target_length_m'],
            'v021_height_m':po['R07']['crest_height_m'],'v022_height_m':r07['crest_height_m'],
            'v021_takeoff_deg':opf['R07']['takeoff_angle_deg'],'v022_takeoff_deg':npf['R07']['takeoff_angle_deg'],
            'face_style':r07.get('face_style')
        },
        'R10':{
            'v021_start_m':po['R10']['station_start_m'],'v022_start_m':r10['station_start_m'],
            'lip_station_m':r10['lip_s'],'landing_end_m':r10['station_end_m'],
            'v021_face_m':po['R10']['face_m'],'v022_face_m':r10['face_m'],
            'v021_height_m':po['R10']['crest_height_m'],'v022_height_m':r10['crest_height_m'],
            'v021_takeoff_deg':opf['R10']['takeoff_angle_deg'],'v022_takeoff_deg':npf['R10']['takeoff_angle_deg']
        },
        'T09':{
            'v021':bo['T09'],'v022':t09
        },
        'native_compilation':False,'in_game_riding':False
    }
    save(R/'DOCUMENTATION/v022_user_request_validation.json',report)
    print(json.dumps(report,indent=2))
    if not report['all_checks_pass']:
        raise RuntimeError('v022 user-request QA failed: '+str([k for k,v in checks.items() if not v]))

if __name__=='__main__':
    main()
