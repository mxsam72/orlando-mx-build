"""Reproducible isolated Orlando MX v020 asset-correction build.

Base: validated/delivered v019. Authorized v020 changes:
- realistic replacement geometry for all four bikes;
- PiBoSo-safe POT textures / native texture verification;
- improved Premier Power graphics;
- remove only generic pickup_03;
- relocate and rebuild the Bithlo sticker sign.
Track terrain, obstacle geometry, start/race layout, pit roads and accepted
Jordan/Sam/Shane vehicles remain protected.
"""
import argparse, subprocess, sys, os
from v020_common import *

def transformed(name):
    return (R/'TOOLS'/name).read_text(encoding='utf-8').replace('v016','v020').replace('V016','V020')

def materialize_runtime():
    simple=['build_v016_race.py','rebind_v016_scenery.py','facility_mesh_v016.py','append_facilities_v016.py',
            'prepare_v016_release.py','render_facilities_v016.py','render_v016_layout.py']
    for src in simple:
        dst=src.replace('v016','v020')
        (R/'TOOLS'/dst).write_text(transformed(src),encoding='utf-8')

    # Facility patch: preserve corrected restroom, remove pickup_03 via source spec,
    # and replace the old chunky sign with a thin roadside assembly.
    fmp=R/'TOOLS/facility_mesh_v020.py'
    fm=fmp.read_text(encoding='utf-8')
    fm=fm.replace("'gravel':(174,169,153)}",
        "'gravel':(174,169,153),\n"
        "         'sticker_white':(244,244,238),'sticker_black':(22,23,22),'sticker_yellow':(232,214,83),\n"
        "         'sticker_blue':(50,90,155),'sticker_green':(70,125,72),'sticker_orange':(213,113,55),'sticker_pink':(186,87,128)}")
    legacy_restroom_side="""            else:
                for z in np.arange(-2,2.2,.18):s.box([-4.1,.9,z],[.13,1.8,.16],'timber')
                s.box([-3.5,.9,2.1],[1.3,1.8,.12],'timber')
"""
    if legacy_restroom_side not in fm:
        raise RuntimeError('legacy restroom side enclosure marker missing')
    fm=fm.replace(legacy_restroom_side,"""            else:
                # v020 preserves the compact corrected restroom body from v019.
                pass
""")
    marker="        elif typ in ['flagpole','utility']:"
    sign=r'''        elif typ=='sticker_stop_sign':
            # User-reference Bithlo roadside sign: slender stickered pole,
            # broad silver upper sign back, central stop octagon, lower sticker board.
            # Sticker plaques are essentially flush (not the old chunky confetti).
            s.beam([0,0,0],[0,4.08,0],.045,'alloy',10)
            s.box([0,3.72,0],[2.72,.46,.045],'alloy')
            s.box([0,3.72,-.035],[2.43,.055,.045],'steel')
            s.box([0,1.52,0],[1.48,1.02,.045],'sticker_white')
            def octagon(cy,r,z,mat):
                vv=[[math.cos(math.pi/8+k*math.pi/4)*r,
                     cy+math.sin(math.pi/8+k*math.pi/4)*r,z] for k in range(8)]
                s.add(vv,[list(range(8))],mat)
            octagon(2.62,.75,.026,'sticker_white')
            octagon(2.62,.685,.031,'red')
            def plaque(cx,cy,w,h,ang,mat,z):
                cc=math.cos(ang);ss=math.sin(ang);pts=[]
                for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:
                    pts.append([cx+dx*cc-dy*ss,cy+dx*ss+dy*cc,z])
                s.add(pts,[list(range(4))],mat)
            rng=np.random.default_rng(20020)
            mats=['sticker_white','sticker_black','sticker_yellow','sticker_blue','sticker_green','red']
            for i in range(72):
                cx=rng.uniform(-.50,.50);dy=rng.uniform(-.48,.48)
                if abs(cx)+abs(dy)>.78:cx*=.70;dy*=.70
                plaque(cx,2.62+dy,rng.uniform(.10,.30),rng.uniform(.07,.16),
                       rng.uniform(-.45,.45),mats[i%len(mats)],.033+i*1e-7)
            for i in range(55):
                plaque(rng.uniform(-.61,.61),1.52+rng.uniform(-.40,.40),
                       rng.uniform(.10,.27),rng.uniform(.07,.15),
                       rng.uniform(-.40,.40),mats[(i+2)%len(mats)],.026+i*1e-7)
            for i,y in enumerate(np.linspace(.28,.95,10)):
                plaque(0,y,.12,.085,(i%3-1)*.10,mats[(i+1)%len(mats)],.050+i*1e-7)
            for i in range(12):
                plaque(rng.uniform(-1.10,1.10),3.72+rng.uniform(-.12,.12),
                       rng.uniform(.12,.28),rng.uniform(.07,.14),
                       rng.uniform(-.20,.20),mats[(i+3)%len(mats)],.025+i*1e-7)
'''
    if marker not in fm:
        raise RuntimeError('facility sign injection marker missing')
    fm=fm.replace(marker,sign+marker)
    fmp.write_text(fm,encoding='utf-8')

    # Layout QA: preserve v019 start/restroom relationships but explicitly validate
    # the user-authorized pickup removal and relocated sign.
    q=transformed('qa_v016_layout.py')
    start=q.index("    b=np.array(assets['restroom']['xz']")
    end=q.index("    save(R/'DOCUMENTATION/v020_layout_validation.json'",start)
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
    qa['layout_checks_pass']=bool(clear.min()>.5 and not cross and 0<t6['arc_start']-cfg['merge_station_m']<8 and t6['angle']<0 and bathroom_to_truck<14.5 and bathroom_to_canopy<14.5 and bathroom_in_grass and road_clear>.5 and qa['generic_pickup_03_removed'] and sign_asset['xz']==[242.0,143.0])
"""
    q=q[:start]+rel+q[end:]
    q=q.replace("('restroom','Bathroom beside red truck',(-110,-35)),('pickup_02','Red truck',(8,-22)),('canopy_01','Canopy',(10,16)),('rv_02','Camper / RV',(10,-20))",
                "('restroom','Bathroom · opposite road',(-95,-38)),('pickup_01','Other red truck',(-62,-22)),('canopy_02','Canopy',(-10,15)),('rv_02','Camper / RV',(10,-20))")
    (R/'TOOLS/qa_v020_layout.py').write_text(q,encoding='utf-8')

    # Preserve the validated v019 connected gravel network.
    pr=transformed('pit_roads_v016.py')
    pr=pr.replace("rgb=np.clip(np.array([184,179,163])+n[...,None],0,255).astype('uint8');Image.fromarray(rgb).save(O/'v020_pit_sand.tga')",
"""base=np.array([194,188,174],dtype=float);rgb=np.clip(base+n[...,None]*1.35,0,255).astype('uint8')
    rr=np.random.default_rng(17017);yy=rr.integers(0,256,5000);xx=rr.integers(0,256,5000);fleck=rr.integers(-24,25,5000)
    for k in range(len(xx)):rgb[yy[k],xx[k]]=np.clip(rgb[yy[k],xx[k]].astype(int)+fleck[k],0,255)
    Image.fromarray(rgb).save(O/'v020_pit_gravel.tga')""")
    pr=pr.replace("O/'v020_pit_sand.tga'","O/'v020_pit_gravel.tga'")
    pr=pr.replace("print('Pit roads and RV/restroom grass paddock prepared')",
                  "print('v020 connected gravel loop and expanded grass paddocks preserved')")
    (R/'TOOLS/pit_roads_v020.py').write_text(pr,encoding='utf-8')

    # Native build: same validated v016-v019 toolchain, with v020 gravel, logo,
    # and explicit compiled-EDF texture checks.
    bw=transformed('build_windows_v016.py')
    bw=bw.replace("shutil.copy2(O/'v020_pit_sand.tga',p/'v020_pit_sand.tga')",
                  "shutil.copy2(O/'v020_pit_gravel.tga',p/'v020_pit_gravel.tga')")
    bw=bw.replace("map = v020_pit_sand.tga","map = v020_pit_gravel.tga").replace("repetitions = 80","repetitions = 95")
    bw=bw.replace("    orig_stage=ns['stage']",
"""    from logo_v020 import main as preserve_logo
    preserve_logo()
    assert sha(R/'12_RELEASE'/NAME/(NAME+'.tga'))==read(S/'v018_invariants.json')['menu_preview_tga_sha256']
    orig_stage=ns['stage']""")
    oldtry="    try:ns['main']()\n    except Exception as e:"
    newtry="""    try:
        ns['main']()
        from PIL import Image
        mats=read(S/'vehicle_materials.json');names=[]
        for name,info in mats.items():
            im=Image.open(S/info['file'])
            if not (im.width&(im.width-1)==0 and im.height&(im.height-1)==0):
                raise RuntimeError('NPOT texture reached native compile: '+name+str(im.size))
            names.append(('v020_vehicle_'+name+'.tga').encode())
        edf=R/'08_OBJECTS_GAME/scenery.edf';raw=edf.read_bytes()
        missing=[n.decode() for n in names if raw.find(n)<0]
        if missing:raise RuntimeError('Compiled EDF missing v020 texture references: '+str(missing))
        save(R/'DOCUMENTATION/v020_native_texture_validation.json',dict(checks_pass=True,power_of_two=True,texture_count=len(names),edf_bytes=len(raw),missing=[],probe_evidence='Actions 36824107860: 256x256 probe EDF 209988 bytes; 256x320 NPOT probe EDF only 716 bytes'))
    except Exception as e:"""
    if oldtry not in bw:raise RuntimeError('native try block marker missing')
    bw=bw.replace(oldtry,newtry)
    bw=bw.replace("native.update(version='v020',",
        "native.update(version='v020',source_commit=os.environ.get('GITHUB_SHA','local'),vehicle_validation=read(R/'DOCUMENTATION/v020_vehicle_validation.json'),menu_logo_validation=read(R/'DOCUMENTATION/v020_menu_logo_validation.json'),v018_invariants=read(R/'DOCUMENTATION/v020_invariants_validation.json'),native_texture_validation=read(R/'DOCUMENTATION/v020_native_texture_validation.json'),")
    bw=bw.replace('obstacle and layout correction candidate',
                  'v020 corrected owner vehicles, realistic bikes and Bithlo pit-sign candidate')
    bw=bw.replace('Review all R01-R18 features against the supplied checklist and confirm the facility colors in game.',
                  'Review Premier Power wrap, all four rebuilt bikes and number/shroud graphics, relocated Bithlo sign and removal of pickup_03. Terrain/start/race/pit roads remain protected.')
    (R/'TOOLS/build_windows_v020.py').write_text(bw,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-only',action='store_true')
    args=ap.parse_args()
    materialize_runtime()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')
    scripts=[
        'materialize_v009_baseline.py','rebuild_v009_geometry.py',
        'v020_common.py','rebuild_v020_geometry.py','qa_v020_geometry.py',
        'build_v020_start_terrain.py','build_v020_race.py','rebind_v020_scenery.py',
        'facility_mesh_v020.py','qa_v020_layout.py','append_facilities_v020.py',
        'vehicle_textures_v020.py','model_vehicles_v020.py','qa_vehicles_v020.py',
        'append_vehicles_v020.py','prepare_v020_release.py','pit_roads_v020.py',
        'qa_v020_custom.py','logo_v020.py',
        'render_facilities_v020.py','render_v020_layout.py','render_vehicles_v020.py',
        'finalize_source_v020.py'
    ]
    for script in scripts:
        print('RUN',script,flush=True)
        subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,env=env,check=True)
    save(R/'DOCUMENTATION/v020_source_checkpoint.json',dict(
        version='v020',source_commit=os.environ.get('GITHUB_SHA','local'),
        geometry_spec_sha256=sha(S/'v020_geometry_spec.json'),
        facilities_spec_sha256=sha(S/'facilities.json'),
        pit_spec_sha256=sha(S/'pit_facilities.json'),
        vehicle_spec_sha256=sha(S/'vehicles.json'),
        vehicle_validation_sha256=sha(R/'DOCUMENTATION/v020_vehicle_validation.json'),
        menu_logo_validation_sha256=sha(R/'DOCUMENTATION/v020_menu_logo_validation.json'),
        user_request_validation_sha256=sha(R/'DOCUMENTATION/v020_user_request_validation.json'),
        source_checks_pass=True,native_compilation=False,in_game_riding=False,
        raw_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),
        start_tcl_sha256=sha(O/'start.tcl'),rdf_sha256=sha(O/(NAME+'.rdf'))))
    if not args.source_only:
        subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v020.py')],cwd=R,env=env,check=True)

if __name__=='__main__':
    main()
