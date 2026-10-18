"""Check that lighting recovery preserves authored FBX data and provenance."""
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_lighting as lighting
import test_native_recovery as base


def fbx_fixture():
    def node(name, props, at, children=b''):
        name = name.encode()
        end = at+13+len(name)+len(props)+len(children)+13
        return struct.pack('<IIIB', end, 3, len(props), len(name))+name+props+children+bytes(13)
    def text(value):
        return b'S'+struct.pack('<I', len(value))+value
    prefix = b'Kaydara FBX Binary  \x00\x1a\x00'+struct.pack('<I',7400)
    children = b''; objects_at = 27; child_at = objects_at+13+7
    for kind in ['Geometry', 'Model']:
        for r in (0,75,150,225):
            for c in (0,75,150,225):
                props = b'L'+struct.pack('<q', r*1000+c)+text(f'SHAD_massif_patch_{r}_{c}'.encode()+b'\x00\x01'+kind.encode())+text(b'Mesh')
                child = node(kind, props, child_at+len(children))
                children += child
    return prefix+node('Objects', b'', objects_at, children)+bytes(13)


class LightingChecks(unittest.TestCase):
    def test_only_distant_name_properties_change(self):
        original = fbx_fixture()
        result, edits = lighting.rename_distant_receivers(original)
        self.assertEqual(len(result), len(original))
        self.assertEqual(len(edits), 32)
        self.assertEqual(sum(a!=b for a,b in zip(result,original)), 128)
        reverted = bytearray(result)
        for edit in edits: reverted[edit['offset']:edit['offset']+5] = b'SHAD_'
        self.assertEqual(bytes(reverted), original)

    def test_missing_target_is_rejected(self):
        with self.assertRaises(AssertionError):
            lighting.rename_distant_receivers(fbx_fixture().replace(b'SHAD_massif_patch_0_0', b'VIEW_massif_patch_0_0'))

    def test_bad_node_range_is_rejected(self):
        source = bytearray(fbx_fixture()); struct.pack_into('<I', source, 27, len(source)+100)
        with self.assertRaises(AssertionError): lighting.rename_distant_receivers(bytes(source))


class ImportedCheckpointChecks(unittest.TestCase):
    setUp = base.RecoveryChecks.setUp
    tearDown = base.RecoveryChecks.tearDown
    fixture = base.RecoveryChecks.fixture

    def test_known_previous_run_restores_under_new_job_context(self):
        with patch.dict(os.environ, {'GITHUB_SHA':lighting.BASE_COMMIT, 'GITHUB_RUN_ID':lighting.BASE_RUN}):
            path, _ = self.fixture()
        with patch.dict(os.environ, {'GITHUB_SHA':'new-build', 'GITHUB_RUN_ID':'new-run'}):
            with self.assertRaises(AssertionError): lighting.recovery.restore('sky')
            path.unlink()
            got = lighting.restore_base('sky')
            self.assertEqual(got['compiler_commit'], lighting.BASE_COMMIT)
            self.assertEqual(path.read_bytes(), b'EDF\0controlled-fixture')

    def test_other_previous_run_is_rejected(self):
        with patch.dict(os.environ, {'GITHUB_SHA':lighting.BASE_COMMIT, 'GITHUB_RUN_ID':'wrong-run'}):
            self.fixture()
        with self.assertRaises(AssertionError): lighting.restore_base('sky')

    def test_incomplete_context_cannot_disable_guard(self):
        self.fixture()
        with self.assertRaises(AssertionError): lighting.recovery.restore('sky', expected_context={})


if __name__ == '__main__': unittest.main()
