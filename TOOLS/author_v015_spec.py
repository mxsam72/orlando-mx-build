"""Validate the user-authored v015 obstacle specification."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];P=R/'V015_SOURCE/v015_geometry_spec.json'

def main():
    spec=json.loads(P.read_text(encoding='utf-8'));p={x['id']:x for x in spec['profiles']}
    expected={'R02':49.0,'R05':29.0,'R09':60.0,'R10':65.0,'R11':20.0,'R12':35.0,'R14':55.0,'R16':46.3,'R18':18.0}
    for k,v in expected.items():assert abs(p[k]['user_target_length_m']-v)<1e-5,(k,p[k]['user_target_length_m'],v)
    assert abs(p['R05']['station_start_m']-399.6)<1e-6
    assert abs(p['R11']['station_start_m']-839.0)<1e-6
    assert abs(p['R14']['station_start_m']-951.0)<1e-6
    assert abs(p['R16']['station_start_m']-1116.8)<1e-6
    assert p['R12']['crest_spacings_m']==[10.0,10.0,5.0]
    assert abs(p['R18']['racing_width_m']-5.6)<1e-6
    assert abs(p['R07']['crest_height_m']-8.2)<1e-6
    print('v015 authoritative spec validated')
if __name__=='__main__':main()
