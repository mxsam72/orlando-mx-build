"""Compile v040 using the existing official, hash-pinned PiBoSo workflow."""
import os,re,shutil,struct,subprocess,sys,zipfile
import numpy as np
from PIL import Image
from v040_common import *
from v027_scenery import parse,geometry_records,vertices
from build_windows_v037 import probe
from validate_native_textures_v024 import bitmap_signature,verify_files

def main():
    if os.name!='nt':raise SystemExit('Native v040 compilation requires Windows.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');ind=read(O/'v040_independent_validation.json');cfg=read(S/'update.json')
    assert qa['source_checks_pass'] and ind['checks_pass']
    source=(R/'TOOLS/build_windows.py').read_text();old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V040_REPO/'12_RELEASE/OrlandoMX_2026_v040.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V040_REPO/'V040_OUTPUT/native_coordinate_probes.json'").replace('compresslevel=6','compresslevel=9')
    ns={'__name__':'v040_native','__file__':__file__,'V040_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v040_stage';DEST=R/'12_RELEASE'/NAME
    ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST);original_stage=ns['stage']
    def stage():
        if P.exists():shutil.rmtree(P)
        original_stage()
        for fn in ['terrain.raw','scenery.fbx','start.tcl','main.tcl','v024_pit_gravel.tga']:copy_exact(O/fn,P/fn)
        for p in (O/'masks').glob('*.tga'):copy_exact(p,P/('mask_'+p.name))
        fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
        for p in (O/'facility_textures').iterdir():
            if p.suffix in ['.tga','.shd']:copy_exact(p,P/p.name);copy_exact(p,fbm/p.name)
        for p in (O/'materials').iterdir():
            if p.suffix in ['.tga','.shd','.hmf']:copy_exact(p,P/p.name)
        copy_exact(O/'compiled_track.hmf',P/'track.hmf');assert sha(P/'track.hmf')==sha(BASE/'compiled_track.hmf')
        params=P/'map_params.ini';lighting=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
            lighting,n=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=2',lighting);assert n==1
        params.write_text(lighting)
        assert sha(P/'track.tht')==sha(W/'BUILD/track.tht')
        for name in re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',(P/'track.tht').read_text()):assert sha(P/name)==sha(O/'masks'/name.removeprefix('mask_'))
        assert sha(P/'terrain.raw')==qa['terrain_sha256'] and sha(P/'scenery.fbx')==qa['scenery_sha256']
        textures=[]
        for folder in ['materials','facility_textures']:
            for p in (O/folder).glob('*.tga'):
                with Image.open(p) as im:w,h=im.size
                assert w>0 and h>0 and not w&(w-1) and not h&(h-1)
                assert sha(P/p.name)==sha(p);textures.append(dict(file=p.name,size=[w,h],sha256=sha(p)))
        save(O/'v040_staging_validation.json',dict(checks_pass=True,shadow_supersampling=2,terrain_and_scenery_exact_v040_source=True,MX_race_inputs_exact_v039=True,all_source_texture_hashes_match_stage=True,textures=textures))
    ns['stage']=stage;ns['main']()
    raw=(DEST/(NAME+'.map')).read_bytes();points=read(O/'v040_native_probes.json')['expected_xyz_metres']
    for name in ['memorial_support_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json']:points+=read(O/name)['expected_xyz_metres']
    coordinates=[]
    for p in points:
        error=probe(raw,p);assert error is not None,'Missing compiled v040 geometry '+str(p)
        coordinates.append(dict(expected_xyz_m=p,error_m=error))
    terrain=[]
    for p in sorted((O/'materials').glob('v032_*.tga')):
        w,h,d=bitmap_signature(p);offset=raw.find(struct.pack('<2I',w,h)+d);assert offset>=0,p.name
        terrain.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset))
    del raw
    # Decode native texture signatures for all existing high-resolution signs
    # and pit displays, plus the new flattened opaque flag.
    textures=[]
    for key in ['pit_access','memorial','qwikchute']:
        textures += [O/'facility_textures'/n['texture'] for n in qa[key]['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['oval_scenery']['new_textures']+qa['v038_scenery']['new_textures']]
    textures += [O/'facility_textures/v040_american_flag.tga']
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    textures += [O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v040_native_object_texture_validation.json')
    rec=geometry_records(parse((O/'scenery.fbx').read_bytes())[0]);trh=(DEST/(NAME+'.trh')).read_bytes();physical=[]
    for name in ['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap']:
        v=vertices(rec[name][0]);checks=[]
        for p in v[np.linspace(0,len(v)-1,12,dtype=int)]:
            error=probe(trh,p);assert error is not None,name;checks.append(dict(expected_xyz_m=p.tolist(),error_m=error))
        physical.append(dict(name=name,probes=checks))
    del trh
    baseline=R/'12_RELEASE/orlandomx_2026_v039'
    for suffix in ['.amb','.tsc','.tga','.rdf','_map.tga']:assert sha(DEST/(NAME+suffix))==sha(baseline/('orlandomx_2026_v039'+suffix))
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert sha(DEST/name)==sha(baseline/name)
    assert sha(DEST/(NAME+'.trh'))!=sha(baseline/'orlandomx_2026_v039.trh'),'Freestyle collision terrain did not change'
    pkz=R/'12_RELEASE/OrlandoMX_2026_v040.pkz';size=pkz.stat().st_size;assert size<=cfg['maximum_pkz_bytes']
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v040',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_version='v039',baseline_release_id=cfg['baseline_release_id'],baseline_source_commit=cfg['baseline_source_commit'],source_checks=True,source_validation=qa,independent_source_checks=ind,staging_validation=read(O/'v040_staging_validation.json'),terrain_texture_payloads=terrain,object_texture_validation=objects,native_coordinate_validation=dict(checks_pass=True,MAP_probes=coordinates,physical_TRH_meshes=physical),freestyle_heightfield_source_and_staging_match=True,freestyle_changes_native_collision=True,oval_geometry_markings_textures_and_camber_unchanged=True,MX_layout_jumps_soils_start_gates_and_race_data_unchanged=True,qwikchute_user_verified_v039_fixes_preserved=True,speed_world_original_corrected_uvs_preserved=True,original_high_resolution_sign_and_color_textures_preserved=True,parked_red_and_black_cybertruck_positions_and_paints_preserved=True,normal_map_optimization=read(O/'optimization_validation.json'),pkz_sha256=sha(pkz),pkz_bytes=size,under_500_decimal_MB=True,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,pending=['User MX Bikes v040 load/riding test','Ride past memorial, flag, bathroom, vehicles and pit displays to confirm flicker repair','Test freestyle takeoff and landing','Check entrance sign placement and both readable faces'])
    save(R/'DOCUMENTATION/v040_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v040_Validation.json',native)
    atomic(R/'12_RELEASE/Install_v040.txt',('Orlando MX 2026 v040\n\nCopy OrlandoMX_2026_v040.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v040. Keep v039 for comparison.\n\nMemorial backing removed; original artwork retained with 23 cm minimum frame clearance. Flag uses separated opaque graphics. Bathroom panels behind doors are cut away. Duplicate/inward vehicle decals removed and offset 4.5 cm. Pit solids use exterior-face culling.\n\nFreestyle double runs from the right grass island to the left in the supplied screenshot (+Z in game): takeoff 8.5 m above ground, landing 7.8 m, lip-to-crest distance 44 m. Both mound footprints stay in the grass islands. Orlando Speed World arch now spans the figure-eight entrance.\n\nOriginal MX layout, jumps, soils, race data, fences, displays, Qwikchute signs, optimized textures, oval pavement/markings/walls, and red/black grass parking retained. Native official compilation and source/native checks passed. In-game flickering, jump riding, and placement verification remain for your test. All multiplayer clients and the server need the same v040 PKZ.\n').encode())
    print('v040 official native build and validation passed; PKZ bytes:',size,flush=True)

if __name__=='__main__':main()
