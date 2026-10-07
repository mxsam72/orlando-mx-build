"""Compile v031 through the accepted PiBoSo Windows interface, then verify it."""
import os, shutil, re, struct, zipfile, subprocess, sys
from PIL import Image
from validate_native_textures_v024 import bitmap_signature, verify_files
from v031_common import *

def main():
    if os.name!='nt':raise SystemExit('Native v031 compilation requires the Windows workflow.')
    subprocess.run([sys.executable,str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    qa=read(O/'source_validation.json');assert qa['source_checks_pass']
    source=(R/'TOOLS/build_windows.py').read_text()
    old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'"; assert source.count(old)==1
    source=source.replace(old,"destination=V031_REPO/'12_RELEASE/OrlandoMX_2026_v031.pkz'")
    source=source.replace("ROOT/'BUILD/native_coordinate_probes.json'","V031_REPO/'V031_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v031_native','__file__':__file__,'V031_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    W=R/'BUILD/v009_work';P=R/'BUILD/v031_stage';DEST=R/'12_RELEASE'/NAME
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
        p=P/'track.hmf';text=p.read_text();m=re.search(r'num_layers\s*=\s*(\d+)',text);count=int(m[1]);assert count==15
        text=text[:m.start(1)]+str(count+1)+text[m.end(1):]
        text+=f'\nlayer{count}\n{{\n map = v024_pit_gravel.tga\n repetitions = 95\n mask = mask_v024_pit_roads.tga\n}}\n';p.write_text(text)
        params=P/'map_params.ini';lighting=params.read_text()
        for key in ['shadowvolumes_supersampling','shadowmaps_supersampling']:
            lighting,n=re.subn(r'(?m)^'+key+r'\s*=\s*1\s*$',key+'=2',lighting);assert n==1
        params.write_text(lighting)
        assert sha(P/'terrain.raw')==qa['terrain_sha256'];assert sha(P/'scenery.fbx')==qa['scenery_sha256']
        assert sha(P/'start.tcl')==EXPECTED['start.tcl']
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
        save(O/'native_staging_validation.json',dict(checks_pass=True,native_layers=16,texture_references_resolved=True,
            physical_materials_exact_accepted_configuration=True,physical_masks_match_authored_source=True,
            shadow_supersampling=2,textures=textures,estimated_unique_terrain_RGBA8_MiB=round(resident/1048576,2),
            estimated_with_full_mip_chain_MiB=round(resident*4/3/1048576,2),estimate_excludes_scenery_and_driver_overhead=True))
        (O/'compiled_track.hmf').write_text(text)
    ns['stage']=stage
    try:ns['main']()
    except Exception as e:(R/'DOCUMENTATION/v031_native_failure.txt').write_text(str(e)+'\n');raise
    meshes=read(R/'V024_OUTPUT/vehicle_meshes.json')+read(R/'V024_OUTPUT/sign_graphic_meshes.json')
    textures=[O/'facility_textures'/('v024_vehicle_'+n+'.tga') for n in sorted({m['material'] for m in meshes})]
    textures += [O/'facility_textures'/n['texture'] for n in qa['pit_access']['new_textures']]
    objects=verify_files(W/'08_OBJECTS_GAME/scenery.edf',DEST/(NAME+'.map'),textures,R/'DOCUMENTATION/v031_native_object_texture_validation.json')
    raw=(DEST/(NAME+'.map')).read_bytes();embedded=[]
    # Check decoded pixels in compiled MAP, not merely staged filenames.
    for p in sorted((O/'materials').glob('v031_*.tga')):
        w,h,d=bitmap_signature(p);pos=raw.find(struct.pack('<2I',w,h)+d)
        assert pos>=0,'Missing native terrain bitmap: '+p.name
        embedded.append(dict(texture=p.name,size=[w,h],pixel_md5=d.hex(),map_signature_offset=pos))
    del raw
    pkz=R/'12_RELEASE/OrlandoMX_2026_v031.pkz'
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None;assert len(z.namelist())==13
        assert all(n.startswith(NAME+'/') for n in z.namelist())
    native=read(R/'DOCUMENTATION/native_build_validation.json')
    native.update(version='v031',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=qa['baseline_commit'],
        source_checks=True,source_validation=qa,geometry_unchanged=True,physics_unchanged=True,
        accepted_macro_layout_unchanged=True,physical_material_declarations_unchanged=True,
        staging_validation=read(O/'native_staging_validation.json'),terrain_texture_payloads=embedded,object_texture_validation=objects,
        pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,in_game_riding_test=False,in_game_visual_check=False,performance_test=False,
        pending=['MX Bikes load and riding test','Confirm both entry-sign faces read left to right','Inspect scanned soil blending and normal-map response at rider height','FPS/VRAM comparison'])
    save(R/'DOCUMENTATION/v031_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v031_Validation.json',native)
    (R/'12_RELEASE/Install_v031.txt').write_text('Orlando MX 2026 v031 - scanned dirt and sign update\n\nCopy OrlandoMX_2026_v031.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\. Select Orlando MX 2026 v031.\n\nTwelve distinct scanned soil materials plus a broad dirt-variation layer use thirteen independent CC0 Poly Haven source images. Matched scanned normal and height detail, restrained highlights and separate wet-material response are integrated into the native terrain shaders. Entry-board horizontal UVs are corrected on both native polygon faces.\n\nTested v030 geometry and grass coverage are unchanged, including protected pits grass, the cleared starting section and the 50% reduction of remaining course grass. The source previews are not game screenshots. Native compilation and validation passed; an in-game load, appearance, ride and performance test has not been performed here.\n',encoding='utf-8')
    print('v031 native PKZ and embedded textures verified; in-game riding remains pending.',flush=True)
if __name__=='__main__':main()

