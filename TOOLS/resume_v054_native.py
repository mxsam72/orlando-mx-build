"""Verify the saved official v054 build without recompiling its native files."""
import os,shutil,urllib.request,zipfile
from pathlib import Path
from v052_transfer import api,identity,HEADERS,safe,extract
from resume_v052 import NoAuthRedirect
from v054_geometry import R,O,DEST,NAME,read,sha,save
from build_windows_v054 import P,LOG,stage,validate

RELEASE=412990475
COMPILE_RUN=38607699127
COMPILE_COMMIT='76696afc917cbb8ade40e391c69ad2b2248cc7fc'
ARTIFACT=11919446532
ARTIFACT_PIN=(129472,'3ee26b905722c54fc582cd00d63b5edf689a0477e4b54fea7aef08008cc9b3f0')
PINS={
 'OrlandoMX-v054-native-scenery.zip':(228735136,'50e3d6ac7a96b9988f5c9cf23ccb3c72fdd7cabe9841fbd4af00b67a74e8e8ed'),
 'OrlandoMX_2026_v054.pkz':(920767498,'3d3324a29d488ddb49ae53454cc948cfb7a673ca308dbd8518410a03cb773e21'),
 'OrlandoMX_2026_v054.pkz.sha256':(91,'a7a8185def394205e5f2b22cccac72657e3e188cc1e3ae0f56aa9de1ef57b066'),
 'native_compile_results.json':(515,'edff02ad04b5c4b05471f043f21977432537aa28eedf9a6aa9cc9697dc0ec6b9'),
}

def download(url,p,pin):
 p.parent.mkdir(parents=True,exist_ok=True)
 req=urllib.request.Request(url,headers=HEADERS|{'Accept':'application/octet-stream'})
 with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=300) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
 assert p.stat().st_size==pin[0] and sha(p)==pin[1],('Saved build pin mismatch',p.name)
 print('Recovered exact saved native asset',p.name,p.stat().st_size,flush=True)
 return p

def main():
 identity();rel=api('/releases/'+str(RELEASE));assert rel['draft'] and rel['tag_name']=='v054-start-corners-38605191325'
 recovery=read(R/'BUILD/v054_recovery.json');assert recovery['reviewed_source_recovered_exact'] and recovery['descriptor']['source_commit']=='03b21cb68c34366ddc0f8a8a63995f9b31abc528'
 textures,normals=stage();assets={a['name']:a for a in rel['assets']};paths={}
 for name,pin in PINS.items():
  a=assets[name];assert a['state']=='uploaded' and a['size']==pin[0] and a['digest']=='sha256:'+pin[1]
  dest=R/('12_RELEASE' if name.endswith(('.pkz','.sha256')) else 'BUILD')/name
  paths[name]=download(a['url'],dest,pin)
 artifact=api('/actions/artifacts/'+str(ARTIFACT));assert not artifact['expired'] and artifact['workflow_run']['id']==COMPILE_RUN
 assert artifact['size_in_bytes']==ARTIFACT_PIN[0] and artifact['digest']=='sha256:'+ARTIFACT_PIN[1]
 diagnostic=download(artifact['archive_download_url'],R/'BUILD/v054_saved_native_validation.zip',ARTIFACT_PIN)
 required={f'DOCUMENTATION/{n}.log' for n in ['fbx2edf_v054','terrained_trh_v054','tracked_merge_v054','terrained_map_v054']}|{'V054_OUTPUT/native_scenery_preflight.json'}
 with zipfile.ZipFile(diagnostic) as z:
  assert z.testzip() is None and required<=set(z.namelist())
  for name in required:safe(name);extract(z,z.getinfo(name),R/name)
 assert read(O/'native_scenery_preflight.json')['checks_pass'] and 'Map File Write' in (LOG/'terrained_map_v054.log').read_text()
 with zipfile.ZipFile(paths['OrlandoMX-v054-native-scenery.zip']) as z:
  assert z.testzip() is None and set(z.namelist())=={'scenery.edf','fbx2edf_v054.log'}
  extract(z,z.getinfo('scenery.edf'),P/'scenery.edf')
  assert z.read('fbx2edf_v054.log')==(LOG/'fbx2edf_v054.log').read_bytes()
 assert (P/'scenery.edf').read_bytes()[:4]==b'EDF\0'
 pkz=paths['OrlandoMX_2026_v054.pkz']
 assert paths['OrlandoMX_2026_v054.pkz.sha256'].read_text().split()==[PINS[pkz.name][1],pkz.name]
 source_files={p.name for p in DEST.iterdir() if p.is_file() and p.suffix not in ['.map','.trh'] and p.name!='code.txt'}
 with zipfile.ZipFile(pkz) as z:
  assert len(z.infolist())==13 and z.testzip() is None
  for i in z.infolist():
   safe(i.filename);parts=Path(i.filename).parts
   assert len(parts)==2 and parts[0]==NAME and not i.is_dir()
  non_native={Path(i.filename).name for i in z.infolist() if Path(i.filename).suffix not in ['.map','.trh']}
  assert non_native==source_files,('Saved package/source file set mismatch',non_native,source_files)
  for i in z.infolist():
   p=DEST/Path(i.filename).name
   if p.suffix not in ['.map','.trh']:assert p.read_bytes()==z.read(i),('Saved native package source drift',p.name)
   extract(z,i,p)
 assert (DEST/(NAME+'.map')).read_bytes()[:2]==b'MP' and (DEST/(NAME+'.trh')).read_bytes()[:3]==b'TRH'
 native=read(paths['native_compile_results.json'])
 assert all(native[k]['returncode']==0 for k in ['scenery','collision','centreline','terrain'])
 save(O/'native_compile_results.json',native)
 save(R/'BUILD/v054_native_reuse.json',dict(checks_pass=True,compiled_run=COMPILE_RUN,compiled_commit=COMPILE_COMMIT,source_release_id=RELEASE,pinned_assets=PINS,diagnostic_artifact=ARTIFACT,diagnostic_sha256=ARTIFACT_PIN[1],reviewed_source_recovered_exact=True,non_native_package_files_match_reviewed_source=True,pkz_crc_root_and_13_files_checked=True,native_outputs_reused_without_modification=True))
 os.environ['V054_NATIVE_COMPILE_RUN']=str(COMPILE_RUN);os.environ['V054_NATIVE_COMPILE_COMMIT']=COMPILE_COMMIT
 validate(textures,normals,native,pkz)

if __name__=='__main__':main()
