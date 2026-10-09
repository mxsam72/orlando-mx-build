"""Compile the v037 additive oval with official PiBoSo Windows tools."""
import os, shutil, re, struct, zipfile, subprocess, sys
import numpy as np
from PIL import Image
from validate_native_textures_v024 import bitmap_signature, verify_files
from v037_common import *
from v027_scenery import parse, geometry_records, vertices

def probe(raw,point,tolerance=.0001):
    if raw.find(struct.pack('<3f',*point))>=0:return 0.
    lo=struct.unpack('<I',struct.pack('<f',point[0]-tolerance))[0];hi=struct.unpack('<I',struct.pack('<f',point[0]+tolerance))[0]
    for bits in range(lo,hi+1):
        needle=struct.pack('<I',bits);offset=raw.find(needle)
        while offset>=0 and offset+12<=len(raw):
            got=struct.unpack_from('<3f',raw,offset);error=max(abs(a-b) for a,b in zip(point,got))
            if error<tolerance:return error
            offset=raw.find(needle,offset+1)
    return None

def main():
    if os.name!='nt':raise SystemExit('Native v037 compilation requires the Windows workflow.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');independent=read(O/'oval_independent_validation.json');assert qa['source_checks_pass'] and independent['checks_pass']
    for name in ['terrain.raw','main.tcl','start.tcl']:assert sha(O/name)==sha(BASE/name)
    source=(R/'TOOLS/build_windows.py').read_text();old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V037_REPO/'12_RELEASE/OrlandoMX_2026_v037.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V037_REPO/'V037_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v037_native','__file__':__file__,'V037_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v037_stage';DEST=R/'12_RELEASE'/NAME
    ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST);orig_stage=ns['stage']
    def stage():
        if P.exists():shutil.rmtree(P)
        orig_stage()
        for fn in ['terrain.raw','scenery.fbx','start.tcl','main.tcl','v024_pit_gravel.tga']:shutil.copy2(O/fn,P/fn)
        for p in (O/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
        fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
        for p in (O/'facility_textures').iterdir():
            if p.suffix not in ['.tga','.shd']:continue
            shutil.copy2(p,P/p.name);shutil.copy2(p,fbm/p.name);assert sha(p)==sha(P/p.name)==sha(fbm/p.name)
        for p in (O/'materials').iterdir():
            if p.suffix in ['.tga','.shd','.hmf']:shutil.copy2(p,P/p.name)
        shutil.copy2(BASE/'compiled_track.hmf',P/'track.hmf');assert sha(P/'track.hmf')==sha(O/'compiled_track.hmf')
        params=P/'map_params.ini';lighting=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
            lighting,n=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=2',lighting);assert n==1
        params.write_text(lighting)
        assert sha(P/'track.tht')==sha(W/'BUILD/track.tht'),'MX physical material declarations changed'
        for fn in re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',(P/'track.tht').read_text()):assert sha(P/fn)==sha(O/'masks'/fn.removeprefix('mask_'))
        assert sha(P/'terrain.raw')==qa['terrain_sha256'];assert sha(P/'scenery.fbx')==qa['scenery_sha256']
        refs=[]
        for fn in ['track.hmf','track.tht']:
            for key,path in re.findall(r'(?m)^\s*(map|mask|data)\s*=\s*(\S+)',(P/fn).read_text()):assert (P/path).is_file();refs.append(path)
        for folder in ['materials','facility_textures']:
            for shd in (O/folder).glob('*.shd'):
                for path in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shd.read_text()):assert (P/path).is_file();refs.append(path)
        refs += [p.name for p in (O/'facility_textures').glob('v037_*.tga')]
        textures=[]
        for name in sorted(set(refs)):
            if not name.endswith('.tga'):continue
            with Image.open(P/name) as im:w,h=im.size
            assert not w&(w-1) and not h&(h-1)
            textures.append(dict(file=name,size=[w,h],sha256=sha(P/name)))
        save(O/'native_staging_validation.json',dict(checks_pass=True,native_layers=15,texture_references_resolved=True,MX_physical_material_declarations_exact_v036=True,MX_heightmap_and_masks_exact_v036=True,scenery_asphalt_physical_prefix='TRKASPH',concrete_wall_physical_prefix='WLLCONC',shadow_supersampling=2,textures=textures))
    ns['stage']=stage;ns['main']()
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    textures=[O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    for key in ['pit_access','memorial','qwikchute']:textures += [O/'facility_textures'/n['texture'] for n in qa[key]['new_textures']]
    textures += [O/'facility_textures'/n['texture'] for n in qa['oval_scenery']['new_textures']]
    rawmap=(DEST/(NAME+'.map')).read_bytes();points=read(O/'native_coordinate_probes.json')['expected_xyz_metres']
    for fn in ['memorial_native_probes.json','memorial_support_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json','update_native_probes.json']:points+=read(O/fn)['expected_xyz_metres']
    probes=[]
    for point in points:
        error=probe(rawmap,point);assert error is not None,'Missing native MAP geometry: '+str(point);probes.append(dict(expected_xyz_m=point,error_m=error))
    prior=read(O/'memorial_support_native_probes.json')['prior_xyz_metres'];assert all(rawmap.find(struct.pack('<3f',*p))<0 for p in prior)
    embedded=[]
    for p in sorted((O/'materials').glob('v032_*.tga')):
        w,h,d=bitmap_signature(p);pos=rawmap.find(struct.pack('<2I',w,h)+d);assert pos>=0,p.name
        embedded.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=pos))
    del rawmap
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v037_native_object_texture_validation.json')
    # Asphalt must be in the actual physical TRH, not just the visual MAP.
    rec=geometry_records(parse((O/'scenery.fbx').read_bytes())[0]);rawtrh=(DEST/(NAME+'.trh')).read_bytes();physical=[]
    for name in ['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap']:
        vv=vertices(rec[name][0]);indices=np.linspace(0,len(vv)-1,20,dtype=int);checks=[]
        for point in vv[indices]:
            error=probe(rawtrh,point);assert error is not None,'Missing physical TRH geometry: '+name+' '+str(point);checks.append(dict(expected_xyz_m=point.tolist(),error_m=error))
        physical.append(dict(name=name,probes=checks))
    del rawtrh
    pkz=R/'12_RELEASE/OrlandoMX_2026_v037.pkz'
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    baseline=R/'12_RELEASE/orlandomx_2026_v036';assert sha(DEST/(NAME+'.trh'))!=sha(baseline/'orlandomx_2026_v036.trh')
    for suffix in ['.amb','.tsc','.tga','.rdf','_map.tga']:
        assert sha(DEST/(NAME+suffix))==sha(baseline/('orlandomx_2026_v036'+suffix)),suffix
    for fn in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert sha(DEST/fn)==sha(baseline/fn)
    save(O/'oval_native_coordinate_validation.json',dict(checks_pass=True,MAP_probes=probes,physical_TRH_meshes=physical,tolerance_m=.0001))
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v037',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=qa['baseline_commit'],baseline_version='user-tested v036',source_checks=True,source_validation=qa,independent_source_checks=independent,staging_validation=read(O/'native_staging_validation.json'),terrain_texture_payloads=embedded,object_texture_validation=objects,native_coordinate_validation=read(O/'oval_native_coordinate_validation.json'),MX_heightmap_route_soils_race_gates_pits_and_reset_byte_exact=True,existing_signs_and_pit_vehicles_preserved=True,asphalt_surface_in_physical_TRH=True,concrete_wall_in_physical_TRH=True,static_oval_cybertrucks=2,pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,pending=['MX Bikes v037 load and oval riding test','Oval entrance and crossover check','Cybertruck and boundary collision check','FPS comparison'])
    save(R/'DOCUMENTATION/v037_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v037_Validation.json',native)
    atomic(R/'12_RELEASE/Install_v037.txt',('Orlando MX 2026 v037\n\nCopy OrlandoMX_2026_v037.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v037. Keep v036 separately for comparison.\n\nNew: paved car oval in the empty field east of the trees, two grass infields, paved central crossover, low white/green concrete boundary with an open entrance, markings, rubber wear and two static Cybertruck display models on the asphalt. The trucks are scenery, not drivable or animated cars.\n\nTested v036 motocross heightmap, jumps, start lanes, soils, race centreline, gates, pit spawns, checkpoints, reset boundaries, signs, memorial and four pit displays retained unchanged.\n\nOfficial PiBoSo Windows MAP/TRH compilation, native asphalt/concrete collision mesh checks, source comparisons, compiled geometry and texture checks, and archive integrity passed. Review images are external source renders, not MX Bikes screenshots. v037 in-game load, oval riding, object collision and performance tests remain pending. All multiplayer clients and the server need the same v037 PKZ.\n').encode())
    print('v037 official native build and visual/physical geometry checks passed.',flush=True)
if __name__=='__main__':main()
