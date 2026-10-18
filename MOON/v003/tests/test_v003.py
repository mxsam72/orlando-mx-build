"""Geometry, directional shading, archive integrity and listing regressions."""
from pathlib import Path
import hashlib,io,json,re,sys,unittest,zipfile
import numpy as np
V=Path(__file__).resolve().parents[1];sys.path.insert(0,str(V/'scripts'))
import build_v003 as s
import native_v003 as native

class ShadowTests(unittest.TestCase):
    def test_flat_surface_does_not_self_shadow(self):
        mask=s.directional_shadows(np.zeros((129,129),np.float32))
        self.assertEqual(mask.shape,(129,129));self.assertLess(float(mask[8:-8,8:-8].max()),1e-5)
    def test_mound_shadow_points_away_from_runtime_sun(self):
        h=np.zeros((129,129),np.float32);h[62:67,62:67]=25
        mask=s.directional_shadows(h)
        self.assertGreater(float(mask[49,84]),.95)
        self.assertLess(float(mask[79,44]),.01)

class ArchiveTests(unittest.TestCase):
    def archive(self,data=b'source',name='MOON/v003/build/test.txt'):
        buf=io.BytesIO()
        files={name:dict(bytes=6,sha256=hashlib.sha256(b'source').hexdigest())}
        manifest=dict(files=files)
        with zipfile.ZipFile(buf,'w') as z:z.writestr('manifest.json',json.dumps(manifest));z.writestr(name,data)
        buf.seek(0);return zipfile.ZipFile(buf),manifest
    def test_valid_checkpoint_and_content_corruption(self):
        z,m=self.archive();native.verify_archive(z,m,('MOON/v003/',));z.close()
        z,m=self.archive(b'wrong!')
        with z,self.assertRaises(AssertionError):native.verify_archive(z,m,('MOON/v003/',))
    def test_traversal_cannot_pass_hash_validation(self):
        z,m=self.archive(name='MOON/v003/../../../outside.txt')
        with z,self.assertRaises(AssertionError):native.verify_archive(z,m,('MOON/v003/',))
    def test_pkz_basename_and_internal_root_must_match(self):
        required=[native.NAME+x for x in ['.map','.trh','.rdf','.ini','.amb','.tga','_map.tga']]+['moon_v003_sky.edf','gfx.cfg','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']
        names=[native.NAME+'/'+x for x in required]
        native.package_identity(native.NAME+'.pkz',names)
        with self.assertRaises(AssertionError):native.package_identity('Descriptive_Download_Name.pkz',names)
        with self.assertRaises(AssertionError):native.package_identity(native.NAME+'.pkz',[x.replace(native.NAME+'/','another_track/') for x in names])

@unittest.skipUnless((V/'build/source_validation.json').is_file(),'Generate terrain before authored-grid tests')
class AuthoredTerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((V/'build/source_validation.json').read_text())
        cls.raw=np.fromfile(V/'build/terrain.raw','<u2').reshape(2049,2049)
        cls.h=cls.raw.astype(float)/65535*cls.spec['native_scale_m']+cls.spec['terrain_height_offset_m']
    def test_nominal_flights_clear_entire_gap_and_meet_landings(self):
        for j in self.spec['features']+[self.spec['optional_transfer']]:
            with self.subTest(jump=j['id']):
                u=np.linspace(1,j['gap']+75,4000);c=np.array(j['center']);d=np.array(j['direction']);p=c+d*(u-j['gap']/2)[:,None]
                z=j['launch_height_absolute_m']+s.ballistic(u,j);gap=z-s.sample(self.h,p[:,0],p[:,1])
                self.assertGreater(float(gap[(u>5)&(u<j['gap']-2)].min()),.2)
                hits=np.flatnonzero((u>j['gap']-1)&(gap<=.02));self.assertGreater(len(hits),0)
                self.assertAlmostEqual(float(u[hits[0]]),j['gap']+30,delta=2)
                # The entire intended 48 m landing corridor is level laterally.
                touch=c+d*(j['gap']/2+30);normal=np.array([-d[1],d[0]])
                z=s.sample(self.h,*touch);sides=[s.sample(self.h,*(touch+normal*x)) for x in [-20,20]]
                self.assertLess(max(abs(float(v-z)) for v in sides),.02)
    def test_shorty_measurements_survive_native_quantization(self):
        data=np.load(V/'build/design.npz');x,y=np.meshgrid(data['x'],data['y']);protected=np.hypot(x,y)<90
        expected=data['base']+self.spec['terrain_height_offset_m']
        self.assertLess(float(np.max(abs(self.h[protected]-expected[protected]))),.002)
    def test_finish_and_bypass_reset_limits_are_not_in_first_gap(self):
        race=json.loads((V/'build/race_positions.json').read_text());self.assertEqual(race['finish_station_m'],60)
        rdf=(V/'build/game'/(native.NAME+'.rdf')).read_text()
        self.assertEqual(float(re.search(r'finish_line\s*\{[^}]*\blong\s*=\s*([\d.]+)',rdf)[1]),60)
        for p in (V/'build/game').glob('*.tl'):
            points=np.frombuffer(p.read_bytes(),'<f4',offset=8).reshape(-1,2)
            self.assertTrue(np.all(abs(points[:,1])==180))

if __name__=='__main__':unittest.main()
