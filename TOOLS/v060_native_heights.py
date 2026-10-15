"""Compare every native height sample with the approved v059/v060 source."""
import numpy as np
from v060_inputs import R,PREV,O,sha,save
from v057_native_heights import collision_heights,map_heights
from v056_geometry import corner_checks

def validate_native_heights(map_path,trh_path):
 expected=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)
 accepted=np.fromfile(PREV/'terrain.raw','<u2').reshape(2049,2049)
 assert np.array_equal(expected,accepted),'Density edit changed the accepted geometry'
 collision=collision_heights(trh_path);visual,offset=map_heights(map_path,expected)
 assert np.array_equal(collision,expected) and np.array_equal(visual,expected)
 route=dict(np.load(PREV/'route.npz'))
 _,corners=corner_checks(accepted,collision,route['q'],route['v054_old_station'])
 assert len(corners)==14 and all(c['raw_grid_exact'] for c in corners)
 tested=np.fromfile(R/'V056_OUTPUT/terrain.raw','<u2').reshape(2049,2049)
 report=dict(checks_pass=True,native_MAP_entire_grid_exact_source=True,native_TRH_entire_grid_exact_source=True,
  native_visual_collision_grids_exact=True,samples_checked_per_grid=int(expected.size),map_grid_offset=offset,
  native_all_14_corner_grids_exact_v059=True,entire_native_ground_exact_v059=True,corners=corners,
  samples_differ_from_v056=int(np.count_nonzero(collision!=tested)),source_raw_sha256=sha(O/'terrain.raw'),
  map_sha256=sha(map_path),trh_sha256=sha(trh_path))
 save(O/'native_height_validation.json',report);return report
