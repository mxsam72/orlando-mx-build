"""Reproducible isolated v019 source build.
Generates unchanged support scripts from the tested v016 implementations, then
runs the v019-specific geometry, pit and QA stages.
"""
import argparse, subprocess, sys, os
from v019_common import *

def transformed(name):
    return (R/'TOOLS'/name).read_text(encoding='utf-8').replace('v016','v019').replace('V016','V019')

def materialize_runtime():
    simple=['build_v016_race.py','rebind_v016_scenery.py','facility_mesh_v016.py','append_facilities_v016.py',
            'prepare_v016_release.py','render_facilities_v016.py','render_v016_layout.py']
    for src in simple:
        dst=src.replace('v016','v019');(R/'TOOLS'/dst).write_text(transformed(src),encoding='utf-8')

    # Add the signature Bithlo sticker-covered stop-sign / number-board assembly.
    fmp=R/'TOOLS/facility_mesh_v019.py'
    fm=fmp.read_text(encoding='utf-8')
    fm=fm.replace("'gravel':(174,169,153)}","'gravel':(174,169,153),\n         'sticker_white':(240,239,229),'sticker_black':(24,25,24),'sticker_yellow':(226,201,60),\n         'sticker_blue':(45,98,153),'sticker_green':(77,133,73),'sticker_orange':(211,111,48),\n         'sticker_pink':(184,83,123)}")
    # The legacy restroom helper added a timber side enclosure extending well
    # beyond the actual building footprint. The supplied bathroom video shows
    # the compact building/front-door mass instead; remove that enclosure so it
    # neither distorts the silhouette nor conflicts with preserved pit spawns.
    legacy_restroom_side="""            else:
                for z in np.arange(-2,2.2,.18):s.box([-4.1,.9,z],[.13,1.8,.16],'timber')
                s.box([-3.5,.9,2.1],[1.3,1.8,.12],'timber')
"""
    if legacy_restroom_side not in fm: raise RuntimeError('legacy restroom side enclosure marker missing')
    fm=fm.replace(legacy_restroom_side,"""            else:
                # v019: no oversized side enclosure; keep the photo-derived compact restroom body.
                pass
""")
    marker="        elif typ in ['flagpole','utility']:"
    sign=r'''        elif typ=='sticker_stop_sign':
            # Photo-derived Bithlo landmark: tall stickered pole, lower number board,
            # octagonal STOP plate and upper street-sign plank.  Stickers are
            # deterministic small raised plaques rather than a flat generic sign.
            s.beam([0,0,0],[0,3.85,0],.065,'alloy',10)
            # upper aluminum road-name plank
            s.box([0,3.55,0],[2.55,.48,.09],'alloy')
            # lower rectangular number/sticker board
            s.box([0,1.45,0],[1.55,1.12,.10],'sticker_white')
            # stop octagon: white border behind red octagon, front faces local +Z
            def octagon(cy,r,z,mat):
                vv=[[math.cos(math.pi/8+k*math.pi/4)*r,cy+math.sin(math.pi/8+k*math.pi/4)*r,z] for k in range(8)]
                s.add(vv,[list(range(8))],mat)
            octagon(2.55,.78,.065,'sticker_white');octagon(2.55,.71,.080,'red')
            # sticker plaques, rotated in local XY; dense like the reference photos
            def plaque(cx,cy,w,h,ang,mat,z=.105):
                c=math.cos(ang);q=math.sin(ang);pts=[]
                for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:
                    pts.append([cx+dx*c-dy*q,cy+dx*q+dy*c,z])
                s.add(pts,[[0,1,2,3]],mat)
            rng=np.random.default_rng(18018)
            sticker_mats=['sticker_white','sticker_black','sticker_yellow','sticker_blue','sticker_green','sticker_orange','sticker_pink','red','navy']
            # stop-face collage
            for i in range(58):
                ang=rng.uniform(-.55,.55);cx=rng.uniform(-.52,.52);cy=2.55+rng.uniform(-.50,.50)
                # keep plaque centers inside octagonal body
                if abs(cx)+abs(cy-2.55)>.86: cx*=.72
                plaque(cx,cy,rng.uniform(.18,.42),rng.uniform(.10,.24),ang,sticker_mats[i%len(sticker_mats)],.110+i*1e-5)
            # lower board collage
            for i in range(48):
                plaque(rng.uniform(-.64,.64),1.45+rng.uniform(-.43,.43),rng.uniform(.16,.38),rng.uniform(.09,.21),rng.uniform(-.50,.50),sticker_mats[(i+3)%len(sticker_mats)],.111+i*1e-5)
            # top plank stickers and number plates
            for i in range(14):
                plaque(rng.uniform(-1.05,1.05),3.55+rng.uniform(-.13,.13),rng.uniform(.18,.42),rng.uniform(.09,.18),rng.uniform(-.25,.25),sticker_mats[(i+5)%len(sticker_mats)],.105+i*1e-5)
            # sticker bands down the pole
            for i,y in enumerate(np.linspace(.35,.92,8)):
                plaque(0,y,.18,.12,(i%3-1)*.15,sticker_mats[(i+1)%len(sticker_mats)],.085+i*1e-5)
'''
    if marker not in fm: raise RuntimeError('facility sign injection marker missing')
    fm=fm.replace(marker,sign+marker)
    fmp.write_text(fm,encoding='utf-8')

    q=transformed('qa_v016_layout.py')
    start=q.index("    b=np.array(assets['restroom']['xz']")
    end=q.index("    save(R/'DOCUMENTATION/v019_layout_validation.json'",start)
    rel="""    b=np.array(assets['restroom']['xz'],dtype=float);truck=np.array(assets['pickup_01']['xz'],dtype=float);canopy=np.array(assets['canopy_02']['xz'],dtype=float)
    bathroom_to_truck=float(np.linalg.norm(b-truck));bathroom_to_canopy=float(np.linalg.norm(b-canopy))
    patch=next(p for p in pit['grass_patches'] if p['id']=='lower_pit_parking_grass')
    x0,z0,x1,z1=map(float,patch['bounds_xz']);bathroom_in_grass=bool(x0<b[0]<x1 and z0<b[1]<z1)
    road_clear=float('inf')
    for road in pit['roads']:
        pts=np.asarray(road['points'],dtype=float)
        for aa,bb in zip(pts[:-1],pts[1:]):
            d=bb-aa;t=np.clip((b-aa)@d/(d@d),0,1);dist=np.linalg.norm(b-(aa+t*d))-road['width']/2
            road_clear=min(road_clear,float(dist))
    qa=dict(start_length_m=float(sa[-1,3]),gate_stalls=cfg['grid_stalls'],grid_outer_stall_span_m=23*cfg['stall_spacing_m'],gate_apron_width_m=cfg['start_width_knots'][0][1],minimum_start_width_m=float(sw.min()),minimum_other_lane_edge_clearance_m=float(clear.min()),self_crossings=cross,merge_station_m=cfg['merge_station_m'],right_turn='T06',right_turn_angle_deg=t6['angle'],distance_before_right_turn_m=t6['arc_start']-cfg['merge_station_m'],bathroom_distance_from_lower_red_truck_m=bathroom_to_truck,bathroom_distance_from_lower_canopy_m=bathroom_to_canopy,bathroom_in_grass_patch=bathroom_in_grass,bathroom_road_edge_clearance_m=road_clear,office_left_of_frontage_truck=assets['office']['xz'][0]<assets['pickup_03']['xz'][0],office_view_direction='+Z from pit road toward spectator fence',outside_shoulder_note='Start loop unchanged from v017.',runtime_start_reset_and_timing='Pending in-game test')
    qa['layout_checks_pass']=bool(clear.min()>.5 and not cross and 0<t6['arc_start']-cfg['merge_station_m']<8 and t6['angle']<0 and bathroom_to_truck<14.5 and bathroom_to_canopy<14.5 and bathroom_in_grass and road_clear>.5 and qa['office_left_of_frontage_truck'])
"""
    q=q[:start]+rel+q[end:]
    q=q.replace("('restroom','Bathroom beside red truck',(-110,-35)),('pickup_02','Red truck',(8,-22)),('canopy_01','Canopy',(10,16)),('rv_02','Camper / RV',(10,-20))",
                "('restroom','Bathroom · opposite road',(-95,-38)),('pickup_01','Other red truck',(-62,-22)),('canopy_02','Canopy',(-10,15)),('rv_02','Camper / RV',(10,-20))")
    (R/'TOOLS/qa_v019_layout.py').write_text(q,encoding='utf-8')

    pr=transformed('pit_roads_v016.py')
    pr=pr.replace("rgb=np.clip(np.array([184,179,163])+n[...,None],0,255).astype('uint8');Image.fromarray(rgb).save(O/'v019_pit_sand.tga')",
"""base=np.array([194,188,174],dtype=float);rgb=np.clip(base+n[...,None]*1.35,0,255).astype('uint8')
    rr=np.random.default_rng(17017);yy=rr.integers(0,256,5000);xx=rr.integers(0,256,5000);fleck=rr.integers(-24,25,5000)
    for k in range(len(xx)):rgb[yy[k],xx[k]]=np.clip(rgb[yy[k],xx[k]].astype(int)+fleck[k],0,255)
    Image.fromarray(rgb).save(O/'v019_pit_gravel.tga')""")
    pr=pr.replace("O/'v019_pit_sand.tga'","O/'v019_pit_gravel.tga'")
    pr=pr.replace("print('Pit roads and RV/restroom grass paddock prepared')","print('v019 connected gravel loop and expanded grass paddocks prepared')")
    (R/'TOOLS/pit_roads_v019.py').write_text(pr,encoding='utf-8')

    bw=transformed('build_windows_v016.py')
    bw=bw.replace("shutil.copy2(O/'v019_pit_sand.tga',p/'v019_pit_sand.tga')","shutil.copy2(O/'v019_pit_gravel.tga',p/'v019_pit_gravel.tga')")
    bw=bw.replace("map = v019_pit_sand.tga","map = v019_pit_gravel.tga").replace("repetitions = 80","repetitions = 95")
    bw=bw.replace("    orig_stage=ns['stage']", "    from logo_v019 import main as preserve_logo\n    preserve_logo()\n    assert sha(R/'12_RELEASE'/NAME/(NAME+'.tga'))==read(S/'v018_invariants.json')['menu_preview_tga_sha256']\n    orig_stage=ns['stage']")
    bw=bw.replace("native.update(version='v019',", "native.update(version='v019',source_commit=os.environ.get('GITHUB_SHA','local'),vehicle_validation=read(R/'DOCUMENTATION/v019_vehicle_validation.json'),menu_logo_validation=read(R/'DOCUMENTATION/v019_menu_logo_validation.json'),v018_invariants=read(R/'DOCUMENTATION/v019_invariants_validation.json'),")
    bw=bw.replace('obstacle and layout correction candidate','owner vehicles and bikes pit scenery candidate')
    bw=bw.replace('Review all R01-R18 features against the supplied checklist and confirm the facility colors in game.','Review the four owner vehicles and bikes in the grass right of the flag/frontage pickup, and confirm wrap graphics, glass, bike numbers and ground contact in game. Terrain, start and race inputs match validated v018.')
    (R/'TOOLS/build_windows_v019.py').write_text(bw,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');args=ap.parse_args()
    materialize_runtime()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')
    scripts=['materialize_v009_baseline.py','rebuild_v009_geometry.py','v019_common.py','rebuild_v019_geometry.py','qa_v019_geometry.py','build_v019_start_terrain.py','build_v019_race.py','rebind_v019_scenery.py','facility_mesh_v019.py','qa_v019_layout.py','append_facilities_v019.py','restore_vehicle_textures_v019.py','model_vehicles_v019.py','qa_vehicles_v019.py','append_vehicles_v019.py','prepare_v019_release.py','pit_roads_v019.py','qa_v019_custom.py','logo_v019.py','render_facilities_v019.py','render_v019_layout.py','render_vehicles_v019.py','finalize_source_v019.py']
    for script in scripts:
        print('RUN',script,flush=True);subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,env=env,check=True)
    save(R/'DOCUMENTATION/v019_source_checkpoint.json',dict(version='v019',source_commit=os.environ.get('GITHUB_SHA','local'),geometry_spec_sha256=sha(S/'v019_geometry_spec.json'),facilities_spec_sha256=sha(S/'facilities.json'),vehicle_spec_sha256=sha(S/'vehicles.json'),vehicle_validation_sha256=sha(R/'DOCUMENTATION/v019_vehicle_validation.json'),menu_logo_validation_sha256=sha(R/'DOCUMENTATION/v019_menu_logo_validation.json'),user_request_validation_sha256=sha(R/'DOCUMENTATION/v019_user_request_validation.json'),source_checks_pass=True,native_compilation=False,in_game_riding=False,raw_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),start_tcl_sha256=sha(O/'start.tcl'),rdf_sha256=sha(O/(NAME+'.rdf'))))
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v019.py')],cwd=R,env=env,check=True)
if __name__=='__main__':main()
