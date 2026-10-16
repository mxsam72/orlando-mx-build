"""Pure-stdlib contract tests; source inventory is checked by v066_lighting.check."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
import zipfile
from v066_lighting import (BASE_BUILD, BASE_GAME, OLD_NAME, S, author_amb,
                           author_params, format_amb, parse_amb, read,
                           sun_position, validate_pair, copy_exact, extract_file)


class LightingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = read(S / 'lighting_spec.json')
        cls.amb = (BASE_GAME / (OLD_NAME + '.amb')).read_text()
        cls.params = (BASE_BUILD / 'v065_stage/map_params.ini').read_text()

    def test_roundtrip_preserves_all_semantics(self):
        before = parse_amb(self.amb)
        self.assertEqual(before, parse_amb(format_amb(before)))

    def test_target_angles(self):
        p = sun_position(self.spec)
        self.assertAlmostEqual(math.degrees(math.atan2(p['y'], math.hypot(p['x'], p['z']))), 28)
        self.assertAlmostEqual(math.degrees(math.atan2(p['z'], p['x'])) % 360, 230)

    def test_runtime_and_baked_directions_match(self):
        result = validate_pair(author_amb(self.amb, self.spec), author_params(self.params, self.spec))
        self.assertTrue(result['synchronized_baked_and_runtime_sun'])

    def test_mismatched_old_shadows_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'directions differ'):
            validate_pair(author_amb(self.amb, self.spec), self.params)

    def test_only_authorized_environment_values_change(self):
        before = parse_amb(self.amb)
        after = parse_amb(author_amb(self.amb, self.spec))
        self.assertEqual(before['cloudy'], after['cloudy'])
        self.assertEqual(before['rainy'], after['rainy'])
        for weather in ['clear', 'cloudy', 'rainy']:
            for key in ['sky', 'sky_rot']:
                self.assertEqual(before[weather][key], after[weather][key])
        for key in ['red', 'green', 'blue']:
            self.assertEqual(before['clear']['fog'][key], after['clear']['fog'][key])

    def test_no_new_shadow_resolution_or_features(self):
        before = self.params.splitlines()
        after = author_params(self.params, self.spec).splitlines()
        self.assertEqual([x for x in before if not x.startswith('lightdir_')],
                         [x for x in after if not x.startswith('lightdir_')])

    def test_unsafe_color_and_dark_sun_are_rejected(self):
        invalid = copy.deepcopy(self.spec)
        invalid['clear_sun_rgb'][0] = 2
        with self.assertRaises(AssertionError):
            author_amb(self.amb, invalid)
        invalid = copy.deepcopy(self.spec)
        invalid['sun_elevation_degrees'] = 5
        with self.assertRaises(AssertionError):
            sun_position(invalid)

    def test_comments_are_ignored_and_bad_braces_are_rejected(self):
        self.assertEqual(parse_amb('; comment\n' + self.amb), parse_amb(self.amb))
        with self.assertRaises(AssertionError):
            parse_amb('clear { ambient { red = 1 }')

    def test_incomplete_owned_copy_is_repaired(self):
        with tempfile.TemporaryDirectory(prefix='v066-copy-') as directory:
            root = Path(directory)
            source = root / 'source.bin'
            target = root / 'target.bin'
            source.write_bytes(bytes(range(256)) * 4096)
            target.write_bytes(b'incomplete')
            copy_exact(source, target)
            self.assertEqual(source.read_bytes(), target.read_bytes())

    def test_cached_extraction_requires_matching_size_and_crc(self):
        with tempfile.TemporaryDirectory(prefix='v066-extract-') as directory:
            root = Path(directory)
            archive = root / 'fixture.zip'
            payload = bytes(range(256)) * 4096
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('asset.bin', payload)
            target = root / 'asset.bin'
            # Matching length is insufficient: corrupted cached bytes must be repaired.
            target.write_bytes(b'X' * len(payload))
            with zipfile.ZipFile(archive) as z:
                extract_file(z, 'asset.bin', target)
            self.assertEqual(payload, target.read_bytes())


if __name__ == '__main__':
    unittest.main()
