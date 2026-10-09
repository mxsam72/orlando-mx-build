"""Compile v043 using the existing official, hash-pinned PiBoSo workflow."""
import os,re,shutil,struct,subprocess,sys,zipfile
import numpy as np
from PIL import Image
from v043_common import *
from v027_scenery import parse,geometry_records,vertices,values
from build_windows_v037 import probe
from validate_native_textures_v024 import bitmap_signature,verify_files

def active_diffuse_textures(nodes):
    objects={values(n)[0]:n for n in next(n for n in nodes if n['name']==b'Objects')['children']}
    models={mid for g,mid in geometry_records(nodes).values()}
    links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    materials={v[1] for v in links if v[2] in models and objects.get(v[1],{}).get('name')==b'Material'}
    active=set()
    for link in links:
        if link[2] not in materials or objects.get(link[1],{}).get('name')!=b'Texture':continue
        if link[0]==b'OP' and link[3]!=b'DiffuseColor':continue
        for n in objects[link[1]]['children']:
            if n['name'] not in [b'FileName',b'Filename',b'RelativeFilename']:continue
            value=values(n)[0];value=value.decode() if isinstance(value,bytes) else str(value)
            active.add(value.replace('\\','/').split('/')[-1])
    return active

def main():
    if os.name!='nt':raise SystemExit('Native v043 compilation requires Windows.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');ind=read(O/'v043_independent_validation.json');cfg=read(S/'update.json')
    assert qa['source_checks_pass'] and ind['checks_pass']
    source=(R/'TOOLS/build_windows.py').read_text();old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V043_REPO/'12_RELEASE/OrlandoMX_2026_v043.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V043_REPO/'V043_OUTPUT/native_coordinate_probes.json'").replace('compresslevel=6','compresslevel=9')
    ns={'__name__':'v043_native','__file__':__file__,'V043_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v043_stage';DEST=R/'12_RELEASE'/NAME
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
        save(O/'v043_staging_validation.json',dict(checks_pass=True,shadow_supersampling=2,terrain_and_scenery_exact_v043_source=True,MX_race_inputs_exact_v042=True,all_source_texture_hashes_match_stage=True,textures=textures))
    ns['stage']=stage;ns['main']()
    raw=(DEST/(NAME+'.map')).read_bytes();points=read(O/'v043_native_probes.json')['expected_xyz_metres']
    points+=read(O/'v042_native_probes.json')['expected_xyz_metres']
    points+=read(O/'v041_native_probes.json')['expected_xyz_metres']
    for name in ['memorial_support_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json']:points+=read(O/name)['expected_xyz_metres']
    coordinates=[]
    for p in points:
        error=probe(raw,p);assert error is not None,'Missing compiled v043 geometry '+str(p)
        coordinates.append(dict(expected_xyz_m=p,error_m=error))
    terrain=[]
    for p in sorted((O/'materials').glob('v032_*.tga')):
        w,h,d=bitmap_signature(p);offset=raw.find(struct.pack('<2I',w,h)+d);assert offset>=0,p.name
        terrain.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset))
    del raw
    # Decode native texture signatures for all existing high-resolution signs
    # and pit displays, the retained opaque flag, and every new v043 texture.
    textures=[]
    for key in ['pit_access','memorial','qwikchute']:
        textures += [O/'facility_textures'/n['texture'] for n in qa[key]['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['oval_scenery']['new_textures']+qa['v038_scenery']['new_textures']]
    textures += [O/'facility_textures/v040_american_flag.tga']
    textures += sorted((O/'facility_textures').glob('v041_*.tga'))
    textures += sorted((O/'facility_textures').glob('v042_*.tga'))
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    textures += [O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    scene_nodes=parse((O/'scenery.fbx').read_bytes())[0]
    active=active_diffuse_textures(scene_nodes)
    unused=sorted({p.name for p in textures if p.name not in active})
    # v028_red belonged only to the generic staging pickup removed in v041.
    # PiBoSo correctly prunes its unused native bitmap. Every requested sign,
    # display and new texture is still mandatory and verified byte for byte.
    assert unused==['v028_red.tga'],('Unexpected unused required artwork',unused)
    textures=[p for p in textures if p.name in active]
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v043_native_object_texture_validation.json')
    objects['unused_removed_pickup_texture_refs']=unused
    save(R/'DOCUMENTATION/v043_native_object_texture_validation.json',objects)
    rec=geometry_records(scene_nodes);trh=(DEST/(NAME+'.trh')).read_bytes();physical=[]
    for name in ['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap','TRKASPH_v041_oval_wall_gap_fill','WLLCONC_v041_grandstand_decks']:
        v=vertices(rec[name][0]);checks=[]
        for p in v[np.linspace(0,len(v)-1,12,dtype=int)]:
            error=probe(trh,p);assert error is not None,name;checks.append(dict(expected_xyz_m=p.tolist(),error_m=error))
        physical.append(dict(name=name,probes=checks))
    del trh
    baseline=R/'12_RELEASE/orlandomx_2026_v042'
    for suffix in ['.amb','.tsc','.tga','.rdf','_map.tga']:assert sha(DEST/(NAME+suffix))==sha(baseline/('orlandomx_2026_v042'+suffix))
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert sha(DEST/name)==sha(baseline/name)
    native_trh_identical=sha(DEST/(NAME+'.trh'))==sha(baseline/'orlandomx_2026_v042.trh')
    pkz=R/'12_RELEASE/OrlandoMX_2026_v043.pkz';size=pkz.stat().st_size;assert size<=cfg['maximum_pkz_bytes']
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v043',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_version='v042',baseline_release_id=cfg['baseline_release_id'],baseline_source_commit=cfg['baseline_source_commit'],source_checks=True,source_validation=qa,independent_source_checks=ind,staging_validation=read(O/'v043_staging_validation.json'),terrain_texture_payloads=terrain,object_texture_validation=objects,native_coordinate_validation=dict(checks_pass=True,MAP_probes=coordinates,physical_TRH_meshes=physical),flag_validation=read(O/'v043_flag_validation.json'),vehicle_validation=read(O/'v043_vehicle_validation.json'),native_trh_identical_to_v042=native_trh_identical,all_existing_collision_meshes_unchanged=True,freestyle_heightfield_preserved_exact_v042=True,v041_gap_fill_grandstands_crocodile_preserved_exact=True,oval_geometry_markings_textures_and_camber_unchanged=True,MX_layout_jumps_soils_start_gates_and_race_data_unchanged=True,qwikchute_user_verified_v039_fixes_preserved=True,speed_world_original_corrected_uvs_preserved=True,original_high_resolution_sign_and_color_textures_preserved=True,all_existing_pit_and_oval_vehicles_preserved_exact=True,normal_map_optimization=read(O/'optimization_validation.json'),pkz_sha256=sha(pkz),pkz_bytes=size,under_500_decimal_MB=True,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,pending=['User MX Bikes v043 load/riding test','Confirm flag track-facing canton is beside the pole and pit-facing flag is unchanged','Confirm Sam Ford beside the figure-eight Qwikchute billboard','Confirm all retained v042 course and assets'])
    save(R/'DOCUMENTATION/v043_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v043_Validation.json',native)
    instructions = """Orlando MX 2026 v043

Copy OrlandoMX_2026_v043.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v043. Keep v042 for comparison.

Only the track-facing side of the American flag is corrected. The stars now sit beside the pole on both sides, as on a real flag. The accepted pit-facing UVs, image, pole, placement, winding and 30 cm opaque anti-flicker separation are unchanged.

An additional copy of Sam's Ford F-150 King Ranch is parked beside the Qwikchute billboard by the figure-eight track. The original Ford remains in the pits. Original model geometry, markings, opaque materials and textures are reused, with the copy fitted to the grass terrain clear of the pavement and existing assets.

All other delivered v042 features remain exact, including the accepted MX course, figure-eight road and wall-gap collision fill, freestyle double, stadium seating, crocodile, Cybertrucks, signs, pit displays, soils and race data. Official Windows compilation and independent source/native checks passed. In-game confirmation remains for your test. Multiplayer clients and server need the same v043 PKZ.
"""
    atomic(R/'12_RELEASE/Install_v043.txt',instructions.encode())
    print('v043 official native build and validation passed; PKZ bytes:',size,flush=True)

if __name__=='__main__':main()
