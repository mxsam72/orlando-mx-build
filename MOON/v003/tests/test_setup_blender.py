"""Regression coverage for forbidden downloads and incomplete archives."""
from pathlib import Path
import hashlib
import io
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import setup_blender as setup


class BlenderDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / 'blender.tar.xz'
        self.data = b'verified Blender archive fixture'
        for name, value in [('SIZE', len(self.data)), ('SHA256', hashlib.sha256(self.data).hexdigest())]:
            p = patch.object(setup, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_forbidden_primary_uses_verified_mirror(self):
        error = HTTPError(setup.URLS[0], 403, 'Forbidden', {}, None)
        with patch.object(setup.urllib.request, 'urlopen', side_effect=[error, io.BytesIO(self.data)]) as open_url:
            setup.download(self.archive)
        self.assertEqual(open_url.call_count, 2)
        self.assertEqual(self.archive.read_bytes(), self.data)
        self.assertFalse(self.archive.with_suffix('.xz.part').exists())

    def test_same_size_wrong_hash_and_partial_cache_are_rejected(self):
        self.archive.write_bytes(b'partial')
        with patch.object(setup.urllib.request, 'urlopen', side_effect=[io.BytesIO(b'x' * len(self.data)), io.BytesIO(self.data)]):
            setup.download(self.archive)
        self.assertEqual(self.archive.read_bytes(), self.data)

    def test_all_bad_downloads_leave_no_installable_archive(self):
        with patch.object(setup.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(b'partial')):
            with self.assertRaises(RuntimeError):
                setup.download(self.archive)
        self.assertFalse(self.archive.exists())
        self.assertFalse(self.archive.with_suffix('.xz.part').exists())

    def test_verified_cache_needs_no_network(self):
        self.archive.write_bytes(self.data)
        with patch.object(setup.urllib.request, 'urlopen') as open_url:
            setup.download(self.archive)
        open_url.assert_not_called()
