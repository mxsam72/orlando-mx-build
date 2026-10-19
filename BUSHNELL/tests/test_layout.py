from pathlib import Path
import importlib.util,json,unittest
import numpy as np
R=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('bushnell_builder',R/'scripts/build_source.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class LayoutTests(unittest.TestCase):
 def test_accepted_loop_and_eight_sources(self):
  c,d,q=b.load_project();self.assertEqual(c['physics_profile'],'standard_game');self.assertLess(np.linalg.norm(q[0]-q[-1]),.001)
  videos=json.loads((R/'references/videos.json').read_text())['videos'];self.assertEqual([v['video'] for v in videos],list(range(1,9)));self.assertEqual({r['video'] for r in d['source_ranges'] if 'video' in r},set(range(1,9)))
 def test_native_north_and_image_orientation(self):
  origin=np.array([-100.,-150.]);g=b.local_to_game([[0,0],[0,20],[20,0]],origin);p=b.game_to_pixel(g,384,2049)
  self.assertGreater(g[1,1],g[0,1]);self.assertLess(p[1,1],p[0,1]);self.assertGreater(p[2,0],p[0,0]);np.testing.assert_allclose(g+origin,[[0,0],[0,20],[20,0]])
 def test_open_or_invalid_route_is_rejected(self):
  with self.assertRaises(ValueError):b.validate_route([[0,0],[1,0],[1,1],[0,1]])
  with self.assertRaises(ValueError):b.validate_route([[0,0],[1,0],[np.nan,1],[0,0]])
 def test_arc_sampling_preserves_turns_and_seam(self):
  s,q=b.sample_route(np.array([[0,0],[10,0],[10,10],[0,10],[0,0]],float),.5);self.assertEqual(s[-1],40.);np.testing.assert_allclose(q[0],q[-1]);self.assertTrue(np.all((q>=0)&(q<=10)));np.testing.assert_allclose(q[20],[10,0])
if __name__=='__main__':unittest.main()
