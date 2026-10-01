# Orlando MX v020 — native-build repair checkpoint, 2026-10-01

Branch: rebuild-v020 in mxsam72/orlando-mx-build. Base for this repair is c6a2021921e8459809ebb87d10880ec34d01f4ed. Delivered v019 remains untouched at 002ab59e00200b5c64ee735bd8769f77d3e95bee.

## Verified failure cause

Actions 36866951534 generated a PKZ, then failed a false texture check. PiBoSo removes .tga from native texture names. Do not restore literal filename searches or simply remove validation.

Native probe run 36824107860 proves that non-power-of-two bitmaps are silently omitted. Supported bitmaps contain an extensionless 100-byte name, dimensions, the MD5 of bottom-up RGBA pixels, and a bounded compressed payload. validate_native_textures_v020.py verifies these records and requires corresponding signatures in the final MAP. Local positive, NPOT-negative and corrupted-digest controls passed.

## Included repairs

- All owner graphic textures remain power-of-two, with explicit FBX UV and texture-file properties.
- Four custom bike meshes have fuller engines/frames, suspension, controls, knobby wheels and spokes. This repair adds curved fenders, rounded engine details and open brake rotors. Front plates clear the forks; number/shroud backings sit behind their graphic faces.
- Premier's wrap follows the bent cab shoulder instead of cutting through it. The red power graphic covers the rear window. Removed the unrelated adjacent van's electrical-company label. The other three accepted vehicle geometries compare exactly against the pre-repair builders.
- Removed only generic pickup_03, formerly (321,149), heading -15.
- Replaced the random-colored sign plaques with actual user-reference sticker artwork on four thin physical surfaces. V020_SOURCE/bithlo_sign_reference.jpg is verified through native compilation along with vehicle textures.
- Sign position is (278,142), heading 270, estimated from the yellow circle at the left shoulder of the main-frontage / office-apron gravel junction. The failed build's (242,143) was an assistant interpretation, not a user-supplied coordinate. Placement remains an authored estimate for the next game review.
- Terrain, track profiles, start/race files, gravel/grass layouts and other facilities remain protected. Missing protected inputs now fail instead of being silently skipped.

## References and limits

The supplied 71.94-second v019 clip was reviewed: old sign at 9–18 s, pickup_03 near 21 s, owner assets at 24–36 and 42–66 s. Blank game graphics despite visible graphics in source renders led to the native texture investigation.

mxb-mods.com led to Jay's Husqvarna release and Yamaha source-model threads, but their MediaFire downloads were unavailable. No community/OEM source bike was imported. These are custom photo-derived static scenery meshes. The official PiBoSo bike template was examined but was not a suitable complete visual model.

Mesh previews are software renders of authored geometry, not in-game screenshots. An MX Bikes visual/riding test remains necessary.

## Resume and delivery

1. Check the newest Actions run on rebuild-v020. Do not use the old failed run or stop after dispatch.
2. Source, clearances and protected-input checks must pass; a source artifact is saved before native compile.
3. Native MAP/TRH/PKZ compilation and exact texture verification must pass. Inspect native-failure-data if needed; do not disable the gate.
4. Download game-candidate, verify SHA, ZIP CRC and PKZ contents; inspect final evidence/previews.
5. Deliver the actual PKZ, validation and install notes. Update this handover with the successful run/checksum. In-game review remains pending.

At this checkpoint the native rebuild is pending; no repaired package has yet been delivered.
