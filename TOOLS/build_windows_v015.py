"""Compile only v015 using the repository's hash-pinned official native tools."""
import os, shutil, re
from v015_common import *

def main():
    if os.name!='nt':raise SystemExit('Native compilation requires Windows or the v015 GitHub workflow.')
    qa=read(R/'DOCUMENTATION/v015_release_validation.json')
    if not qa.get('release_source_checks_pass'):raise RuntimeError('v015 release source checks missing/failed')
    for rel,digest in qa['input_sha256'].items():
        if sha(R/rel)!=digest:raise RuntimeError('Input changed since source validation: '+rel)
    source=(R/'TOOLS/build_windows.py').read_text(encoding='utf-8')
    old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V015_REPO/'12_RELEASE/OrlandoMX_2026_v015.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V015_REPO/'V015_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v015_native','__file__':__file__,'V015_REPO':R};exec(compile(source,__file__,'exec'),ns,ns)
    ns.update(ROOT=R/'BUILD/v009_work',NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=R/'BUILD/v015_stage',OUT=R/'12_RELEASE'/NAME)
    orig_stage=ns['stage']
    def stage():
        p=ns['STAGE']
        if p.exists():shutil.rmtree(p)
        orig_stage()
        for name in ['terrain.raw','scenery.fbx','start.tcl']:shutil.copy2(O/name,p/name)
        for mask in (O/'masks').glob('*.tga'):shutil.copy2(mask,p/('mask_'+mask.name))
        # Generated facility textures are referenced by the FBX during
        # fbx2edf.  Stage them in both the working root and scenery.fbm so the
        # native importer can resolve either normal FBX relative-path convention.
        facility_fbm=p/'scenery.fbm';facility_fbm.mkdir(exist_ok=True)
        for tex in (O/'facility_textures').glob('*.tga'):
            shutil.copy2(tex,p/tex.name)
            shutil.copy2(tex,facility_fbm/tex.name)
        texture_checks=[]
        for tex in sorted((O/'facility_textures').glob('*.tga')):
            digest=sha(tex);assert sha(p/tex.name)==digest and sha(facility_fbm/tex.name)==digest
            texture_checks.append(dict(texture=tex.name,sha256=digest,root_matches=True,fbm_matches=True))
        assert len(texture_checks)==read(R/'DOCUMENTATION/v015_scenery_validation.json')['new_materials']
        save(R/'DOCUMENTATION/v015_texture_staging_validation.json',dict(checks_pass=True,textures=texture_checks))
        shutil.copy2(O/'v015_pit_sand.tga',p/'v015_pit_sand.tga')
        hmf=p/'track.hmf';text=hmf.read_text(encoding='utf-8');match=re.search(r'num_layers\s*=\s*(\d+)',text);assert match
        count=int(match[1]);text=text[:match.start(1)]+str(count+1)+text[match.end(1):]
        text+='\nlayer'+str(count)+'\n{\n map = v015_pit_sand.tga\n repetitions = 80\n mask = mask_v015_pit_roads.tga\n}\n';hmf.write_text(text,encoding='utf-8')

        for name in ['terrain.raw','scenery.fbx','start.tcl']:assert sha(p/name)==sha(O/name)
        assert sha(p/'start.tcl')!=sha(R/'BUILD/v009_work/09_TRACKED/start.tcl')
        assert sha(p/'mask_start.tga')!=sha(R/'BUILD/v009_work/03_MASKS/start.tga')
    ns['stage']=stage
    try:ns['main']()
    except Exception as e:
        (R/'DOCUMENTATION/v015_native_failure.txt').write_text(str(e)+'\n',encoding='utf-8');raise
    native=read(R/'DOCUMENTATION/native_build_validation.json');native.update(version='v015',in_game_riding_test=False,first_lap_test=False,start_reset_test=False,geometry_source_sha256=sha(O/'terrain.raw'),source_checks=qa['release_source_checks_pass'])
    save(R/'DOCUMENTATION/v015_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v015_Validation.json',native)
    (R/'12_RELEASE/Install_v015.txt').write_text('Orlando MX 2026 v015 - obstacle and layout correction candidate\n\nCopy OrlandoMX_2026_v015.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\.\nSelect Orlando MX 2026 v015. Earlier versions remain separate.\n\nNative compilation is not ride validation. Test an actual 24-rider start around T05 and into T06, first finish crossing, a full timed lap and resets on the start lane. R01 carries the existing finish plane on its longer deck. Review all R01-R18 features against the supplied checklist and confirm the facility colors in game.\n',encoding='utf-8')
    print('v015 native candidate packaged. In-game tests still required.')
if __name__=='__main__':main()
