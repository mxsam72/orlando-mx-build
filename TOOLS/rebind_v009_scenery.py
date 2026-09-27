#!/usr/bin/env python3
"""Run the validated FBX vertex-rebind algorithm against v008b and v009."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 source=(R/'TOOLS/rebind_scenery.py').read_text(encoding='utf-8')
 replacements={"ROOT/'BUILD/v006_scenery.fbx'":"ROOT/'BUILD/v009_baseline/scenery.fbx'","ROOT/'BUILD/v006_terrain.raw'":"ROOT/'BUILD/v009_baseline/terrain.raw'","ROOT/'02_HEIGHTMAP/terrain.raw'":"ROOT/'V009_OUTPUT/terrain.raw'","ROOT/'07_OBJECTS_SOURCE/scenery.fbx'":"ROOT/'V009_OUTPUT/scenery.fbx'","ROOT/'V007_SOURCE/scenery_patch.json'":"ROOT/'V009_OUTPUT/scenery_patch.json'","ROOT/'BUILD/native_coordinate_probes.json'":"ROOT/'V009_OUTPUT/native_coordinate_probes.json'","ROOT/'DOCUMENTATION/v007_scenery_validation.json'":"ROOT/'DOCUMENTATION/v009_scenery_validation.json'"}
 for old,new in replacements.items():
  if old not in source:raise RuntimeError('Validated scenery script changed: '+old)
  source=source.replace(old,new)
 ns={'__name__':'__main__','__file__':__file__};exec(compile(source,__file__,'exec'),ns,ns)
if __name__=='__main__':main()
