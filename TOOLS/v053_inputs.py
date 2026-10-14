"""Restore the delivered v052 scenery and approved source with pinned digests."""
import json,os,shutil,urllib.request,zipfile
from pathlib import Path
from v053_surface import R,BASE,DIRT,O,PREVIOUS,SPEC,sha,save
from v052_transfer import restore as baseline_restore,api,identity,HEADERS,safe,extract
from resume_v052 import NoAuthRedirect

RELEASE=412509917
COMMIT='109bf8469e09d9653898f975c906729e1ca53530'
PINS={
 'OrlandoMX-v052-source-checkpoint.zip':(418060442,'402566cd10ae9b724cadaf67ea2377cdc25f062fda563828b11ffc390a094c31'),
 'OrlandoMX-v052-native-scenery.zip':(228735599,'1967697ea9e16a6a8ad12c73b1fef10a4d25472fcffac209cc1be35ede41aff3'),
 'OrlandoMX_v052_Validation.json':(112355,'0742a0464dca264295d1d52035aeb87702ec0b3e84ee51fd5b54e304c6b3fa06'),
}
def restore():
    baseline_restore(); identity(); rel=api('/releases/'+str(RELEASE))
    assert not rel['draft'] and rel['target_commitish']==COMMIT
    before=sha(SPEC)
    for name,(size,digest) in PINS.items():
        asset=next(a for a in rel['assets'] if a['name']==name)
        assert asset['state']=='uploaded' and asset['size']==size and asset['digest']=='sha256:'+digest
        p=R/'BUILD'/name
        req=urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'})
        with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=300) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
        assert p.stat().st_size==size and sha(p)==digest
        if p.suffix!='.zip':continue
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            if 'source-checkpoint' in name:
                for i in z.infolist():
                    safe(i.filename)
                    if not i.is_dir() and i.filename.startswith(('V052_OUTPUT/','V052_SOURCE/')):extract(z,i,R/i.filename)
            else:
                extract(z,z.getinfo('scenery.edf'),R/'BUILD/v053_stage/scenery.edf')
                extract(z,z.getinfo('fbx2edf_v052.log'),R/'DOCUMENTATION/fbx2edf_v053.log')
        if 'source-checkpoint' in name:p.unlink()
    qa=json.loads((R/'BUILD/OrlandoMX_v052_Validation.json').read_text())
    assert qa['compiled'] and qa['source_checks'] and qa['native_trh_identical_to_v050']
    assert qa['pkz_sha256']=='6a874fefa8bce42044e976a3e32e8d3c25c869b82e01e437c23901e3436d3a64'
    assert sha(SPEC)==before and sha(R/'BUILD/v053_stage/scenery.edf')==qa['scenery_edf_sha256']
    surface=json.loads((PREVIOUS/'v052_surface_validation.json').read_text())
    for name,row in surface['files'].items():assert sha(PREVIOUS/name)==row['sha256'],name
    assert sha(PREVIOUS/'scenery.fbx')==qa['grass_validation']['scenery_sha256']
    shutil.copytree(PREVIOUS,O,dirs_exist_ok=True)
    # Reports describe retained v052 assets. Preserve their contents exactly;
    # the v053 delivery validator also records their origin and byte digests.
    for name in ['scenery_validation','native_probes','layer_trials','verge_validation','foliage_validation']:
        shutil.copy2(PREVIOUS/('v052_'+name+'.json'),O/('v053_'+name+'.json'))
    save(R/'BUILD/v053_recovery.json',dict(checks_pass=True,original_source_release=RELEASE,original_source_commit=COMMIT,
        pinned_saved_assets=PINS,saved_edf_sha256=sha(R/'BUILD/v053_stage/scenery.edf'),saved_source_scene_sha256=sha(O/'scenery.fbx'),
        scenery_reused_exact=True,matte_foliage_reused_exact=True,grass_reused_exact=True,baseline_v052_pkz_sha256=qa['pkz_sha256']))
    shutil.copy2(R/'BUILD/v052_input_validation.json',R/'BUILD/v053_input_validation.json')
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as env:env.write('V053_REUSE_SCENERY=1\n')
    print('Restored delivered v052 grass, foliage, scene and official EDF exactly.',flush=True)
if __name__=='__main__':restore()
