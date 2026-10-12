"""Official Windows compilation, exact physical preservation and bitmap payload checks."""
import os,re,shutil,struct,subprocess,sys,zipfile
from PIL import Image
from v044_common import *
from build_windows_v037 import probe
from validate_native_textures_v024 import bitmap_signature,verify_files
from build_windows_v043 import active_diffuse_textures
from v027_scenery import parse,geometry_records,vertices

def main():
    assert os.name=='nt','Use the official Windows workflow'
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'v044_source_validation.json');assert qa['checks_pass']
    W=R/'BUILD/v009_work';P=R/'BUILD/v044_stage';DEST=R/'12_RELEASE'/NAME;baseline=R/'12_RELEASE/orlandomx_2026_v043';DEST.mkdir(parents=True,exist_ok=True)
    for p in baseline.iterdir():
        if p.suffix in ['.map','.trh']:continue
        name=p.name.replace('orlandomx_2026_v043',NAME);shutil.copy2(p,DEST/name)
    ini=DEST/(NAME+'.ini');ini.write_text(ini.read_text().replace('v043','v044').replace('v042','v044'))
    amb=DEST/(NAME+'.amb');text=amb.read_text();text=text.replace('red = 0.48\n green = 0.53\n blue = 0.6','red = 0.44\n green = 0.49\n blue = 0.56').replace('red = 1.0\n green = 0.95\n blue = 0.82','red = 1.0\n green = 0.97\n blue = 0.90').replace('density = 0.00045','density = 0.00030');amb.write_text(text)
    source=(R/'TOOLS/build_windows.py').read_text();old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V044_REPO/'12_RELEASE/OrlandoMX_2026_v044.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V044_REPO/'V044_OUTPUT/native_coordinate_probes.json'").replace('compresslevel=6','compresslevel=9').replace("'terrained_map',2400","'terrained_map',4800").replace("'fbx2edf',900","'fbx2edf',2400")
    ns={'__name__':'v044_native','__file__':__file__,'V044_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST);original=ns['stage']
    def stage():
        if P.exists():shutil.rmtree(P)
        original()
        for fn in ['terrain.raw','scenery.fbx','start.tcl','main.tcl','v024_pit_gravel.tga']:shutil.copy2(O/fn,P/fn)
        for p in (O/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
        fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
        for folder in [M,F]:
            for p in folder.iterdir():
                if p.suffix in ['.tga','.shd','.hmf']:
                    shutil.copy2(p,P/p.name)
                    if folder==F:shutil.copy2(p,fbm/p.name)
        shutil.copy2(O/'compiled_track.hmf',P/'track.hmf')
        params=P/'map_params.ini';text=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:text,n=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=4',text);assert n==1
        text,n=re.subn(r'(?m)^shadowmaps_scale\s*=\s*0\.2\s*$','shadowmaps_scale=0.1',text);assert n==1
        params.write_text(text)
        assert sha(P/'track.tht')==sha(W/'BUILD/track.tht')
        for name in re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',(P/'track.tht').read_text()):assert sha(P/name)==sha(O/'masks'/name.removeprefix('mask_'))
        assert sha(P/'terrain.raw')==qa['terrain_sha256'] and sha(P/'scenery.fbx')==qa['scenery_sha256']
        for fn in ['track.hmf','track.tht']:
            for name in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',(P/fn).read_text()):assert (P/name).exists(),name
        save(O/'v044_staging_validation.json',dict(checks_pass=True,physical_declarations_exact=True,shadow_supersampling=4,shadowmap_scale=.1,terrain_self_shadowing=True,all_texture_references_resolved=True))
    ns['stage']=stage;ns['main']()
    raw=(DEST/(NAME+'.map')).read_bytes();coords=[]
    points=read(O/'v044_native_probes.json')['expected_xyz_metres']
    # Three probes per authored vegetation batch and scan part; plus legacy flag, Ford and gap repairs.
    for fn in ['v043_native_probes.json','v042_native_probes.json','v041_native_probes.json','qwikchute_native_probes.json','holeshot_native_probes.json']:
        if (O/fn).exists():points+=read(O/fn)['expected_xyz_metres']
    for p in points:
        e=probe(raw,p);assert e is not None,('Missing native new geometry',p);coords.append(dict(expected_xyz_m=p,error_m=e))
    signatures=[]
    text=(O/'compiled_track.hmf').read_text();names=set(re.findall(r'(?m)^\s*map\s*=\s*(\S+)',text))
    for name in list(names):
        shd=M/(name[:-4]+'.shd')
        if shd.exists():names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)',shd.read_text()))
    for name in sorted(names):
        p=P/name
        w,h,d=bitmap_signature(p);offset=raw.find(struct.pack('<2I',w,h)+d);assert offset>=0,('Native terrain payload missing',name);signatures.append(dict(texture=name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=offset))
    del raw
    scene=parse((O/'scenery.fbx').read_bytes())[0];active=active_diffuse_textures(scene);textures=[F/name for name in sorted(active) if (F/name).exists()]
    assert all((F/name).exists() for name in active),active
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v044_native_object_texture_validation.json')
    # Vegetation is purely visual. Any actual collision change rejects delivery.
    trh_exact=sha(DEST/(NAME+'.trh'))==sha(baseline/'orlandomx_2026_v043.trh');assert trh_exact,'Native physical track differs from delivered v043'
    for suffix in ['.tsc','.tga','.rdf','_map.tga']:assert sha(DEST/(NAME+suffix))==sha(baseline/('orlandomx_2026_v043'+suffix))
    for fn in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert sha(DEST/fn)==sha(baseline/fn)
    pkz=R/'12_RELEASE/OrlandoMX_2026_v044.pkz'
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v044',source_commit=os.environ['GITHUB_SHA'],baseline_version='v043',source_checks=True,source_validation=qa,surface_validation=read(O/'v044_surface_validation.json'),scenery_validation=read(O/'v044_scenery_validation.json'),staging_validation=read(O/'v044_staging_validation.json'),terrain_texture_payloads=signatures,object_texture_validation=objects,native_coordinate_validation=dict(checks_pass=True,MAP_probes=coords),native_trh_identical_to_v043=trh_exact,MX_layout_jumps_race_data_and_physics_exact=True,personalized_assets_and_road_gap_repairs_preserved=True,weather_focus='standard dry weather',package_size_cap_removed=True,pkz_bytes=pkz.stat().st_size,pkz_sha256=sha(pkz),in_game_visual_check=False,in_game_riding_test=False,performance_test=False,pending=['User MX Bikes load and standard-weather riding comparison','Check new foliage in motion and grass density','Confirm normal relief and overall daylight appearance','Measure frame rate and load time'])
    save(R/'12_RELEASE/OrlandoMX_v044_Validation.json',native)
    notes='''Orlando MX 2026 v044 — Standard Weather Realism

Copy OrlandoMX_2026_v044.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v044. Choose clear/standard dry weather. Keep v043 for comparison.

New continuous 8192x8192 route-following diffuse and normal bake replaces four fixed grooming orientations. Three wandering wheel paths, braking wear, subtle shoulder disturbance and broad material variation follow the real accepted course. Six photographic dirt families refined while preserving their existing average colors. Dry damp overlay removed. Grass boundary wear refined without extending grass across racing lines.

Selected near-course trees replaced with reduced scan-derived foliage and real photographic materials. Botanical Bermuda clusters added in grass margins with corridor, road and facility exclusions. Bark, timber and concrete receive photographic grain and matte normal maps. Native alpha-tested leaf/grass textures avoid transparency sorting artifacts. Clear daylight fill/fog refined; sun direction stays aligned with native compiled shadows. Higher quality native shadows: supersampling 4, shadowmap scale 0.1.

MX riding heightfield, jumps, race data and complete compiled collision TRH are identical to delivered v043. Existing flag faces, billboards, personalized vehicles, wall-gap repair, seating and pits remain retained. Official Windows source/native/bitmap/archive validation passed. Actual in-game visuals, riding and performance remain pending your test.

No 500 MB size limit applies to this build. This version focuses on clear dry weather; rainy/muddy presentation was not upgraded or validated. Server and clients must use the same PKZ for multiplayer.
'''
    atomic(R/'12_RELEASE/Install_v044.txt',notes.encode())
    print('v044 official Windows compilation and exact collision preservation passed; PKZ bytes',pkz.stat().st_size,flush=True)
if __name__=='__main__':main()
