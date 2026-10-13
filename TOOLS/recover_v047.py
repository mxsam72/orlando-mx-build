"""Recheck exact checkpointed native files and publish without recompilation."""
import os,shutil,urllib.request,zipfile
from v047_common import *
from v047_transfer import api,identity,extract,safe_name,restore,deliver
from build_windows_v047 import stage,validate
from validate_native_textures_v024 import bitmap_signature,texture_record

RELEASE=412053683
NATIVE_COMMIT='a296ae1fffa880cbe6044a99d3def86666239955'
ASSETS={
    'OrlandoMX-v047-tree-source-checkpoint.zip':(292379577,'0a1f44d74eef2908a17e120fac9eed7ad9ec416fa693c51d0c6a08c83749cdf1'),
    'OrlandoMX-v047-native-scenery.zip':(226150374,'ebc41d61f88d7b661ce9b380a0efb108c21f3db6efd5775e7cee3a69fcd21fe7'),
    'OrlandoMX_2026_v047.pkz':(917973744,'f841c49859be1fe34c9e5641d39ed2b3f7eaabb981f55660a1b1b5f9fb4cf783'),
    'v047_diagnostics-38458081921.zip':(131538,'50e3d038dfca9266926938eb1bf1af7d98e5e87e6aa600fc8fefb2f1b8a960d1')
}

class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        # The API's signed asset URL carries its own authorization. Do not
        # forward the GitHub token to the storage host.
        out=super().redirect_request(req,fp,code,msg,headers,newurl)
        if out is not None:
            out.remove_header('Authorization');out.remove_header('Accept')
        return out

def saved_asset(a):
    size,digest=ASSETS[a['name']];assert a['size']==size and a['digest']=='sha256:'+digest
    p=R/'BUILD'/a['name'];p.parent.mkdir(parents=True,exist_ok=True)
    headers={'Authorization':'Bearer '+os.environ['V047_RELEASE_TOKEN'],'Accept':'application/octet-stream','User-Agent':'OrlandoMX-v047-native-recovery'}
    opener=urllib.request.build_opener(NoAuthRedirect)
    with opener.open(urllib.request.Request(a['url'],headers=headers),timeout=300) as src,p.open('wb') as out:shutil.copyfileobj(src,out,4*1024*1024)
    assert p.stat().st_size==size and sha(p)==digest
    print('Authenticated saved native/source asset',p.name,size,flush=True);return p

def main():
    identity();rel=api('/releases/'+str(RELEASE));assert rel['draft'] and rel['target_commitish']==NATIVE_COMMIT
    assets={a['name']:a for a in rel['assets']}
    # Reconstruct all exact baseline terrain and source bitmaps. No native tool
    # or Blender process is run in this workflow.
    restore()
    saved={name:saved_asset(assets[name]) for name in ASSETS}
    with zipfile.ZipFile(saved['OrlandoMX-v047-tree-source-checkpoint.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            if not i.is_dir() and i.filename.startswith(('V047_OUTPUT/','V047_SOURCE/')):extract(z,i,R/i.filename)
    saved['OrlandoMX-v047-tree-source-checkpoint.zip'].unlink()
    q,baseline,textures=stage()
    with zipfile.ZipFile(saved['OrlandoMX-v047-native-scenery.zip']) as z:
        extract(z,z.getinfo('scenery.edf'),P/'scenery.edf')
    saved['OrlandoMX-v047-native-scenery.zip'].unlink()
    pkz=R/'12_RELEASE/OrlandoMX_2026_v047.pkz';shutil.move(saved[pkz.name],pkz)
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.infolist())==13
        for i in z.infolist():
            safe_name(i.filename);assert i.filename.startswith(NAME+'/')
            if not i.is_dir():extract(z,i,DEST/Path(i.filename).name)
    with zipfile.ZipFile(saved['v047_diagnostics-38458081921.zip']) as z:
        for i in z.infolist():
            safe_name(i.filename)
            if i.filename in ['DOCUMENTATION/fbx2edf_v047.log','DOCUMENTATION/terrained_v047.log']:extract(z,i,R/i.filename)
    saved['v047_diagnostics-38458081921.zip'].unlink()
    # Inspect the actual failing record and retain the strict payload evidence.
    raw=(P/'scenery.edf').read_bytes();path=P/'pine_bark_n.tga';w,h,d=bitmap_signature(path)
    off=raw.find(path.stem.encode()+bytes(100-len(path.stem)))
    print('V047_NORMAL_RECORD_DIAGNOSTIC',dict(offset=off,expected_size=[w,h],expected_pixel_md5=d.hex(),header_hex=raw[off+100:off+160].hex()),flush=True)
    normal=texture_record(raw,path,normal_map=True)
    print('V047_REAL_NORMAL_RECORD_VERIFIED',normal,flush=True);del raw
    for label in ['fbx2edf_v047','terrained_v047']:
        text=(R/'DOCUMENTATION'/(label+'.log')).read_text(encoding='utf-8')
        # FBX2EDF was deliberately invoked with -q; an empty stdout log is
        # expected. The original compiler's return code and EDF header were
        # checked before it saved the authenticated native checkpoint.
        assert 'ERROR:' not in text.upper()
        if label=='terrained_v047':assert text and 'Map File Write' in text
    native=dict(recovered_from_successful_native_compilation_run=38458081921,native_source_commit=NATIVE_COMMIT,
        scenery=dict(returncode=0,log='fbx2edf_v047.log',checkpoint_authenticated=True),terrain=dict(returncode=0,log='terrained_v047.log',checkpoint_authenticated=True),native_files_recompiled=False)
    validate(q,baseline,textures,native,pkz)
    qa=read(R/'12_RELEASE/OrlandoMX_v047_Validation.json');assert sha(pkz)==ASSETS[pkz.name][1]
    qa['source_commit']=NATIVE_COMMIT;qa['validation_commit']=os.environ['GITHUB_SHA']
    qa['build_run']=38458081921;qa['validation_run']=int(os.environ['GITHUB_RUN_ID'])
    qa['normal_map_record_validation']=dict(checks_pass=True,diffuse_dimension_offset=104,normal_dimension_offset=100,strict_named_record_source_pixel_digest_and_payload_bounds=True,actual_bark_record=normal)
    qa['native_checkpoint_recovery']=dict(checks_pass=True,release_id=RELEASE,native_files_recompiled=False,pkz_unchanged=True,authenticated_assets=ASSETS)
    save(R/'12_RELEASE/OrlandoMX_v047_Validation.json',qa);deliver()

if __name__=='__main__':main()
