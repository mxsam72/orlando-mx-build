"""Native v025 build, reusing the validated compiler interface without editing it."""
from pathlib import Path
import os, json, shutil, re, hashlib, struct
from PIL import Image
from build_v025 import R, O, NAME, EXPECTED, sha
from validate_native_textures_v024 import verify_files, bitmap_signature

def read(p):return json.loads(Path(p).read_text())
def main():
    if os.name!='nt':raise SystemExit('Use the Windows v025 workflow for native compilation.')
    qa=read(O/'source_validation.json');assert qa['source_checks_pass']
    source=(R/'TOOLS/build_windows.py').read_text()
    old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V025_REPO/'12_RELEASE/OrlandoMX_2026_v025.pkz'")
    source=source.replace("ROOT/'BUILD/native_coordinate_probes.json'","V025_REPO/'V025_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v025_native','__file__':__file__,'V025_REPO':R}
    exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v025_stage';DEST=R/'12_RELEASE'/NAME
    ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=P,OUT=DEST)
    orig_stage=ns['stage']
    def stage():
        if P.exists():shutil.rmtree(P)
        orig_stage()
        for fn in ['terrain.raw','scenery.fbx','start.tcl','v024_pit_gravel.tga']:shutil.copy2(O/fn,P/fn)
        for p in (O/'masks').glob('*.tga'):shutil.copy2(p,P/('mask_'+p.name))
        fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
        for p in (O/'facility_textures').glob('*.tga'):
            shutil.copy2(p,P/p.name);shutil.copy2(p,fbm/p.name)
            assert sha(p)==sha(P/p.name)==sha(fbm/p.name)
        for p in (O/'materials').iterdir():
            if p.suffix in ['.tga','.shd','.hmf']:shutil.copy2(p,P/p.name)
        hmf=P/'track.hmf';text=hmf.read_text();m=re.search(r'num_layers\s*=\s*(\d+)',text)
        count=int(m[1]);text=text[:m.start(1)]+str(count+1)+text[m.end(1):]
        text+='\nlayer'+str(count)+'\n{\n map = v024_pit_gravel.tga\n repetitions = 95\n mask = mask_v024_pit_roads.tga\n}\n'
        hmf.write_text(text)
        params=P/'map_params.ini';lighting=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
            lighting,count=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=2',lighting)
            assert count==1,'Inspect changed native shadow parameter: '+key
        params.write_text(lighting)
        assert sha(P/'terrain.raw')==EXPECTED['terrain.raw']
        assert sha(P/'scenery.fbx')==EXPECTED['scenery.fbx']
        assert sha(P/'start.tcl')==EXPECTED['start.tcl']
        assert sha(P/'track.tht')==sha(W/'BUILD/track.tht'),'Physical terrain configuration changed'
        tht=(P/'track.tht').read_text()
        physical=re.findall(r'(?m)^\s*mask\s*=\s*(\S+)',tht)
        for fn in physical:
            expected=O/'masks'/fn.removeprefix('mask_')
            assert sha(P/fn)==sha(expected),'Physics mask changed: '+fn
        inputs=[];resident=0
        for fn in ['track.hmf','track.tht']:
            for key,path in re.findall(r'(?m)^\s*(map|mask|data)\s*=\s*(\S+)',(P/fn).read_text()):
                assert (P/path).is_file(),'Unresolved native input: '+path
                inputs.append(path)
        for p in (O/'materials').glob('*.shd'):
            for name in re.findall(r'(?m)^\s*map\s*=\s*(\S+)',p.read_text()):
                assert (P/name).is_file(),'Unresolved shader normal: '+name
                inputs.append(name)
        texchecks=[]
        for name in sorted(set(inputs)):
            p=P/name
            if p.suffix!='.tga':continue
            im=Image.open(p);w,h=im.size
            assert w>0 and h>0 and not w&(w-1) and not h&(h-1),'Non-power-of-two material'
            resident+=w*h*4
            texchecks.append(dict(file=name,width=w,height=h,sha256=sha(p)))
        (O/'native_staging_validation.json').write_text(json.dumps(dict(checks_pass=True,
            geometry_exact=True,physical_hmf_tht_grid_same=True,tht_sha256=sha(P/'track.tht'),
            physical_masks_exact=physical,texture_references_resolved=True,textures=texchecks,
            shadow_supersampling=2,light_direction_unchanged=True,
            estimated_unique_terrain_RGBA8_MiB=round(resident/1048576,2),
            estimated_with_full_mip_chain_MiB=round(resident*4/3/1048576,2),
            estimate_excludes_scenery_and_driver_overhead=True),indent=2)+'\n')
        (O/'compiled_track.hmf').write_text(text)
    ns['stage']=stage
    try:ns['main']()
    except Exception as e:
        (R/'DOCUMENTATION/v025_native_failure.txt').write_text(str(e)+'\n');raise
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    used=sorted({x['material'] for x in meshes})
    textures=[O/'facility_textures'/('v024_vehicle_'+name+'.tga') for name in used]
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v025_native_object_texture_validation.json')
    # The existing native validator established this exact decoded-pixel signature.
    # Terrain textures are checked in MAP directly, not by filename presence.
    raw=(DEST/(NAME+'.map')).read_bytes();embedded=[]
    for p in sorted((O/'materials').glob('v025_*.tga')):
        w,h,d=bitmap_signature(p);sig=struct.pack('<2I',w,h)+d;pos=raw.find(sig)
        if pos<0:raise RuntimeError('Native MAP is missing exact terrain bitmap signature: '+p.name)
        embedded.append(dict(texture=p.name,width=w,height=h,pixel_md5=d.hex(),map_signature_offset=pos))
    del raw
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v025',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=qa['baseline_commit'],
        source_checks=True,geometry_unchanged=True,physics_unchanged=True,scenery_unchanged=True,
        protected_source=qa['protected'],terrain_texture_payloads=embedded,object_texture_validation=objects,
        material_validation=read(O/'material_validation.json'),staging_validation=read(O/'native_staging_validation.json'),
        in_game_riding_test=False,in_game_visual_check=False,performance_test=False,
        pending=['MX Bikes load test','Rider and elevated visual inspection','Full lap visual audit','FPS/VRAM comparison'])
    pkz=R/'12_RELEASE/OrlandoMX_2026_v025.pkz'
    native.update(pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size)
    for p in [R/'DOCUMENTATION/v025_native_validation.json',R/'12_RELEASE/OrlandoMX_v025_Validation.json']:
        p.write_text(json.dumps(native,indent=2)+'\n')
    (R/'12_RELEASE/Install_v025.txt').write_text('Orlando MX 2026 v025 - visual test candidate\n\nCopy OrlandoMX_2026_v025.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\.\nSelect Orlando MX 2026 v025. v024 remains separate for comparison.\n\nGeometry, traction, deformation, scenery, pits, start and timing match v024 exactly at source. Racing remains deferred.\n\nInspect dirt at normal rider height and stopped: R07, R09, R10 takeoff and landing, T09, R11, R12, R14, R16, R17 and R18. Look for texture repetition, overly dark wear, sharp grass edges and normal-map direction. Compare FPS and loading against v024 with identical settings.\n\nNative compilation is not in-game validation. Source-rendered comparison images are not MX Bikes screenshots.\n')
    print('v025 native candidate built; actual game and performance checks remain pending.',flush=True)
if __name__=='__main__':main()
