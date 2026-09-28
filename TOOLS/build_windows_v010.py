"""Compile only v010 using the repository's hash-pinned official native tools."""
import os, shutil
from v010_common import *

def main():
    if os.name!='nt':raise SystemExit('Native compilation requires Windows or the v010 GitHub workflow.')
    qa=read(R/'DOCUMENTATION/v010_release_validation.json')
    if not qa.get('release_source_checks_pass'):raise RuntimeError('v010 release source checks missing/failed')
    for rel,digest in qa['input_sha256'].items():
        if sha(R/rel)!=digest:raise RuntimeError('Input changed since source validation: '+rel)
    source=(R/'TOOLS/build_windows.py').read_text(encoding='utf-8')
    old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'";assert source.count(old)==1
    source=source.replace(old,"destination=V010_REPO/'12_RELEASE/OrlandoMX_2026_v010.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V010_REPO/'V010_OUTPUT/native_coordinate_probes.json'")
    ns={'__name__':'v010_native','__file__':__file__,'V010_REPO':R};exec(compile(source,__file__,'exec'),ns,ns)
    ns.update(ROOT=R/'BUILD/v009_work',NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=R/'BUILD/v010_stage',OUT=R/'12_RELEASE'/NAME)
    orig_stage=ns['stage']
    def stage():
        p=ns['STAGE']
        if p.exists():shutil.rmtree(p)
        orig_stage()
        for name in ['terrain.raw','scenery.fbx','start.tcl']:shutil.copy2(O/name,p/name)
        for mask in (O/'masks').glob('*.tga'):shutil.copy2(mask,p/('mask_'+mask.name))
        for name in ['terrain.raw','scenery.fbx','start.tcl']:assert sha(p/name)==sha(O/name)
        assert sha(p/'start.tcl')!=sha(R/'BUILD/v009_work/09_TRACKED/start.tcl')
        assert sha(p/'mask_start.tga')!=sha(R/'BUILD/v009_work/03_MASKS/start.tga')
    ns['stage']=stage
    try:ns['main']()
    except Exception as e:
        (R/'DOCUMENTATION/v010_native_failure.txt').write_text(str(e)+'\n',encoding='utf-8');raise
    native=read(R/'DOCUMENTATION/native_build_validation.json');native.update(version='v010',in_game_riding_test=False,first_lap_test=False,start_reset_test=False,geometry_source_sha256=sha(O/'terrain.raw'),source_checks=qa['release_source_checks_pass'])
    save(R/'DOCUMENTATION/v010_native_validation.json',native);save(R/'12_RELEASE/OrlandoMX_v010_Validation.json',native)
    (R/'12_RELEASE/Install_v010.txt').write_text('Orlando MX 2026 v010 - IRL correction candidate\n\nCopy OrlandoMX_2026_v010.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\.\nSelect Orlando MX 2026 v010. Earlier versions remain separate.\n\nNative compilation is not ride validation. Test an actual 24-rider start into T05, first finish crossing, a full timed lap and resets on the start lane. Then record the P01-P14 comparison lap. EX1/EX2 remain disabled pending clarification.\n',encoding='utf-8')
    print('v010 native candidate packaged. In-game tests still required.')
if __name__=='__main__':main()
