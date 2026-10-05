"""Recover v026, allowing a different FBX only after exact native equivalence.

The old pipeline can produce a different serialized FBX on another runner.
Unchanged native scenery is proved with the accepted complete EDF SHA-256,
not a visual similarity or loose coordinate tolerance. Terrain/start checks
remain byte-exact. Historical source generators are executed without edits.
"""
import os, sys, shutil, subprocess, urllib.request, zipfile
from v027_common import *

ACCEPTED_EDF_SHA256='9e868d4c5453adfafd423d5e46f26f22678cc7ea04f6eb65470876af289e280b'
ACCEPTED_EDF_BYTES=173137253
def native_equivalence():
    assert os.name=='nt','Baseline native equivalence requires Windows'
    W=R/'BUILD/v009_work'; P=R/'BUILD/v027_baseline_native_check'
    source=(R/'TOOLS/build_windows.py').read_text();ns={'__name__':'baseline_check','__file__':__file__}
    exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
    ns.update(ROOT=W,STAGE=P,OUT=R/'BUILD/v027_baseline_unused_release',LOG=R/'DOCUMENTATION')
    if P.exists():shutil.rmtree(P)
    ns['stage']();shutil.copy2(R/'V024_OUTPUT/scenery.fbx',P/'scenery.fbx')
    fbm=P/'scenery.fbm';fbm.mkdir(exist_ok=True)
    for p in (R/'V024_OUTPUT/facility_textures').glob('*.tga'):
        shutil.copy2(p,P/p.name);shutil.copy2(p,fbm/p.name)
    versions=read(W/'BUILD/tool_versions.json');tools=W/'BUILD/native_tools';tools.mkdir(exist_ok=True)
    for name,v in versions.items():
        if 'fbx2edf' not in name.lower():continue
        p=tools/name
        if not p.is_file() or sha(p)!=v['sha256']:
            with urllib.request.urlopen(v['url'],timeout=60) as response,p.open('wb') as f:shutil.copyfileobj(response,f)
        assert sha(p)==v['sha256'],'Official native tool package changed'
        with zipfile.ZipFile(p) as z:z.extractall(tools)
    edf=P/'scenery.edf';ns['run'](tools/'fbx2edf/fbx2edf_x64.exe',['scenery.fbx','scenery.edf','edf_params.ini','-q'],'v027_baseline_fbx2edf',900)
    native_sha=sha(edf); actual=sha(R/'V024_OUTPUT/scenery.fbx')
    qa=dict(regenerated_fbx_sha256=actual,accepted_fbx_sha256=EXPECTED['scenery.fbx'],
            compiled_edf_sha256=native_sha,accepted_edf_sha256=ACCEPTED_EDF_SHA256,
            compiled_edf_bytes=edf.stat().st_size,accepted_edf_bytes=ACCEPTED_EDF_BYTES,
            native_equivalent=native_sha==ACCEPTED_EDF_SHA256 and edf.stat().st_size==ACCEPTED_EDF_BYTES,
            method='Exact complete accepted EDF bytes, including geometry, normals and embedded textures')
    save(R/'DOCUMENTATION/v027_baseline_native_equivalence.json',qa)
    assert qa['native_equivalent'],'Regenerated scenery changes the accepted native EDF; inspect before proceeding'
    return qa

def main():
    result=subprocess.run([sys.executable,str(R/'TOOLS/build_v026.py'),'--source-only'],cwd=R)
    equivalence=None
    if result.returncode:
        old=R/'V024_OUTPUT'
        assert sha(old/'terrain.raw')=='4befe79d6820865f4aba34649a5b54ed22472e7a3c1e7f8d3d56f53f3e340d91'
        assert sha(old/'start.tcl')==EXPECTED['start.tcl']
        checkpoint=read(R/'DOCUMENTATION/v024_source_checkpoint.json');assert checkpoint['source_checks_pass']
        actual=sha(old/'scenery.fbx')
        if actual==EXPECTED['scenery.fbx']:raise RuntimeError('v026 failed after an exact baseline; inspect its original exception')
        equivalence=native_equivalence()
        source=(R/'TOOLS/build_v026.py').read_text();ns={'__name__':'verified_v026','__file__':str(R/'TOOLS/build_v026.py')}
        exec(compile(source,str(R/'TOOLS/build_v026.py'),'exec'),ns,ns);ns['EXPECTED']=dict(ns['EXPECTED'],**{'scenery.fbx':actual})
        argv=sys.argv;sys.argv=['build_v026.py','--source-only','--reuse-baseline']
        try:ns['main']()
        finally:sys.argv=argv
    base=R/'V026_OUTPUT'; actual_sha={fn:sha(base/fn) for fn in EXPECTED}
    for fn in ['terrain.raw','start.tcl']:assert actual_sha[fn]==EXPECTED[fn],fn
    if actual_sha['scenery.fbx']!=EXPECTED['scenery.fbx']:assert equivalence and equivalence['native_equivalent']
    qa=dict(checks_pass=True,accepted_v026_sha256=EXPECTED,actual_source_sha256=actual_sha,
            native_equivalence=equivalence,terrain_and_start_exact=True,
            scenery_exact_source_or_exact_native=True)
    save(base/'baseline_validation.json',qa);save(R/'DOCUMENTATION/v027_baseline_validation.json',qa)
    print('Accepted v026 terrain/start and exact source-or-native scenery proved',flush=True)
if __name__=='__main__':main()
