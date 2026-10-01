"""Reproducible isolated Orlando MX v021 mirrored-graphics correction.

Base: validated/delivered v020. The ONLY intended visible change is horizontal
orientation correction for readable vehicle/bike decals reported mirrored
in-game: Premier Power wrap, Ford/4x4/King Ranch markings, Chevy badge, and all
bike number/shroud graphics. The accepted Bithlo sign and all v020 geometry,
placements, terrain, start/race data and pit layout remain protected.
"""
import argparse, subprocess, sys, os
from v021_common import *

def transformed(name):
    return (R/'TOOLS'/name).read_text(encoding='utf-8').replace('v016','v021').replace('V016','V021')

def materialize_runtime():
    simple=['build_v016_race.py','rebind_v016_scenery.py','facility_mesh_v016.py','append_facilities_v016.py',
            'prepare_v016_release.py','render_facilities_v016.py','render_v016_layout.py']
    for src in simple:
        dst=src.replace('v016','v021')
        (R/'TOOLS'/dst).write_text(transformed(src),encoding='utf-8')

    # Facility patch: preserve corrected restroom, remove pickup_03 via source spec,
    # and replace the old chunky sign with a thin roadside assembly.
    fmp=R/'TOOLS/facility_mesh_v021.py'
    fm=fmp.read_text(encoding='utf-8')
    fm=fm.replace("'gravel':(174,169,153)}",
        "'gravel':(174,169,153),\n"
        "         'sticker_white':(240,239,229),'sticker_black':(24,25,24),'sticker_yellow':(226,201,60),\n"
        "         'sticker_blue':(45,98,153),'sticker_green':(77,133,73),'sticker_orange':(211,111,48),'sticker_pink':(184,83,123),'bithlo_photo':(220,220,220)}")
    legacy_restroom_side="""            else:
                for z in np.arange(-2,2.2,.18):s.box([-4.1,.9,z],[.13,1.8,.16],'timber')
                s.box([-3.5,.9,2.1],[1.3,1.8,.12],'timber')
"""
    if legacy_restroom_side not in fm:
        raise RuntimeError('legacy restroom side enclosure marker missing')
    fm=fm.replace(legacy_restroom_side,"""            else:
                # v021 preserves the compact corrected restroom body from v019.
                pass
""")
    marker="        elif typ in ['flagpole','utility']:"
    sign=r'''        elif typ=='sticker_stop_sign':
            # Thin metal assembly. Actual reference artwork is UV-mapped later.
            s.beam([0,0,-.035],[0,3.30,-.035],.029,'alloy',12)
            s.box([0,3.04,0],[1.47,.47,.018],'alloy')
            s.box([0,1.465,0],[.84,.67,.018],'alloy')
            octagon=[[-.205,2.805,.035],[.205,2.805,.035],[.495,2.515,.035],[.495,2.105,.035],[.205,1.815,.035],[-.205,1.815,.035],[-.495,2.105,.035],[-.495,2.515,.035]]
            vv=octagon+[[x,y,z-.018] for x,y,z in octagon]
            s.add(vv,[list(range(8)),list(range(15,7,-1))]+[[k,(k+1)%8,(k+1)%8+8,k+8] for k in range(8)],'alloy')
            for y,w in [(2.88,1.40),(3.20,1.40),(1.23,.78),(1.70,.78)]:
                s.box([0,y,-.02],[w,.028,.020],'alloy')
'''
    if marker not in fm:
        raise RuntimeError('facility sign injection marker missing')
    fm=fm.replace(marker,sign+marker)
    fmp.write_text(fm,encoding='utf-8')

    # Layout QA: preserve v019 start/restroom relationships but explicitly validate
    # the user-authorized pickup removal and relocated sign.
    q=transformed('qa_v016_layout.py')
    start=q.index("    b=np.array(assets['restroom']['xz']")
    end=q.index("    save(R/'DOCUMENTATION/v021_layout_validation.json'",start)
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
    sign_asset=assets['bithlo_sticker_stop']
    qa=dict(start_length_m=float(sa[-1,3]),gate_stalls=cfg['grid_stalls'],grid_outer_stall_span_m=23*cfg['stall_spacing_m'],gate_apron_width_m=cfg['start_width_knots'][0][1],minimum_start_width_m=float(sw.min()),minimum_other_lane_edge_clearance_m=float(clear.min()),self_crossings=cross,merge_station_m=cfg['merge_station_m'],right_turn='T06',right_turn_angle_deg=t6['angle'],distance_before_right_turn_m=t6['arc_start']-cfg['merge_station_m'],bathroom_distance_from_lower_red_truck_m=bathroom_to_truck,bathroom_distance_from_lower_canopy_m=bathroom_to_canopy,bathroom_in_grass_patch=bathroom_in_grass,bathroom_road_edge_clearance_m=road_clear,generic_pickup_03_removed='pickup_03' not in assets,bithlo_sign_xz=sign_asset['xz'],office_view_direction='+Z from pit road toward spectator fence',outside_shoulder_note='Start loop unchanged from v017.',runtime_start_reset_and_timing='Pending in-game test')
    qa['layout_checks_pass']=bool(clear.min()>.5 and not cross and 0<t6['arc_start']-cfg['merge_station_m']<8 and t6['angle']<0 and bathroom_to_truck<14.5 and bathroom_to_canopy<14.5 and bathroom_in_grass and road_clear>.5 and qa['generic_pickup_03_removed'] and sign_asset['xz']==[278.0,142.0])
"""
    q=q[:start]+rel+q[end:]
    q=q.replace("PALETTE[m['material']]","PALETTE.get(m['material'],(128,128,128))")
    q=q.replace("('office','Office: left of frontage truck',(-63,28)),('pickup_03','Red frontage truck',(6,-27)),","('office','Office',(-63,28)),")

    q=q.replace("('restroom','Bathroom beside red truck',(-110,-35)),('pickup_02','Red truck',(8,-22)),('canopy_01','Canopy',(10,16)),('rv_02','Camper / RV',(10,-20))",
                "('restroom','Bathroom · opposite road',(-95,-38)),('pickup_01','Other red truck',(-62,-22)),('canopy_02','Canopy',(-10,15)),('rv_02','Camper / RV',(10,-20))")
    q=q.replace("('pickup_03','Red frontage truck',(6,-27)),","")
    q=q.replace("Office: left of frontage truck","Office / sign-in")
    (R/'TOOLS/qa_v021_layout.py').write_text(q,encoding='utf-8')

    # Preserve the validated v019 connected gravel network.
    pr=transformed('pit_roads_v016.py')
    pr=pr.replace("rgb=np.clip(np.array([184,179,163])+n[...,None],0,255).astype('uint8');Image.fromarray(rgb).save(O/'v021_pit_sand.tga')",
"""base=np.array([194,188,174],dtype=float);rgb=np.clip(base+n[...,None]*1.35,0,255).astype('uint8')
    rr=np.random.default_rng(17017);yy=rr.integers(0,256,5000);xx=rr.integers(0,256,5000);fleck=rr.integers(-24,25,5000)
    for k in range(len(xx)):rgb[yy[k],xx[k]]=np.clip(rgb[yy[k],xx[k]].astype(int)+fleck[k],0,255)
    Image.fromarray(rgb).save(O/'v021_pit_gravel.tga')""")
    pr=pr.replace("O/'v021_pit_sand.tga'","O/'v021_pit_gravel.tga'")
    pr=pr.replace("print('Pit roads and RV/restroom grass paddock prepared')",
                  "print('v021 connected gravel loop and expanded grass paddocks preserved')")
    (R/'TOOLS/pit_roads_v021.py').write_text(pr,encoding='utf-8')

    # Native build: same validated v016-v019 toolchain, with v021 gravel, logo,
    # and explicit compiled-EDF texture checks.
    bw=transformed('build_windows_v016.py')
    bw=bw.replace("shutil.copy2(O/'v021_pit_sand.tga',p/'v021_pit_sand.tga')",
                  "shutil.copy2(O/'v021_pit_gravel.tga',p/'v021_pit_gravel.tga')")
    bw=bw.replace("map = v021_pit_sand.tga","map = v021_pit_gravel.tga").replace("repetitions = 80","repetitions = 95")
    bw=bw.replace("    orig_stage=ns['stage']",
"""    from logo_v021 import main as preserve_logo
    preserve_logo()
    assert sha(R/'12_RELEASE'/NAME/(NAME+'.tga'))==read(S/'v018_invariants.json')['menu_preview_tga_sha256']
    orig_stage=ns['stage']""")
    oldtry="    try:ns['main']()\n    except Exception as e:"
    newtry="""    try:
        ns['main']()
        from validate_native_textures_v021 import verify_files
        meshes=read(O/'vehicle_meshes.json')+read(O/'sign_graphic_meshes.json');used=sorted({m['material'] for m in meshes})
        textures=[O/'facility_textures'/('v021_vehicle_'+name+'.tga') for name in used]
        verify_files(R/'BUILD/v009_work/08_OBJECTS_GAME/scenery.edf',
                     R/'12_RELEASE'/NAME/(NAME+'.map'),textures,
                     R/'DOCUMENTATION/v021_native_texture_validation.json')
    except Exception as e:"""
    if oldtry not in bw:raise RuntimeError('native try block marker missing')
    bw=bw.replace(oldtry,newtry)
    bw=bw.replace("native.update(version='v021',",
        "native.update(version='v021',source_commit=os.environ.get('GITHUB_SHA','local'),vehicle_validation=read(R/'DOCUMENTATION/v021_vehicle_validation.json'),menu_logo_validation=read(R/'DOCUMENTATION/v021_menu_logo_validation.json'),v018_invariants=read(R/'DOCUMENTATION/v021_invariants_validation.json'),native_texture_validation=read(R/'DOCUMENTATION/v021_native_texture_validation.json'),")
    bw=bw.replace('obstacle and layout correction candidate',
                  'v021 corrected non-mirrored vehicle and bike graphics candidate')
    bw=bw.replace('Review all R01-R18 features against the supplied checklist and confirm the facility colors in game.',
                  'Confirm Premier Power wrap, Ford/4x4/King Ranch markings and all bike number/shroud graphics read normally in game. The Bithlo sign and all v020 geometry/placements are intentionally unchanged.')
    (R/'TOOLS/build_windows_v021.py').write_text(bw,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-only',action='store_true')
    args=ap.parse_args()
    materialize_runtime()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')
    scripts=[
        'materialize_v009_baseline.py','rebuild_v009_geometry.py',
        'v021_common.py','rebuild_v021_geometry.py','qa_v021_geometry.py',
        'build_v021_start_terrain.py','build_v021_race.py','rebind_v021_scenery.py',
        'facility_mesh_v021.py','qa_v021_layout.py','append_facilities_v021.py',
        'vehicle_textures_v021.py','sign_graphics_v021.py','model_vehicles_v021.py','qa_vehicles_v021.py','qa_graphics_v021.py',
        'append_vehicles_v021.py','prepare_v021_release.py','pit_roads_v021.py',
        'qa_v021_custom.py','logo_v021.py',
        'render_facilities_v021.py','render_v021_layout.py','render_vehicles_v021.py',
        'finalize_source_v021.py'
    ]
    for script in scripts:
        print('RUN',script,flush=True)
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,env=env,check=True)
    save(R/'DOCUMENTATION/v021_source_checkpoint.json',dict(
        version='v021',source_commit=os.environ.get('GITHUB_SHA','local'),
        geometry_spec_sha256=sha(S/'v021_geometry_spec.json'),
        facilities_spec_sha256=sha(S/'facilities.json'),
        pit_spec_sha256=sha(S/'pit_facilities.json'),
        vehicle_spec_sha256=sha(S/'vehicles.json'),
        vehicle_validation_sha256=sha(R/'DOCUMENTATION/v021_vehicle_validation.json'),
        graphics_validation_sha256=sha(R/'DOCUMENTATION/v021_graphics_validation.json'),
        menu_logo_validation_sha256=sha(R/'DOCUMENTATION/v021_menu_logo_validation.json'),
        user_request_validation_sha256=sha(R/'DOCUMENTATION/v021_user_request_validation.json'),
        source_checks_pass=True,native_compilation=False,in_game_riding=False,
        raw_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
        start_tcl_sha256=sha(O/'start.tcl'),rdf_sha256=sha(O/(NAME+'.rdf'))))
    if not args.source_only:
        subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v021.py')],cwd=R,env=env,check=True)

if __name__=='__main__':
    main()

