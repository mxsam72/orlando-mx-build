"""Restore saved v051 authoring, bake native grass colour and resume compiling."""
import hashlib,os,shutil,struct,urllib.request,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from v051_surface import R,O,M,sha,save
from v051_transfer import api,identity,restore,safe,extract,checkpoint
from v051_scenery import F,TEXTURE,COLOUR_MULTIPLIER,TINT
from v027_scenery import parse,values,fingerprint,child
from v037_fbx import setvalues
from v047_scenery import encode_linear

SAVED_RELEASE=412344816
SAVED_COMMIT='e600172967c0f23e3e447acdd522b0dcbc51ec5f'
SAVED_SIZE=430879619
SAVED_SHA='86749c3ac3e31caea60d68e52b08c3eca3e1f1fb5903355cc8192a4d40ebe7f2'

class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  out=super().redirect_request(req,fp,code,msg,headers,newurl)
  if out is not None:out.remove_header('Authorization');out.remove_header('Accept')
  return out

def saved_source():
 identity();rel=api('/releases/'+str(SAVED_RELEASE));assert rel['draft'] and rel['target_commitish']==SAVED_COMMIT
 a=next(a for a in rel['assets'] if a['name']=='OrlandoMX-v051-source-checkpoint.zip')
 assert a['size']==SAVED_SIZE and a['digest']=='sha256:'+SAVED_SHA
 p=R/'BUILD/v051_saved_source.zip';p.parent.mkdir(exist_ok=True)
 headers={'Authorization':'Bearer '+os.environ['V051_RELEASE_TOKEN'],'Accept':'application/octet-stream','User-Agent':'OrlandoMX-v051-resume'}
 with urllib.request.build_opener(NoAuthRedirect).open(urllib.request.Request(a['url'],headers=headers),timeout=300) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst,4*1024*1024)
 assert p.stat().st_size==SAVED_SIZE and sha(p)==SAVED_SHA
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for i in z.infolist():
   safe(i.filename)
   if not i.is_dir() and i.filename.startswith(('V051_OUTPUT/','V051_SOURCE/','BUILD/v051_review/')):extract(z,i,R/i.filename)
 p.unlink()
 print('Authenticated saved v051 surface, grass geometry and comparison views.',flush=True)

def bake_colour():
 q=__import__('json').loads((O/'v051_scenery_validation.json').read_text());assert q['checks_pass'] and q['all_non_grass_records_exact']
 scene=O/'scenery.fbx';photo=F/TEXTURE;assert sha(scene)==q['scenery_sha256'] and sha(photo)==q['photographic_texture_sha256']
 rgba=np.array(Image.open(photo).convert('RGBA'));alpha=rgba[:,:,3].copy()
 rgba[:,:,:3]=np.uint8(np.rint(np.clip(rgba[:,:,:3].astype(np.float32)*np.array(COLOUR_MULTIPLIER),0,255)))
 assert np.array_equal(alpha,rgba[:,:,3]);Image.fromarray(rgba).save(photo,format='TGA');raw=photo.read_bytes()
 nodes,tail=parse(scene.read_bytes());objects=next(n for n in nodes if n['name']==b'Objects')['children']
 before={values(n)[0]:fingerprint(n) for n in objects};changed=set();stem=TEXTURE[:-4].encode()
 for n in objects:
  v=values(n)
  if n['name'] not in [b'Material',b'Video'] or len(v)<2 or v[1].split(b'\0')[0]!=stem:continue
  changed.add(v[0])
  if n['name']==b'Video':
   c=child(n,b'Content');assert c;c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
  else:
   for pp in child(n,b'Properties70')['children']:
    vv=values(pp)
    if vv and vv[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(pp,*vv[:4],*TINT)
 assert len(changed)==2
 encoded=encode_linear(nodes,tail);expected_digest=hashlib.sha256(encoded).hexdigest()
 temp=scene.with_suffix('.fbx.tmp')
 with temp.open('wb') as f:
  for start in range(0,len(encoded),4*1024*1024):
   block=memoryview(encoded)[start:start+4*1024*1024];assert f.write(block)==len(block)
 assert temp.stat().st_size==len(encoded) and sha(temp)==expected_digest
 after=parse(temp.read_bytes())[0];temp.replace(scene)
 got={values(n)[0]:fingerprint(n) for n in next(n for n in after if n['name']==b'Objects')['children']}
 assert all(got[i]==f for i,f in before.items() if i not in changed),'Saved grass or retained geometry changed'
 mips=[]
 for n in [256,64,16,4,1]:
  rgb=np.asarray(Image.fromarray(rgba[:,:,:3]).resize((n,n),Image.Resampling.BOX),np.float32);mean=rgb.mean((0,1))
  assert mean[1]>mean[0]*1.35 and mean[1]>mean[2]*1.6 and mean[1]>75
  mips.append(dict(size=n,tinted_rgb_mean=mean.tolist(),green_dominant=True))
 q.update(scenery_sha256=sha(scene),photographic_texture_sha256=sha(photo),photographic_material_tint_rgb=TINT,
  photographic_colour_multiplier_baked=COLOUR_MULTIPLIER,photo_opaque_rgb_unchanged=False,photo_alpha_unchanged=True,
  colour_method='Intended green colour multiplier baked into photographic RGB; native material stays white',distance_mip_colour_validation=mips,
  saved_geometry_reused_exact=True,restored_source_release=SAVED_RELEASE)
 save(O/'v051_scenery_validation.json',q)
 save(O/'v051_colour_recovery.json',dict(checks_pass=True,original_source_commit=SAVED_COMMIT,original_source_checkpoint_sha256=SAVED_SHA,
  geometry_unchanged=True,all_non_grass_objects_unchanged=True,only_grass_material_and_photo_video_changed=True,
  photographic_alpha_unchanged=True,green_colour_baked=True))
 print('Baked green photographic RGB; every saved geometry record remains exact.',flush=True)

def main():
 assert os.name=='nt'
 restore();saved_source();bake_colour()
 # Do not overwrite preserved source geometry, surface or comparison renders.
 # Save the corrected source before official native compilation resumes.
 checkpoint()
if __name__=='__main__':main()
