"""v023 targeted QA: revert T09; retune T13 flow and T06 bank before R07."""
import json
from scipy.ndimage import label
from v023_common import *
from jump_v023 import make_profile
from pit_roads_v023 import road_field, grass_field

def main():
    now=read(S/'v023_geometry_spec.json')
    v22=read(R/'V022_SOURCE/v022_geometry_spec.json')
    v21=read(R/'V021_SOURCE/v021_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']};p22={p['id']:p for p in v22['profiles']}
    bn={b['id']:b for b in now['berms']};b22={b['id']:b for b in v22['berms']};b21={b['id']:b for b in v21['berms']}
    checks={}

    # Preserve the successful v022 jump work exactly.
    for rid in pn:
        checks['preserve_'+rid]=pn[rid]==p22[rid]
    # Only T06, T09 and T13 may change among corners.
    for tid in bn:
        if tid not in ['T06','T09','T13']:
            checks['preserve_'+tid]=bn[tid]==b22[tid]

    # User explicitly requested the post-R10 corner back to the old v021 shape.
    checks['T09_exact_v021_revert']=bn['T09']==b21['T09']

    # T13: the left into the rollers should not hook inward as sharply; widen
    # its usable envelope and keep the outer line farther right through exit.
    t13=bn['T13'];o13=b22['T13']
    checks['T13_wider']=t13['effective_width_m']>o13['effective_width_m']
    checks['T13_softer_bank']=t13['entry_load']<o13['entry_load'] and t13['exit_load']<o13['exit_load']
    checks['T13_exit_fades_farther_right']=t13['rut_paths'][1]['exit_out_m']>o13['rut_paths'][1]['exit_out_m']+.8
    checks['T13_outer_line_broader']=t13['rut_paths'][1]['width_m']>o13['rut_paths'][1]['width_m']
    checks['T13_apex_later']=t13['apex_shift_m']>o13['apex_shift_m']

    # T06: user wants a visible bank that climbs then drops away before R07.
    t06=bn['T06'];o06=b22['T06']
    checks['T06_bank_higher']=t06['outer_rise_m']>o06['outer_rise_m']+.6
    checks['T06_wider']=t06['effective_width_m']>o06['effective_width_m']
    checks['T06_deeper_supported_pocket']=t06['pocket_depth_m']>o06['pocket_depth_m']
    checks['T06_bank_fades_before_R07']=t06['exit_load']<o06['exit_load']-.2
    checks['T06_outer_rut_supported']=t06['rut_paths'][1]['depth_scale']>=o06['rut_paths'][1]['depth_scale']

    # Pits/scenery specs remain unchanged from v022.
    checks['facilities_unchanged']=read(S/'facilities.json')==read(R/'V022_SOURCE/facilities.json')
    checks['start_layout_unchanged']=read(S/'start_layout.json')==read(R/'V022_SOURCE/start_layout.json')
    checks['pit_facilities_unchanged']=read(S/'pit_facilities.json')==read(R/'V022_SOURCE/pit_facilities.json')
    checks['vehicles_unchanged']=read(S/'vehicles.json')==read(R/'V022_SOURCE/vehicles.json')
    pit=read(S/'pit_facilities.json');roads=road_field((768,768));grass=grass_field((768,768));_,count=label(roads>.30)
    checks['pit_road_network_still_connected']=int(count)==1
    checks['grass_preserved']=float((grass>.5).sum())>0
    sign=next(a for a in pit['assets'] if a['id']=='bithlo_sticker_stop')
    oldsign=next(a for a in read(R/'V022_SOURCE/pit_facilities.json')['assets'] if a['id']=='bithlo_sticker_stop')
    checks['approved_stop_sign_unchanged']=sign==oldsign

    report={
      'version':'v023','scope':['T09 revert','T13 flow','T06 bank'],
      'checks':checks,'all_checks_pass':all(checks.values()),
      'T09':{'v022':b22['T09'],'v023':bn['T09'],'reverted_to_v021':bn['T09']==b21['T09']},
      'T13':{'v022':o13,'v023':t13},
      'T06':{'v022':o06,'v023':t06},
      'R07_preserved':pn['R07']==p22['R07'],'R10_preserved':pn['R10']==p22['R10'],
      'reference_context':'Current v022 ride footage checked against the same Orlando MX GoPro section mapping used previously.',
      'native_compilation':False,'in_game_riding':False
    }
    save(R/'DOCUMENTATION/v023_user_request_validation.json',report)
    print(json.dumps(report,indent=2))
    if not report['all_checks_pass']:
        raise RuntimeError('v023 user-request QA failed: '+str([k for k,v in checks.items() if not v]))

if __name__=='__main__':
    main()
