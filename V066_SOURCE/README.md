# v066 native cinematic-lighting test

This is an in-game daylight experiment against the released v065 track, not a
Blender-render-equivalent claim. The source is restored from the authenticated
v065 checkpoint; no historical authoring stack is regenerated.

The primary game sun changes from `(2, 10, -7)` (about 53.945 degrees elevation)
to the 230-degree X/Z azimuth, 28-degree elevation defined in `lighting_spec.json`.
That is slightly above the main photo set's 23-degree key, retaining visibility
while giving normals, jump faces and berms more side lighting. Clear-weather
sunlight is warm; ambient fill stays sufficient to read black paint and shadows.
Fog density drops from 0.00018 to 0.00010. Cloudy/rainy color settings and stock
skies are retained; the shared global sun direction changes consistently.

The `.amb` runtime position and TerrainEd's `lightdir_*` values are generated
from one specification and must match. Baked shadows are rebuilt. The existing
0.1 shadowmap scale, supersampling of 4, and terrain self-shadowing are preserved.
No new material images, reflection cube maps, geometry, layers or shadow
resolution are added. Source texture allocation is unchanged; measured game
RAM/VRAM and FPS remain unverified until the user's test.

All v065 height samples, physical declarations, route/race/reset data, B corners,
C surfaces, cleared start grass and wall roller are retained. The scenery FBX,
native EDF, all terrain bitmap/shader hashes and scenery probes are checked.
That includes the four vehicle models, candy sign, Pup memorial and crocodile.

Run `TOOLS/v066_lighting.py restore`, `TOOLS/test_v066_lighting.py`, then
`TOOLS/build_windows_v066.py stage` for source validation. The Windows workflow
performs the official TerrainEd/TrackEd compilation, full height and bitmap
validation, source checkpoint and gated native release.

Compare v065 and v066 in **Clear** weather with matching graphics settings and
shadows enabled. Judge the result from actual MX Bikes screenshots and riding.

Official technical references:

- https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide
- https://docs.piboso.com/wiki/index.php?title=FBX2EDF
- https://docs.piboso.com/wiki/index.php?title=Track_Creation_Guide
