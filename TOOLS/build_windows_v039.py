"""Compile v039 with official PiBoSo tools and enforce a decimal 500 MB cap."""
import os, re, shutil, struct, subprocess, sys, zipfile
import numpy as np
from PIL import Image
from v039_common import *
from v027_scenery import parse, geometry_records, vertices
from build_windows_v037 import probe
from validate_native_textures_v024 import bitmap_signature, verify_files

def main():
    if os.name!='nt':raise SystemExit('Native v039 compilation requires Windows.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');ind=read(O/'v039_independent_validation.json');cfg=read(S/'sign_fix.json');assert qa['source_checks_pass'] and ind['checks_pass']
    source=(R/'TOOLS/build_windows.py').read_text();old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V039_REPO/'12_RELEASE/OrlandoMX_2026_v039.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V039_REPO/'V039_OUTPUT/native_coordinate_probes.json'").replace('compresslevel=6','compresslevel=9')
    ns={'__name__':'v039_native','__file__':__file__,'V039_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v039_stage';DEST=R/'12_RELEASE'/NAME;ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST);original_stage=ns['stage']
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
        assert sha(P/'terrain.raw')==sha(BASE/'terrain.raw') and sha(P/'scenery.fbx')==qa['scenery_sha256']
        textures=[]
        for folder in ['materials','facility_textures']:
            for p in (O/folder).glob('*.tga'):
                with Image.open(p) as im:w,h=im.size
                assert w>0 and h>0 and not w&(w-1) and not h&(h-1);assert sha(P/p.name)==sha(p);textures.append(dict(file=p.name,size=[w,h],sha256=sha(p)))
        save(O/'v039_staging_validation.json',dict(checks_pass=True,shadow_supersampling=2,MX_physics_inputs_exact_v038=True,all_source_texture_hashes_match_stage=True,textures=textures))
    ns['stage']=stage;ns['main']()
    raw=(DEST/(NAME+'.map')).read_bytes();points=read(O/'native_coordinate_probes.json')['expected_xyz_metres']
    for name in ['memorial_native_probes.json','memorial_support_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json','update_native_probes.json']:points+=read(O/name)['expected_xyz_metres']
    coordinate=[]
    for p in points:
        error=probe(raw,p);assert error is not None,'Missing compiled geometry '+str(p);coordinate.append(dict(expected_xyz_m=p,error_m=error))
    old_memorial=read(O/'memorial_support_native_probes.json')['prior_xyz_metres'];assert all(raw.find(struct.pack('<3f',*p))<0 for p in old_memorial)
    removed_backboards=ind['removed_black_backboard_corners_xyz_m'];assert all(raw.find(struct.pack('<3f',*p))<0 for p in removed_backboards),'An old black backboard corner remains in native MAP'
    terrain=[]
    for p in sorted((O/'materials').glob('v032_*.tga')):
        w,h,d=bitmap_signature(p);offset=raw.find(struct.pack('<2I',w,h)+d);assert offset>=0,p.name;terrain.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset,optimized=p.name in {c['file'] for c in read(BASE/'optimization_validation.json')['changed_files']}))
    del raw
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json');textures=[O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    for key in ['pit_access','memorial','qwikchute']:textures += [O/'facility_textures'/n['texture'] for n in qa[key]['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['oval_scenery']['new_textures']+qa['v038_scenery']['new_textures']]
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v039_native_object_texture_validation.json')
    rec=geometry_records(parse((O/'scenery.fbx').read_bytes())[0]);trh=(DEST/(NAME+'.trh')).read_bytes();physical=[]
    for name in ['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap']:
        v=vertices(rec[name][0]);checks=[]
        for point in v[np.linspace(0,len(v)-1,20,dtype=int)]:
            error=probe(trh,point);assert error is not None,name;checks.append(dict(expected_xyz_m=point.tolist(),error_m=error))
        physical.append(dict(name=name,probes=checks))
    del trh
    source=R/'12_RELEASE/orlandomx_2026_v038'
    for suffix in ['.amb','.tsc','.tga','.rdf','_map.tga']:assert sha(DEST/(NAME+suffix))==sha(source/('orlandomx_2026_v038'+suffix))
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert sha(DEST/name)==sha(source/name)
    pkz=R/'12_RELEASE/OrlandoMX_2026_v039.pkz';size=pkz.stat().st_size
    assert size<=cfg['maximum_pkz_bytes'],f'PKZ still exceeds 500 MB: {size}'
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    native=read(R/'DOCUMENTATION/native_build_validation.json');native.update(version='v039',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_version='user-tested v038',baseline_commit=cfg['baseline_source_commit'],source_checks=True,source_validation=qa,independent_source_checks=ind,staging_validation=read(O/'v039_staging_validation.json'),terrain_texture_payloads=terrain,object_texture_validation=objects,native_coordinate_validation=dict(checks_pass=True,MAP_probes=coordinate,physical_TRH_meshes=physical),oval_geometry_markings_textures_and_camber_unchanged=True,MX_heightmap_routes_race_gates_pits_soils_and_color_maps_unchanged=True,memorial_and_pit_displays_preserved=True,corrected_speed_world_sign_and_both_qwikchute_billboards=True,all_original_texture_pixels_exact_v038=True,parked_static_red_and_black_cybertrucks=True,normal_map_optimization=read(O/'optimization_validation.json'),pkz_sha256=sha(pkz),pkz_bytes=size,baseline_pkz_bytes=cfg['baseline_pkz_bytes'],saved_bytes=cfg['baseline_pkz_bytes']-size,under_500_decimal_MB=True,physical_TRH_byte_exact_v038=sha(DEST/(NAME+'.trh'))==sha(source/'orlandomx_2026_v038.trh'),in_game_riding_test=False,in_game_visual_check=False,performance_test=False,pending=['MX Bikes v039 load test','Read both sides of Orlando Speed World','Ride past both Qwikchute signs and check flickering'])
    save(R/'DOCUMENTATION/v039_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v039_Validation.json',native)
    atomic(R/'12_RELEASE/Install_v039.txt',('Orlando MX 2026 v039\n\nCopy OrlandoMX_2026_v039.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v039. Keep v038 for comparison.\n\nSIGN FIX ONLY: Orlando Speed World horizontal UV mapping is corrected on both sides. Both Qwikchute billboards use the original flat opaque image faces, with the full black backboard removed and at least 18 cm of spacing from supports. Original logo pixels, sizes, sign positions, textures, red/black grass parking, riding geometry, oval, soils, race and reset data are preserved. No further texture optimization is applied.\n\nNative official MAP/TRH compilation, source preservation, geometry probes, decoded texture signatures, removed-backboard probes, CRC checks and the 500,000,000-byte cap passed. In-game v039 visibility and riding verification remain pending. All multiplayer clients and the server need the same v039 PKZ.\n').encode())
    print('v039 native build passed; PKZ bytes:',size,'saved bytes:',cfg['baseline_pkz_bytes']-size,flush=True)

if __name__=='__main__':main()
