"""Validate the user-authored v016 obstacle specification."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];P=R/'V016_SOURCE/v016_geometry_spec.json'

def main():
    spec=json.loads(P.read_text(encoding='utf-8'));p={x['id']:x for x in spec['profiles']}
    expected={'R03':47.0,'R07':36.4322368421,'R09':50.0,'R10':70.0,'R14':55.0,'R16':43.3,'R17':80.0,'R18':18.0}
    for k,v in expected.items():assert abs(p[k]['user_target_length_m']-v)<1e-4,(k,p[k]['user_target_length_m'],v)
    assert abs(p['R03']['landing_m']-11.2)<1e-6
    assert abs(p['R07']['crest_height_m']-6.15)<1e-6
    assert abs(p['R09']['station_start_m']-691.2)<1e-6 and abs(p['R09']['crest_height_m']-3.456)<1e-6
    assert abs(p['R10']['station_start_m']-741.2)<1e-6 and abs(p['R10']['deck_m']-20.5)<1e-6
    assert abs(p['R14']['user_target_length_m']-55.0)<1e-6
    assert abs(p['R16']['deck_m']-18.0)<1e-6
    assert abs(p['R17']['station_start_m']-1257.5)<1e-6
    assert abs(p['R18']['racing_width_m']-7.1)<1e-6
    print('v016 authoritative spec validated')
if __name__=='__main__':main()
