# Moon v002 — first native test build

This stage adds native gray regolith color/normal layers, broad route-following grooming and wheel paths, white/blue edge markers, a compact lunar service canopy, a graded pit apron and entry lane, eight pit spawns and eight start positions, timing splits/checkpoints and reset boundaries. The 3.64 km main lap, low rollers and terrain within 90 m of Shorty remain unchanged from v001.

The native compile workflow has two stages: Ubuntu authors and preserves exact source files and renders; Windows verifies the checkpoint hash and uses the official hash-pinned PiBoSo tools to build the sky, scenery, MAP and TRH, then merges the centerline. The build compares every visual and collision height sample against the RAW source, checks native geometry placements and material payloads, and checks archive integrity before publishing a prerelease test candidate. A failed check stops delivery.

**Target: single-player Testing with the separately installed MXB Quiet Gravity v4 set to `preset=half` (4.905 m/s²).** The PKZ does not switch gravity itself. The supplied INI selects half gravity for the existing plugin; the plugin binary is not bundled.

Run locally from the repository root:

```bash
python -m pip install -r MOON/requirements.txt
python MOON/scripts/build_test.py
blender -b --factory-startup -t 8 --python MOON/scripts/build_scene_test.py
# Windows only, after authoring/export:
python MOON/scripts/native_test.py
```

The `Moon v002 native test build` Actions workflow performs this sequence and publishes the test files after validation. `Install_Moon_v002.txt` describes installation and the first ride. Check the workflow's actual status; this source document does not claim compilation has already succeeded.

Native authoring validation is not an in-game test. Loading, timing, pit entry, pack starts, resets, traction, half-gravity jump behavior, rendering quality and FPS require a ride. Multiplayer is not supported by this test process. Blender source previews are not screenshots of MX Bikes.

The underlying lunar terrain comes from the v001 LROC sources. Fine grains, individual rocks, grooming and motocross/pit construction are authored, not surveyed microtopography or photographic scans. The tire/dust behavior still uses provisional compact/soft-soil game materials rather than a vacuum-regolith simulation. Fine visible surface relief is in normal maps and does not add physical bumps.
