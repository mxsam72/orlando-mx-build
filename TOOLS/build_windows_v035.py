"""Compile v035 through the accepted PiBoSo Windows interface, then verify it."""
import os, shutil, re, struct, zipfile, subprocess, sys
from PIL import Image
from validate_native_textures_v024 import bitmap_signature, verify_files
from v035_common import *

def main():
    if os.name!='nt':raise SystemExit('Native v035 compilation requires the Windows workflow.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');assert qa['source_checks_pass']
    assert read(O/'holeshot_independent_validation.json')['checks_pass']
    assert sha(O/'main.tcl')==sha(BASE/'main.tcl')
    source=(R/'TOOLS/build_windows.py').read_text()
    old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'"; assert source.count(old)==1
    source=source.replace(old,"destination=V035_REPO/'12_RELEASE/OrlandoMX_2026_v035.pkz'")
    source=source.replace("ROOT/'BUILD/native_coordinate_probes.json'","V035_REPO/'V035_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v035_native','__file__':__file__,'V035_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v035_stage';DEST=R/'12_RELEASE'/NAME
    ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST);orig_stage=ns['stage']
    def stage():
        if P.exists():shutil.rmtree(P)
        orig_stage()
        for fn in ['terrain.raw','scenery.fbx','start.tcl','main.tcl','v024_pit_gravel.tga']:shutil.copy2(O/fn,P/fn)
        for p in (O/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
        fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
        for p in (O/'facility_textures').glob('*.tga'):
            shutil.copy2(p,P/p.name);shutil.copy2(p,fbm/p.name);assert sha(p)==sha(P/p.name)==sha(fbm/p.name)
        for p in (O/'materials').iterdir():
            if p.suffix in ['.tga','.shd','.hmf']:shutil.copy2(p,P/p.name)
        p=P/'track.hmf';text=p.read_text();m=re.search(r'num_layers\s*=\s*(\d+)',text);count=int(m[1]);assert count==14
        text=text[:m.start(1)]+str(count+1)+text[m.end(1):]
        text+=f'\nlayer{count}\n{{\n map = v024_pit_gravel.tga\n repetitions = 95\n mask = mask_v024_pit_roads.tga\n}}\n';p.write_text(text)
        params=P/'map_params.ini';lighting=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
            lighting,n=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=2',lighting);assert n==1
        params.write_text(lighting)
        assert sha(P/'terrain.raw')==qa['terrain_sha256'];assert sha(P/'scenery.fbx')==qa['scenery_sha256']
        assert sha(P/'start.tcl')==sha(O/'start.tcl');assert sha(P/'main.tcl')==sha(O/'main.tcl')
        assert sha(P/'track.tht')==sha(W/'BUILD/track.tht'),'Physical material declarations changed'
        physical=re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',(P/'track.tht').read_text())
        for fn in physical:assert sha(P/fn)==sha(O/'masks'/fn.removeprefix('mask_'))
        refs=[]
        for fn in ['track.hmf','track.tht']:
            for key,path in re.findall(r'(?m)^\s*(map|mask|data)\s*=\s*(\S+)',(P/fn).read_text()):
                assert (P/path).is_file(),'Missing native input: '+path;refs.append(path)
        for shd in (O/'materials').glob('*.shd'):
            for path in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shd.read_text()):assert (P/path).is_file();refs.append(path)
        resident=0;textures=[]
        for name in sorted(set(refs)):
            if not name.endswith('.tga'):continue
            im=Image.open(P/name);w,h=im.size;assert not w&(w-1) and not h&(h-1)
            resident+=w*h*4;textures.append(dict(file=name,size=[w,h],sha256=sha(P/name)))
        save(O/'native_staging_validation.json',dict(checks_pass=True,native_layers=15,texture_references_resolved=True,
            physical_materials_exact_accepted_configuration=True,physical_masks_match_authored_source=True,
            shadow_supersampling=2,textures=textures,estimated_unique_terrain_RGBA8_MiB=round(resident/1048576,2),
            estimated_with_full_mip_chain_MiB=round(resident*4/3/1048576,2),estimate_excludes_scenery_and_driver_overhead=True))
        (O/'compiled_track.hmf').write_text(text)
    ns['stage']=stage
    try:ns['main']()
    except Exception as e:(R/'DOCUMENTATION/v035_native_failure.txt').write_text(str(e)+'\n');raise
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    textures=[O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    textures += [O/'facility_textures'/n['texture'] for n in qa['pit_access']['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['memorial']['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['qwikchute']['new_textures']]
    probes=read(O/'memorial_native_probes.json')['expected_xyz_metres']
    probes+=read(O/'memorial_support_native_probes.json')['expected_xyz_metres']
    probes+=read(O/'qwikchute_native_probes.json')['expected_xyz_metres']
    probes+=read(O/'holeshot_native_probes.json')['expected_xyz_metres']
    rawedf=(DEST/(NAME+'.map')).read_bytes();probechecks=[]
    for point in probes:
        found=rawedf.find(struct.pack('<3f',*point))>=0;error=0. if found else None
        if not found:
            lo=struct.unpack('<I',struct.pack('<f',point[0]-.0001))[0];hi=struct.unpack('<I',struct.pack('<f',point[0]+.0001))[0]
            for bits in range(lo,hi+1):
                px=struct.pack('<I',bits);offset=rawedf.find(px)
                while offset>=0 and offset+12<=len(rawedf):
                    got=struct.unpack_from('<3f',rawedf,offset);difference=max(abs(a-b) for a,b in zip(point,got))
                    if difference<.0001:found=True;error=difference;break
                    offset=rawedf.find(px,offset+1)
                if found:break
        assert found,'Missing compiled memorial coordinate: '+str(point)
        probechecks.append(dict(expected_xyz_m=point,max_error_m=error))
    prior=read(O/'memorial_support_native_probes.json')['prior_xyz_metres']
    assert all(rawedf.find(struct.pack('<3f',*p))<0 for p in prior),'Old protruding post vertices still compiled'
    del rawedf
    save(O/'memorial_native_coordinate_validation.json',dict(checks_pass=True,probes=probechecks,tolerance_m=.0001))
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v035_native_object_texture_validation.json')
    raw=(DEST/(NAME+'.map')).read_bytes();embedded=[]
    # Check decoded pixels in compiled MAP, not merely staged filenames.
    for p in sorted((O/'materials').glob('v032_*.tga')):
        w,h,d=bitmap_signature(p);pos=raw.find(struct.pack('<2I',w,h)+d)
        assert pos>=0,'Missing native terrain bitmap: '+p.name
        embedded.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=pos))
    del raw
    pkz=R/'12_RELEASE/OrlandoMX_2026_v035.pkz'
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None;assert len(z.namelist())==13
        assert all(n.startswith(NAME+'/') for n in z.namelist())
    baseline=R/'12_RELEASE/orlandomx_2026_v033'
    assert sha(DEST/(NAME+'.trh'))!=sha(baseline/'orlandomx_2026_v033.trh'),'Updated riding geometry was not compiled'
    for suffix in ['.amb','.tsc','.tga']:
        assert sha(DEST/(NAME+suffix))==sha(baseline/('orlandomx_2026_v033'+suffix))
    assert sha(DEST/(NAME+'.rdf'))==sha(O/(NAME+'.rdf'))
    assert read(O/'holeshot_race_validation.json')['checks_pass']
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v035',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=qa['baseline_commit'],
        source_checks=True,source_validation=qa,riding_geometry_start_and_practice_only=True,main_native_tcl_byte_exact_v033=True,T05_full_bank_and_hill_byte_exact_v033=True,physics_materials_preserved=True,memorial_support_geometry_unchanged=True,qwikchute_billboard_preserved=True,
        all_jump_shapes_preserved=True,all_main_corners_preserved=True,gate_grid_world_positions_preserved=True,physical_material_declarations_unchanged=True,
        staging_validation=read(O/'native_staging_validation.json'),independent_source_checks=read(O/'holeshot_independent_validation.json'),terrain_texture_payloads=embedded,object_texture_validation=objects,
        pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,
        memorial_native_coordinate_checks=read(O/'memorial_native_coordinate_validation.json'), holeshot_terrain_validation=read(O/'holeshot_terrain_validation.json'),holeshot_race_validation=read(O/'holeshot_race_validation.json'),holeshot_scenery_validation=read(O/'holeshot_scenery_validation.json'),pending=['MX Bikes v035 load test','Full-pack gate-drop holeshot and first-lap timing','Deformation/reset checks','FPS comparison'])
    save(R/'DOCUMENTATION/v035_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v035_Validation.json',native)
    (R/'12_RELEASE/Install_v035.txt').write_text('Orlando MX 2026 v035 - v033 corner restored; wider start\n\nCopy OrlandoMX_2026_v035.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v035. Keep v033 separately for comparison.\n\nBuilt directly from tested v033, including its Qwikchute billboard, fixed Pup memorial supports, entry sign and v030 color tiles. The original main lap, T05 hill/bank, R05 double, R07 ant hill, all other jumps and corners are preserved in place. The new start keeps a 38 m wide straight apron and about 46 m of run-up from the gates, then sweeps into T05. Practice fencing follows the start clay edge, with its timber and metal sections joined. Only the local start/practice terrain, surface coverage and necessary entry fixtures are changed.\n\nAll 24 gate and 24 pit stalls, main checkpoints and reset limits remain the tested v033 configuration. Three start-only checkpoints follow the new start route. Official PiBoSo MAP/TRH compilation, native geometry and image payload checks, PKZ integrity and independent source comparisons completed. Before/after pictures are external source renders, not MX Bikes screenshots.\n\nThe user verified v033 gate-drop mode. v035 in-game riding, full-pack starts, first-lap timing, resets and performance remain to be tested. Use the same v035 PKZ on every multiplayer client and server.\n',encoding='utf-8')
    print('v035 native holeshot revision compiled and verified; in-game riding remains pending.',flush=True)
if __name__=='__main__':main()

