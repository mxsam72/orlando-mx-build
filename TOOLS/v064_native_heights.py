"""Decode both native height grids, including every new roller sample."""
import json
import numpy as np
from v064_inputs import R,O,TESTED,sha,save
from v057_native_heights import collision_heights,map_heights
from v056_geometry import corner_checks

def validate_native_heights(map_path,trh_path):
 expected=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);tested=np.fromfile(TESTED/'terrain.raw','<u2').reshape(2049,2049)
 assert sha(O/'terrain.raw')=='860350c4c733e5d26939e9e2f40204679ecef302d6e07889f78a849afc8a8fa2'
 collision=collision_heights(trh_path);visual,offset=map_heights(map_path,expected)
 assert np.array_equal(collision,expected) and np.array_equal(visual,expected)
 route=dict(np.load(O/'route.npz'));_,corners=corner_checks(tested,collision,route['q'],route['v054_old_station'])
 assert len(corners)==14 and all(c['raw_grid_exact'] for c in corners)
 scope=np.load(R/'V061_OUTPUT/roller_scope.npy');assert np.array_equal(collision[~scope],tested[~scope]) and np.array_equal(collision[scope],expected[scope])
 assert np.count_nonzero(collision!=tested)==4751
 report=dict(checks_pass=True,native_MAP_entire_grid_exact_source=True,native_TRH_entire_grid_exact_source=True,native_visual_collision_grids_exact=True,
  samples_checked_per_grid=int(expected.size),map_grid_offset=offset,native_all_14_corner_grids_exact_v060=True,wall_roller_visual_and_collision_exact=True,
  terrain_changes_outside_approved_roller=0,samples_differ_from_v060=4751,corners=corners,source_raw_sha256=sha(O/'terrain.raw'),map_sha256=sha(map_path),trh_sha256=sha(trh_path))
 save(O/'native_height_validation.json',report);return report
