"""Publish a clearly marked test release only after native validation passes."""
from pathlib import Path
import hashlib,json,os,urllib.parse,urllib.request
R=Path(__file__).resolve().parents[1];API='https://api.github.com/repos/mxsam72/orlando-mx-build';TOKEN=os.environ['GITHUB_TOKEN'];HEADERS={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'Moon-MX-v002-build'}
def api(path,data=None):
 req=urllib.request.Request(API+path,data=None if data is None else json.dumps(data).encode(),headers=HEADERS|({'Content-Type':'application/json'} if data is not None else {}))
 with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
def main():
 v=json.loads((R/'Moon_v002_Validation.json').read_text());pkz=R/'Taurus_Littrow_MX_v002.pkz';assert v['compiled'] and v['checks_pass'] and v['native_height_validation']['checks_pass'];assert hashlib.sha256(pkz.read_bytes()).hexdigest()==v['pkz_sha256']
 tag='moon-v002-test-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
 release=api('/releases',dict(tag_name=tag,target_commitish=os.environ['GITHUB_SHA'],name='Taurus-Littrow MX v002 — half-gravity test',prerelease=True,draft=False,make_latest='false',body='First native Moon track test candidate, around mapped Shorty crater in Taurus-Littrow. LROC terrain, gray regolith materials, low broad rollers, a compact pit apron/access lane and eight start/pit positions. Native authoring, texture/geometry/height checks passed; actual game loading, riding, timing, appearance and FPS still require testing. Use the separately installed MXB Quiet Gravity v4 with preset=half in single-player Testing. This track does not change gravity itself. The physical Moon has lower gravity than this gameplay preset. No multiplayer support is claimed. Source renders are not game screenshots.'))
 files=[pkz,R/'Taurus_Littrow_MX_v002.pkz.sha256',R/'Moon_v002_Validation.json',R/'Install_Moon_v002.txt',R/'mxb_gravity_quiet.ini',R/'Moon_v002_Previews.zip']
 for p in files:
  data=p.read_bytes();url=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':p.name});request=urllib.request.Request(url,data=data,method='POST',headers=HEADERS|{'Content-Type':'application/octet-stream','Content-Length':str(len(data))})
  with urllib.request.urlopen(request,timeout=900) as response:asset=json.load(response)
  assert asset['size']==len(data) and asset['digest']=='sha256:'+hashlib.sha256(data).hexdigest()
 (R/'v002_delivery.json').write_text(json.dumps(dict(release_url=release['html_url'],pkz_sha256=v['pkz_sha256'],pkz_bytes=v['pkz_bytes']),indent=2)+'\n')
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as out:out.write('[Download Moon v002 test track]('+release['html_url']+')\n')
 print('MOON_V002_RELEASE',release['html_url'],flush=True)
if __name__=='__main__':main()
