"""Verify every native visual/collision sample against unchanged v064 RAW."""
import numpy as np
from v065_inputs import O,sha,save,TERRAIN_SHA
from v057_native_heights import collision_heights,map_heights

def validate_native_heights(map_path,trh_path):
 expected=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);assert sha(O/'terrain.raw')==TERRAIN_SHA
 collision=collision_heights(trh_path);visual,offset=map_heights(map_path,expected)
 assert np.array_equal(collision,expected) and np.array_equal(visual,expected)
 report=dict(checks_pass=True,native_MAP_entire_grid_exact_source=True,native_TRH_entire_grid_exact_source=True,
  native_visual_collision_grids_exact=True,samples_checked_per_grid=int(expected.size),map_grid_offset=offset,
  native_all_14_corner_grids_exact_v064=True,wall_roller_visual_and_collision_exact=True,
  source_raw_sha256=TERRAIN_SHA,map_sha256=sha(map_path),trh_sha256=sha(trh_path))
 save(O/'native_height_validation.json',report);return report
