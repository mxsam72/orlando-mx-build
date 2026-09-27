#!/usr/bin/env python3
"""Compile only v009 with the project's hash-pinned official PiBoSo tools."""
from pathlib import Path
import os,shutil,json,hashlib
R=Path(__file__).resolve().parents[1];W=R/'BUILD/v009_work';O=R/'V009_OUTPUT';NAME='orlandomx_2026_v009'
def main():
 if os.name!='nt':raise SystemExit('Native compiler requires Windows. Use BUILD_V009_LOCAL.bat or the v009 GitHub Windows workflow.')
 qa=json.loads((R/'DOCUMENTATION/v009_geometry_validation.json').read_text(encoding='utf-8'));release=json.loads((R/'DOCUMENTATION/v009_release_validation.json').read_text(encoding='utf-8'))
 if not qa.get('geometry_checks_pass') or not release.get('v008b_texture_hashes_preserved'):raise RuntimeError('v009 precompile QA missing or failed')
 source=(R/'TOOLS/build_windows.py').read_text(encoding='utf-8');old="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'"
 if source.count(old)!=1:raise RuntimeError('Validated native builder changed')
 source=source.replace(old,"destination=V009_REPO/'12_RELEASE/OrlandoMX_2026_v009.pkz'").replace("ROOT/'BUILD/native_coordinate_probes.json'","V009_REPO/'V009_OUTPUT/native_coordinate_probes.json'")
 ns={'__name__':'v009_native','__file__':__file__,'V009_REPO':R};exec(compile(source,str(R/'TOOLS/build_windows.py'),'exec'),ns,ns)
 ns.update(ROOT=W,NAME=NAME,LOG=R/'DOCUMENTATION',STAGE=R/'BUILD/v009_stage',OUT=R/'12_RELEASE'/NAME);orig_stage=ns['stage']
 def stage():
  stagepath=ns['STAGE']
  if stagepath.exists():shutil.rmtree(stagepath)
  orig_stage();shutil.copy2(O/'terrain.raw',stagepath/'terrain.raw');shutil.copy2(O/'scenery.fbx',stagepath/'scenery.fbx')
  for p in (O/'visual_masks').glob('*.tga'):shutil.copy2(p,stagepath/('mask_'+p.name))
  assert hashlib.sha256((stagepath/'terrain.raw').read_bytes()).hexdigest()==qa['raw_sha256']
 ns['stage']=stage
 try:ns['main']()
 except Exception as e:
  (R/'DOCUMENTATION/v009_native_failure.txt').write_text(str(e)+'\n', encoding='utf-8');raise
 v=json.loads((R/'DOCUMENTATION/native_build_validation.json').read_text(encoding='utf-8'));v.update(version='v009',geometry_source_sha256=qa['raw_sha256'],in_game_riding_test=False)
 (R/'DOCUMENTATION/v009_native_validation.json').write_text(json.dumps(v,indent=2)+'\n', encoding='utf-8');shutil.copy2(R/'DOCUMENTATION/v009_native_validation.json',R/'12_RELEASE/OrlandoMX_v009_Validation.json')
 (R/'12_RELEASE/Install_v009.txt').write_text('Orlando MX 2026 v009 - geometry candidate\n\nCopy OrlandoMX_2026_v009.pkz to:\nDocuments\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\\n\nDo not extract or rename. Select Orlando MX 2026 v009 in game.\nEarlier versions remain separate. Native compilation and static QA passed; in-game rider validation remains required.\n', encoding='utf-8')
 print('v009 native package complete. In-game ride test pending.')
if __name__=='__main__':main()
