"""Write the four checkpoint groups of authoritative obstacle source data."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
def main(group):
    path=R/'V013_SOURCE/v013_geometry_spec.json';spec=json.loads(path.read_text());old={p['id']:p for p in json.loads((R/'V011_SOURCE/v011_geometry_spec.json').read_text())['profiles']}
    def feature(id,kind,start,length,F,H,land,**extra):
        p=dict(id=id,kind=kind,target_type=kind.upper(),station_start_m=start,station_end_m=start+length,user_target_length_m=length,face_m=F,face_length_m=F,crest_height_m=H,lip_height_m=H,landing_m=land,landing_length_m=land,lip_s=start+F,racing_width_m=10.,side_taper_m=7.5,face_progression=.5,lower_face_grade_ratio=.6,lip_transition_m=.8,deck_m=0.,gaps=[],notes='User-authoritative v013 target; metric shaping estimates')
        p.update(extra);p['gap_length_m']=sum(g['span_m'] for g in p['gaps']);p['role']=p['notes'];p['evidence']='v013 handover supersedes v011 classification';return p
    def gap(span,low,height):return dict(span_m=span,valley_height_m=low,landing_crest_height_m=height)
    def none(id):
        p=old[id];length=p['face_m']+p.get('lip_transition_m',p['rollover_m'])+p.get('deck_m',p.get('crest_bridge_m',0))+p['landing_m']
        return feature(id,'none',p['lip_s']-p['face_m'],length,p['face_m'],0,length-p['face_m'],user_target_length_m=None,notes='NO JUMP: remove previous obstacle; retain corner/normal ground')
    groups={
     'A':[
        feature('R01','tabletop',-2.,77.2,12.5,2.8,18.,lip_transition_m=1.1,deck_m=45.6,racing_width_m=10.8,notes='Long front tabletop: twice v011 raised-earthwork length (38.6 m); zero-height padding excluded'),
        feature('R02','triple',128.,40.,8.,2.6,12.5,gaps=[gap(9,.30,2.25),gap(9.7,.30,2.4)],notes='Big triple: 8 m face + 0.8 lip + 9 / 9.7 gaps + 12.5 landing = 40 m'),
        feature('R03','table_single',232.,35.,9.,2.6,9.2,deck_m=7.,gaps=[gap(9,.35,2.3)],notes='Table-single: 9 face + 0.8 lip + 7 deck + 9 gap to separate single + 9.2 landing = 35 m'),
        none('R04'),
        feature('R05','double',424.6,12.,3.2,.70,3.4,lip_transition_m=.6,gaps=[gap(4.8,.07,.60)],notes='Low 12 m double ending 2 m before T05 arc entry')],
     'B':[
        none('R06'),
        feature('R07','ant_hill',542.,21.,10.,2.8,11.,notes='One ant-hill crest at s552, the former R07 double landing; remove old takeoff and gap'),
        none('R08'),
        feature('R09','double',696.2,25.,6.8,2.4,7.4,gaps=[gap(10,.25,2.2)],notes='Big 25 m double with independent takeoff and landing'),
        feature('R10','tabletop',746.,50.,13.,3.3,19.,lip_transition_m=1.,deck_m=17.,notes='50 m tabletop: 13 face + 1 lip + 17 deck + 19 landing')],
     'C':[
        feature('R11','double',844.,20.,4.5,.5,5.,lip_transition_m=.6,gaps=[gap(9.9,.05,.45)],notes='20 m low-lipped double; shallow speed-dependent launch'),
        feature('R12','roller_sequence',868.5,20.,2.5,.55,2.5,roller_count=4,spacing_m=5.,roller_heights_m=[.45,.50,.55,.45],notes='Four rolling singles with crests at s871,876,881,886'),
        none('R13'),
        feature('R14','triple',981.,35.,8.,3.2,8.2,gaps=[gap(9,.55,2.7),gap(9,.55,3.)],notes='35 m signature triple: 8 face + .8 lip + 9 / 9 gaps + 8.2 landing')],
     'D':[
        feature('R15','single',1089.5,23.,10.5,.8,12.5,notes='Preserve v011 R15 rounded single dimensions and location'),
        feature('R16','tabletop',1126.8,46.3,10.2,2.7,14.,lip_transition_m=1.1,deck_m=21.,notes='Replace double with tabletop; 46.3 m vs v011 41.3 m, exactly 5 m longer'),
        feature('R17','roller_sequence',1287.5,40.,2.5,.55,2.5,roller_count=8,spacing_m=5.,roller_heights_m=[.40,.48,.52,.55,.55,.52,.48,.40],notes='Eight distinct rollers at 5 m crest spacing, s1290 through s1325'),
        feature('R18','inside_roller',1352.,6.,3.,.5,3.,lateral_offset_m=3.4,racing_width_m=2.2,side_taper_m=.8,notes='Inside left option into T14 only; center/main line free; no R18 obstacle at former straight station s1324')]
    }
    profiles={p['id']:p for p in spec['profiles']}
    for p in groups[group]:profiles[p['id']]=p
    spec['profiles']=[profiles[k] for k in sorted(profiles)];spec['completed_groups']=sorted(set(spec.get('completed_groups',[])+[group]));path.write_text(json.dumps(spec,indent=2)+'\n')
    from jump_v013 import make_profile
    for p in groups[group]:q=make_profile(p);print(p['id'],p['kind'],q['authored_total_length_m'])
if __name__=='__main__':main(sys.argv[1])
