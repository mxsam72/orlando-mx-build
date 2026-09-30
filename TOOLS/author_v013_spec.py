"""Validate the user-authored v013 obstacle specification.

v013 is authored directly in V013_SOURCE/v013_geometry_spec.json from the
September 29 v012 ride-test feedback. This tool deliberately validates instead
of regenerating the file so it cannot silently restore obsolete v012 geometry.
"""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
P=R/'V013_SOURCE/v013_geometry_spec.json'

def main():
    spec=json.loads(P.read_text(encoding='utf-8'))
    p={x['id']:x for x in spec['profiles']}
    expected={
        'R01':('TABLETOP',51.4666666667),
        'R02':('TRIPLE',54.0),
        'R03':('TABLE_SINGLE',50.0),
        'R05':('DOUBLE',24.0),
        'R07':('ANT_HILL',22.0),
        'R09':('DOUBLE',50.0),
        'R10':('TABLETOP',75.0),
        'R12':('ROLLER_SEQUENCE',40.0),
        'R14':('TRIPLE',55.0),
        'R17':('ROLLER_SEQUENCE',80.0),
        'R18':('INSIDE_ROLLER',18.0),
    }
    for k,(kind,length) in expected.items():
        assert p[k]['target_type']==kind,(k,p[k]['target_type'],kind)
        assert abs(p[k]['user_target_length_m']-length)<1e-5,(k,p[k]['user_target_length_m'],length)
    assert abs(p['R05']['station_start_m']-384.6)<1e-6
    assert p['R12']['roller_count']==4 and abs(p['R12']['spacing_m']-10.0)<1e-6
    assert p['R17']['roller_count']==8 and abs(p['R17']['spacing_m']-10.0)<1e-6
    assert abs(p['R18']['lateral_offset_m']-3.4)<1e-6
    print('v013 authoritative spec validated:', ', '.join(expected))

if __name__=='__main__': main()
