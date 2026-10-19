from pathlib import Path
import importlib.util, json, sys, unittest
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from build_source import load_project,profile,digest
from native_validation import valid_member,package_identity


class TerrainTests(unittest.TestCase):
    def test_every_authored_feature_has_video_evidence_and_estimate_status(self):
        d=json.loads((R/'source/terrain_features.json').read_text());self.assertEqual(len(d['jumps']),19);self.assertEqual(len(d['berms']),12)
        for f in d['jumps']+d['berms']:
            self.assertEqual(f['dimension_status'],'authored_estimate');self.assertTrue(f['references'])
            for ref in f['references']:self.assertIn(ref['video'],range(1,9));self.assertLess(ref['time_seconds'][0],ref['time_seconds'][1])
        self.assertEqual({r['video'] for f in d['jumps'] for r in f['references']},set(range(1,9)))

    def test_profiles_have_closed_toes_no_negative_pits_and_distinct_scales(self):
        fs=json.loads((R/'source/terrain_features.json').read_text())['jumps']
        for f in fs:
            a=f['station_start_m'];end=a+sum(f[k] for k in ['takeoff_length_m','deck_length_m','landing_length_m']);s=np.linspace(a,end,1000);h=profile(f,s)
            self.assertGreaterEqual(h.min(),-1e-5);self.assertAlmostEqual(h[0],0,places=5);self.assertAlmostEqual(h[-1],0,places=5);self.assertGreater(h.max(),f['height_m']*.99);self.assertEqual(float(profile(f,np.array([a-1,end+1])).sum()),0)
            self.assertLess(abs(float(profile(f,np.array([a+.001]))[0]))/.001,.005);self.assertLess(abs(float(profile(f,np.array([end-.001]))[0]))/.001,.005)
        self.assertGreater(max(f['height_m'] for f in fs)/min(f['height_m'] for f in fs),3.5)

    def test_package_identity_rejects_misnamed_pkz_and_unsafe_members(self):
        self.assertFalse(valid_member('BushnellMX_v001/../escape','BushnellMX_v001/'));self.assertFalse(valid_member('/BushnellMX_v001/map','BushnellMX_v001/'))
        with self.assertRaises(ValueError):package_identity('DifferentName.pkz',['BushnellMX_v001/a'],'BushnellMX_v001')

    @unittest.skipUnless((R/'build/v001/validation.json').exists(),'Build source first')
    def test_actual_heightfield_varies_and_matches_quantized_review(self):
        B=R/'build/v001';v=json.loads((B/'validation.json').read_text());raw=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049);h=np.load(B/'height_metres.npy')
        self.assertEqual(digest(B/'terrain.raw'),v['source_raw_sha256']);np.testing.assert_allclose(h,raw.astype(np.float32)/65535*16,atol=1e-6);self.assertGreater(float(h.max()-h.min()),3.5);self.assertTrue(v['checks_pass']);self.assertFalse(v['gps_altitude_used']);self.assertLess(v['maximum_riding_line_displacement_m'],.6)


if __name__=='__main__':unittest.main()
