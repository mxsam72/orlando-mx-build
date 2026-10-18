"""Portable checks for recovery integrity, bake isolation and process cleanup."""
import configparser
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_recovery as recovery
n = recovery.n

class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {name: getattr(n, name) for name in ['R', 'M', 'B', 'G', 'LOG']}
        n.R = Path(self.tmp.name); n.M = n.R/'MOON'; n.B = n.M/'build'
        n.G = n.B/'game'; n.LOG = n.M/'native_logs'
        n.G.mkdir(parents=True); n.LOG.mkdir()
        (n.M/'checkpoint_downloads').mkdir()

    def tearDown(self):
        for name, value in self.previous.items(): setattr(n, name, value)
        self.tmp.cleanup()

    def fixture(self):
        path = n.R/recovery.ASSET_FILES['sky'][0]
        path.write_bytes(b'EDF\0controlled-fixture')
        archive = recovery.checkpoint('sky', recovery.ASSET_FILES['sky'], {'returncode': 0})
        dest = n.M/'checkpoint_downloads/sky.zip'; shutil.copyfile(archive, dest)
        return path, dest

    def rewrite(self, archive, change):
        with zipfile.ZipFile(archive) as z: contents = {name: z.read(name) for name in z.namelist()}
        change(contents)
        with zipfile.ZipFile(archive, 'w') as z:
            for name, value in contents.items(): z.writestr(name, value)

    def test_round_trip(self):
        path, _ = self.fixture(); path.unlink()
        recovery.restore('sky')
        self.assertEqual(path.read_bytes(), b'EDF\0controlled-fixture')

    def test_corrupted_payload_does_not_overwrite(self):
        path, archive = self.fixture()
        self.rewrite(archive, lambda d: d.__setitem__(recovery.ASSET_FILES['sky'][0], b'bad'))
        with self.assertRaises(AssertionError): recovery.restore('sky')
        self.assertEqual(path.read_bytes(), b'EDF\0controlled-fixture')

    def test_wrong_provenance_is_rejected(self):
        _, archive = self.fixture()
        def change(d):
            m = json.loads(d['manifest.json']); m['source_archive_sha256'] = 'wrong'
            d['manifest.json'] = json.dumps(m).encode()
        self.rewrite(archive, change)
        with self.assertRaises(AssertionError): recovery.restore('sky')

    def test_extra_archive_entry_is_rejected(self):
        _, archive = self.fixture()
        self.rewrite(archive, lambda d: d.__setitem__('../unexpected', b'bad'))
        with self.assertRaises(AssertionError): recovery.restore('sky')

    def test_bake_only_changes_declared_shadow_settings(self):
        original = '[params]\nlightdir_x=-6\nlightdir_y=10\nlightdir_z=-6.6666667\nshadowmaps_create=1\nshadowmaps_scale=0.5\nshadowmaps_supersampling=2\nshadowvolumes_create=0\nshadowmaps_terraincast=1\n'
        for enabled in [False, True]:
            cfg = configparser.ConfigParser(); cfg.read_string(recovery.bake_params(original, enabled))
            self.assertEqual(cfg['params']['lightdir_z'], '-6.6666667')
            self.assertEqual(cfg['params']['shadowmaps_create'], '1' if enabled else '0')
            self.assertEqual(cfg['params']['shadowmaps_scale'], '0.2')
            self.assertEqual(cfg['params']['shadowmaps_supersampling'], '1')
            self.assertEqual(cfg['params']['shadowmaps_terraincast'], '1')

    def test_process_wrapper_success_failure_and_timeout(self):
        result = n.run(sys.executable, ['-c', 'print("native process fixture")'], 'fixture-ok', 10)
        self.assertEqual(result['returncode'], 0)
        with self.assertRaises(AssertionError):
            n.run(sys.executable, ['-c', 'raise SystemExit(2)'], 'fixture-fail', 10)
        with self.assertRaises(TimeoutError):
            n.run(sys.executable, ['-c', 'import time;time.sleep(10)'], 'fixture-timeout', .2)
        self.assertTrue((n.LOG/'fixture-timeout_status.jsonl').exists())

if __name__ == '__main__': unittest.main()
