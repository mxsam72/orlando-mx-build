#!/usr/bin/env python3
"""Restore v008b in a private v009 work directory, with exactly-once correction."""
from pathlib import Path
import json,hashlib,shutil,subprocess,sys
R=Path(__file__).resolve().parents[1];WORK=R/'BUILD/v009_work';BASE=R/'BUILD/v009_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((R/'V009_SOURCE/baseline_manifest.json').read_text(encoding='utf-8'));marker=WORK/'v009_baseline_ready.json'
 valid=marker.exists()
 for name,h in [('02_HEIGHTMAP/terrain.raw',m['terrain_sha256']),('07_OBJECTS_SOURCE/scenery.fbx',m['scenery_sha256']),*[(f'04_TEXTURES/{n}',h) for n,h in m['texture_sha256'].items()]]:
  p=WORK/name;valid=valid and p.is_file() and sha(p)==h
 if not valid:
  WORK.mkdir(parents=True,exist_ok=True)
  for name in ['BUILD_INPUTS','BUILD_V007','BUILD_V008','TOOLS']:shutil.copytree(R/name,WORK/name,dirs_exist_ok=True)
  (WORK/'BUILD').mkdir(exist_ok=True)
  for name in ['track.tht','track.hmf','map_params.ini','trh_params.ini','edf_params.ini','tool_versions.json','native_coordinate_probes.json']:shutil.copy2(R/'BUILD'/name,WORK/'BUILD'/name)
  for script in ['unpack_inputs.py','prepare_v008_local.py','v008b_visual_fix.py']:subprocess.run([sys.executable,str(WORK/'TOOLS'/script)],check=True,cwd=WORK)
  assert sha(WORK/'02_HEIGHTMAP/terrain.raw')==m['terrain_sha256']
  assert sha(WORK/'07_OBJECTS_SOURCE/scenery.fbx')==m['scenery_sha256']
  for n,h in m['texture_sha256'].items():assert sha(WORK/'04_TEXTURES'/n)==h,n
  marker.write_text(json.dumps(m,indent=2)+'\n', encoding='utf-8')
 BASE.mkdir(exist_ok=True)
 for src,dst in [('02_HEIGHTMAP/terrain.raw','terrain.raw'),('07_OBJECTS_SOURCE/scenery.fbx','scenery.fbx'),('BUILD/native_coordinate_probes.json','native_coordinate_probes.json')]:shutil.copy2(WORK/src,BASE/dst)
 print('Isolated v008b baseline verified; no correction reapplied to corrected inputs.')
if __name__=='__main__':main()
