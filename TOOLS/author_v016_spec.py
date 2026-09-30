"""Validate the user-authored v016 obstacle specification."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];P=R/'V016_SOURCE/v016_geometry_spec.json'

def main():
    spec=json.loads(P.read_text(encoding='utf-8'));p={x['id']:x for x in spec['profiles']}
    assert abs(p['R07']['user_target_length_m']-32.78901315789474)<1e-6
    assert abs(p['R07']['crest_height_m']-5.535)<1e-6
    assert abs(p['R10']['station_start_m']-736.2)<1e-6
    assert abs(p['R10']['user_target_length_m']-75.0)<1e-6
    assert abs(p['R10']['crest_height_m']/p['R10']['face_m']-(3.3/19.5)*1.05)<1e-8
    assert abs(p['R11']['crest_height_m']-0.525)<1e-6
    assert abs(p['R11']['gaps'][0]['landing_crest_height_m']-0.4725)<1e-6
    assert abs(p['R18']['racing_width_m']-10.1)<1e-6
    print('v016 authoritative spec validated')
if __name__=='__main__':main()
