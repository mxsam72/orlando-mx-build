"""Publish the validated v003 test candidate without rerunning native authoring."""
import json,os,sys,urllib.error,urllib.parse,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1];R=V.parents[1]
sys.path.insert(0,str(R/'MOON/scripts'))
from publish_test import api,upload_files
from native_v003 import NAME,PACKAGE,context,package_identity,n

def main():
    report=json.loads((V/'Moon_v003_Validation.json').read_text());pkz=V/(NAME+'.pkz')
    assert all(report[k]==v for k,v in context().items()),'Published package provenance mismatch'
    assert report['compiled'] and report['checks_pass'] and report['native_height_validation']['checks_pass']
    assert report['source_baked_terrain_shadows'] and report['native_shadowmaps'] is False
    assert report['native_compilers']['sky']['checks_pass'] and len(report['native_compilers']['sky']['textures'])==2
    assert report['centerline_merged'] and n.sha(pkz)==report['pkz_sha256']
    assert not any(report[k] for k in ['in_game_load_test','in_game_riding_test','in_game_visual_check','multiplayer_supported'])
    with zipfile.ZipFile(pkz) as z:assert z.testzip() is None;package_identity(pkz.name,z.namelist())
    tag='moon-v003-crater-send-'+os.environ['GITHUB_RUN_ID']
    body='''Six giant fictional crater jumps in the mapped Taurus–Littrow lunar setting: 90, 160, 120, 175, 110 and 140 m gaps. Optional 220 m Shorty transfer, broad landings, crater bypasses, gray regolith, original stars and a prominent blue NASA Earth. Small rollers removed. Designed around the separate Quiet Gravity half preset (4.905 m/s²).

Download taurus_littrow_mx_v003.pkz without renaming it. Copy it into your active MX Bikes mods/tracks/motocross folder, restart the game and select Taurus-Littrow Crater Send v003. Use single-player Testing for the first ride; suggested bike 450, weather Clear, gravity preset half. Read Install_Moon_v003.txt for lip speeds.

Native compilation, source/collision/visual height equality, coordinate and texture checks passed. The track has not yet been loaded or ridden in game. The previews are renders of the exported source assets, not game screenshots. Point-mass flight checks do not establish actual bike handling or rideability. No multiplayer compatibility is claimed.

Terrain shadows are a static source-baked occlusion texture; the slow native shadow bake is disabled. New sky and scenery are included; KBOLTZ MOONED was a visual/technical reference and its assets are not redistributed. Earth image: NASA / Reto Stöckli / Robert Simmon / MODIS Science Team. Earth size/placement and visible stars are artistic. The track does not change gravity itself.'''
    try:release=api('/releases/tags/'+urllib.parse.quote(tag,safe=''))
    except urllib.error.HTTPError as exc:
        if exc.code!=404:raise
        release=api('/releases',dict(tag_name=tag,target_commitish=os.environ['GITHUB_SHA'],name='Taurus-Littrow Crater Send v003 — giant crater test',prerelease=True,draft=False,make_latest='false',body=body))
    assert release['tag_name']==tag and release['target_commitish']==os.environ['GITHUB_SHA'] and release['prerelease']
    upload_files(release,PACKAGE)
    n.save(V/'Moon_v003_Delivery.json',dict(release_url=release['html_url'],pkz_sha256=report['pkz_sha256'],pkz_bytes=report['pkz_bytes']))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as out:out.write('[Download Crater Send v003 test track]('+release['html_url']+')\n')
    print('V003_RELEASE_PUBLISHED',release['html_url'],flush=True)
if __name__=='__main__':main()
