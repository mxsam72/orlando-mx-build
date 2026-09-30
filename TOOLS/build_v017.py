"""Reproducible isolated v017 source build.
Generates unchanged support scripts from the tested v016 implementations, then
runs the v017-specific geometry, pit and QA stages.
"""
import argparse, subprocess, sys, os
from v017_common import *

def transformed(name):
    return (R/'TOOLS'/name).read_text(encoding='utf-8').replace('v016','v017').replace('V016','V017')

def materialize_runtime():
    simple=['build_v016_race.py','rebind_v016_scenery.py','facility_mesh_v016.py','append_facilities_v016.py',
            'prepare_v016_release.py','render_facilities_v016.py','render_v016_layout.py']
    for src in simple:
        dst=src.replace('v016','v017');(R/'TOOLS'/dst).write_text(transformed(src),encoding='utf-8')

    q=transformed('qa_v016_layout.py')
    start=q.index("    b=np.array(assets['restroom']['xz']")
    end=q.index("    save(R/'DOCUMENTATION/v017_layout_validation.json'",start)
    rel="""    b=np.array(assets['restroom']['xz'],dtype=float);truck=np.array(assets['pickup_01']['xz'],dtype=float);canopy=np.array(assets['canopy_02']['xz'],dtype=float)
    bathroom_to_truck=float(np.linalg.norm(b-truck));bathroom_to_canopy=float(np.linalg.norm(b-canopy))
    patch=next(p for p in pit['grass_patches'] if p['id']=='lower_redtruck_restroom_grass')
    x0,z0,x1,z1=map(float,patch['bounds_xz']);bathroom_in_grass=bool(x0<b[0]<x1 and z0<b[1]<z1)
    road_clear=float('inf')
    for road in pit['roads']:
        pts=np.asarray(road['points'],dtype=float)
        for aa,bb in zip(pts[:-1],pts[1:]):
            d=bb-aa;t=np.clip((b-aa)@d/(d@d),0,1);dist=np.linalg.norm(b-(aa+t*d))-road['width']/2
            road_clear=min(road_clear,float(dist))
    qa=dict(start_length_m=float(sa[-1,3]),gate_stalls=cfg['grid_stalls'],grid_outer_stall_span_m=23*cfg['stall_spacing_m'],gate_apron_width_m=cfg['start_width_knots'][0][1],minimum_start_width_m=float(sw.min()),minimum_other_lane_edge_clearance_m=float(clear.min()),self_crossings=cross,merge_station_m=cfg['merge_station_m'],right_turn='T06',right_turn_angle_deg=t6['angle'],distance_before_right_turn_m=t6['arc_start']-cfg['merge_station_m'],bathroom_distance_from_lower_red_truck_m=bathroom_to_truck,bathroom_distance_from_lower_canopy_m=bathroom_to_canopy,bathroom_in_grass_patch=bathroom_in_grass,bathroom_road_edge_clearance_m=road_clear,office_left_of_frontage_truck=assets['office']['xz'][0]<assets['pickup_03']['xz'][0],office_view_direction='+Z from pit road toward spectator fence',outside_shoulder_note='Start loop unchanged from v016.',runtime_start_reset_and_timing='Pending in-game test')
    qa['layout_checks_pass']=bool(clear.min()>.5 and not cross and 0<t6['arc_start']-cfg['merge_station_m']<8 and t6['angle']<0 and bathroom_to_truck<13 and bathroom_to_canopy<14 and bathroom_in_grass and road_clear>.5 and qa['office_left_of_frontage_truck'])
"""
    q=q[:start]+rel+q[end:]
    q=q.replace("('restroom','Bathroom beside red truck',(-110,-35)),('pickup_02','Red truck',(8,-22)),('canopy_01','Canopy',(10,16)),('rv_02','Camper / RV',(10,-20))",
                "('restroom','Bathroom · opposite road',(-95,-38)),('pickup_01','Other red truck',(-62,-22)),('canopy_02','Canopy',(-10,15)),('rv_02','Camper / RV',(10,-20))")
    (R/'TOOLS/qa_v017_layout.py').write_text(q,encoding='utf-8')

    pr=transformed('pit_roads_v016.py')
    pr=pr.replace("rgb=np.clip(np.array([184,179,163])+n[...,None],0,255).astype('uint8');Image.fromarray(rgb).save(O/'v017_pit_sand.tga')",
"""base=np.array([194,188,174],dtype=float);rgb=np.clip(base+n[...,None]*1.35,0,255).astype('uint8')
    rr=np.random.default_rng(17017);yy=rr.integers(0,256,5000);xx=rr.integers(0,256,5000);fleck=rr.integers(-24,25,5000)
    for k in range(len(xx)):rgb[yy[k],xx[k]]=np.clip(rgb[yy[k],xx[k]].astype(int)+fleck[k],0,255)
    Image.fromarray(rgb).save(O/'v017_pit_gravel.tga')""")
    pr=pr.replace("O/'v017_pit_sand.tga'","O/'v017_pit_gravel.tga'")
    pr=pr.replace("print('Pit roads and RV/restroom grass paddock prepared')","print('Restored gravel roads and correct opposite-road bathroom grass paddock prepared')")
    (R/'TOOLS/pit_roads_v017.py').write_text(pr,encoding='utf-8')

    bw=transformed('build_windows_v016.py')
    bw=bw.replace("shutil.copy2(O/'v017_pit_sand.tga',p/'v017_pit_sand.tga')","shutil.copy2(O/'v017_pit_gravel.tga',p/'v017_pit_gravel.tga')")
    bw=bw.replace("map = v017_pit_sand.tga","map = v017_pit_gravel.tga").replace("repetitions = 80","repetitions = 95")
    (R/'TOOLS/build_windows_v017.py').write_text(bw,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');args=ap.parse_args()
    materialize_runtime()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')
    scripts=['materialize_v009_baseline.py','rebuild_v009_geometry.py','v017_common.py','rebuild_v017_geometry.py','qa_v017_geometry.py','build_v017_start_terrain.py','build_v017_race.py','rebind_v017_scenery.py','facility_mesh_v017.py','qa_v017_layout.py','append_facilities_v017.py','prepare_v017_release.py','pit_roads_v017.py','render_facilities_v017.py','render_v017_layout.py']
    for script in scripts:
        print('RUN',script,flush=True);subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,env=env,check=True)
    save(R/'DOCUMENTATION/v017_source_checkpoint.json',dict(version='v017',source_commit=os.environ.get('GITHUB_SHA','local'),geometry_spec_sha256=sha(S/'v017_geometry_spec.json'),facilities_spec_sha256=sha(S/'facilities.json'),source_checks_pass=True,native_compilation=False,in_game_riding=False,raw_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),start_tcl_sha256=sha(O/'start.tcl'),rdf_sha256=sha(O/(NAME+'.rdf'))))
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v017.py')],cwd=R,env=env,check=True)
if __name__=='__main__':main()
