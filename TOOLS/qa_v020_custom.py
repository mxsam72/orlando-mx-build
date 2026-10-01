"""v020 user-request QA: obstacle deltas, bathroom facing, pit grass/road continuity and Bithlo sign."""
import math, json
import numpy as np
from scipy.ndimage import label
from v020_common import *
from jump_v020 import make_profile
from pit_roads_v020 import road_field, grass_field

def front_vector(heading_deg):
    t=math.radians(heading_deg)
    return np.array([math.sin(t), math.cos(t)],dtype=float)  # local +Z in world XZ

def main():
    now=read(S/'v020_geometry_spec.json')
    old=read(R/'V017_SOURCE/v017_geometry_spec.json')
    pn={p['id']:p for p in now['profiles']}; po={p['id']:p for p in old['profiles']}
    nprof={k:make_profile(v) for k,v in pn.items()}
    oprof={k:make_profile(v) for k,v in po.items()}

    checks={}
    checks['R07_shorter']=pn['R07']['user_target_length_m'] < po['R07']['user_target_length_m']
    checks['R07_steeper']=nprof['R07']['takeoff_angle_deg'] > oprof['R07']['takeoff_angle_deg']
    checks['R07_single_compact_mound']=pn['R07']['kind']=='ant_hill' and pn['R07']['deck_m']==0 and abs(pn['R07']['lip_s']-552.0)<1e-6
    checks['R10_takeoff_earlier']=pn['R10']['station_start_m'] < po['R10']['station_start_m']
    checks['R10_bigger']=pn['R10']['crest_height_m'] > po['R10']['crest_height_m'] and pn['R10']['user_target_length_m'] > po['R10']['user_target_length_m']
    checks['R10_steeper']=nprof['R10']['takeoff_angle_deg'] > oprof['R10']['takeoff_angle_deg']
    checks['R11_steeper']=nprof['R11']['takeoff_angle_deg'] > oprof['R11']['takeoff_angle_deg']

    pit=read(S/'pit_facilities.json')
    assets={a['id']:a for a in pit['assets']}
    bath=assets['restroom']; office=assets['office']; sign=assets['bithlo_sticker_stop']
    fence=np.asarray(read(S/'facilities.json')['fence_polyline_xz'],dtype=float)
    toward=fence.mean(0)-np.asarray(bath['xz'],dtype=float); toward/=np.linalg.norm(toward)
    fv=front_vector(bath['heading'])
    checks['bathroom_doors_face_spectator_fence']=float(fv@toward)>.75
    checks['signature_sign_near_office']=float(np.linalg.norm(np.asarray(sign['xz'])-np.asarray(office['xz'])))<10.0

    roads=road_field((768,768)); grass=grass_field((768,768))
    components,count=label(roads>.30)
    road_area=float((roads>.5).sum())*(600/767)**2
    grass_area=float((grass>.5).sum())*(600/767)**2
    checks['gravel_network_connected']=int(count)==1
    checks['expanded_grass_area']=grass_area>2500
    checks['road_area_material']=road_area>2500

    meshes=read(O/'facility_meshes.json')
    sign_meshes=[m for m in meshes if m['asset']=='bithlo_sticker_stop']
    checks['signature_sign_mesh_present']=len(sign_meshes)>=8
    mats=sorted(set(m['material'] for m in sign_meshes))
    checks['signature_sign_sticker_variety']=len(mats)>=7

    report={
      'version':'v020','checks':checks,'all_checks_pass':all(checks.values()),
      'R07':{'old_length_m':po['R07']['user_target_length_m'],'new_length_m':pn['R07']['user_target_length_m'],'old_takeoff_deg':oprof['R07']['takeoff_angle_deg'],'new_takeoff_deg':nprof['R07']['takeoff_angle_deg']},
      'R10':{'old_start_m':po['R10']['station_start_m'],'new_start_m':pn['R10']['station_start_m'],'old_height_m':po['R10']['crest_height_m'],'new_height_m':pn['R10']['crest_height_m'],'old_takeoff_deg':oprof['R10']['takeoff_angle_deg'],'new_takeoff_deg':nprof['R10']['takeoff_angle_deg']},
      'R11':{'old_takeoff_deg':oprof['R11']['takeoff_angle_deg'],'new_takeoff_deg':nprof['R11']['takeoff_angle_deg']},
      'bathroom_heading_deg':bath['heading'],'bathroom_front_dot_to_fence':float(fv@toward),
      'pit_road_area_m2':road_area,'pit_grass_area_m2':grass_area,'road_mask_components':int(count),
      'sign_asset_xz':sign['xz'],'sign_office_distance_m':float(np.linalg.norm(np.asarray(sign['xz'])-np.asarray(office['xz']))),
      'sign_mesh_count':len(sign_meshes),'sign_materials':mats,
      'native_compilation':False,'in_game_riding':False
    }
    save(R/'DOCUMENTATION/v020_user_request_validation.json',report)
    print(json.dumps(report,indent=2))
    if not report['all_checks_pass']:
        raise RuntimeError('v020 user-request QA failed: '+str([k for k,v in checks.items() if not v]))

if __name__=='__main__':
    main()
