"""Resume verified v052 source and scenery; do not repeat source authoring."""
import json,os,shutil,urllib.request,zipfile
from pathlib import Path
from v052_surface import R,O,SPEC,sha,save
from v052_transfer import api,identity,restore,safe,extract,checkpoint,HEADERS

RELEASE=412491281
SOURCE_COMMIT='c3b6d7da13254bff4dd83d98de2f8da54766a3a0'
PINS={
 'OrlandoMX-v052-source-checkpoint.zip':(418055960,'7c49b802a45887fa7a260f2069c5082ff168f03c183985ba6b88ef5cdd83e9ea'),
 'OrlandoMX-v052-native-scenery.zip':(228735599,'1967697ea9e16a6a8ad12c73b1fef10a4d25472fcffac209cc1be35ede41aff3'),
}
class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  out=super().redirect_request(req,fp,code,msg,headers,newurl)
  if out is not None:out.remove_header('Authorization');out.remove_header('Accept')
  return out
def saved():
 identity();rel=api('/releases/'+str(RELEASE));assert rel['draft'] and rel['target_commitish']==SOURCE_COMMIT
 before=sha(SPEC);record=dict(original_source_commit=SOURCE_COMMIT,original_source_release=RELEASE,pinned_saved_assets=PINS)
 for name,(size,digest) in PINS.items():
  asset=next(a for a in rel['assets'] if a['name']==name)
  assert asset['state']=='uploaded' and asset['size']==size and asset['digest']=='sha256:'+digest
  p=R/'BUILD'/name
  req=urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'})
  with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=300) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
  assert p.stat().st_size==size and sha(p)==digest
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   if 'source-checkpoint' in name:
    for i in z.infolist():
     safe(i.filename)
     if not i.is_dir() and i.filename.startswith(('V052_OUTPUT/','V052_SOURCE/','BUILD/v052_review/')):extract(z,i,R/i.filename)
   else:
    extract(z,z.getinfo('scenery.edf'),R/'BUILD/v052_stage/scenery.edf')
    extract(z,z.getinfo('fbx2edf_v052.log'),R/'DOCUMENTATION/fbx2edf_v052.log')
  if 'source-checkpoint' in name:p.unlink()
 assert sha(SPEC)==before
 surface=json.loads((O/'v052_surface_validation.json').read_text())
 grass=json.loads((O/'v052_scenery_validation.json').read_text())
 foliage=json.loads((O/'v052_foliage_validation.json').read_text())
 assert surface['checks_pass'] and surface['grooming_comparison_to_v051']['checks_pass'] and surface['spec']==json.loads(SPEC.read_text())
 assert grass['checks_pass'] and grass['grass_clumps']==4546 and grass['new_verge_clumps']==0
 assert sha(O/'scenery.fbx')==grass['scenery_sha256']
 assert foliage['checks_pass'] and sha(O/'facility_textures'/foliage['specular_map'])==foliage['specular_map_sha256']
 record.update(saved_edf_sha256=sha(R/'BUILD/v052_stage/scenery.edf'),saved_source_scene_sha256=sha(O/'scenery.fbx'),
  source_and_scenery_reused_exact=True,source_views_already_reviewed=True,checks_pass=True)
 save(R/'BUILD/v052_recovery.json',record)
 with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as env:env.write('V052_REUSE_SCENERY=1\n')
 print('Restored the exact reviewed v052 source and successful official scenery export.',flush=True)
def main():
 assert os.name=='nt'
 restore();saved();checkpoint()
if __name__=='__main__':main()
