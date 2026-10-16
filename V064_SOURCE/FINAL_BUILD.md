# User-approved native v064 compilation

The user approved the v064 source previews and requested compilation, followed
by a GitHub status link and no further polling once the final stage starts.

`native_expected_inputs.json` pins the exact approved terrain, scenery, HMF,
routes, physical declarations, daylight, 49 terrain images and 18 active shaders.
The clean Windows runner reconstructs the original v062 B/C methods and v061
roller and rejects any difference from these approved source hashes. Dense
v063 is not used.

The pipeline restores the authenticated v060 release source, game files and
native scenery. Since the entire scenery FBX remains byte-exact, its pinned
native EDF is reused. Before compilation its geometry probes and matte foliage
are checked. Full object bitmap and scenery checks run against the final MAP.

TerrainEd recompiles collision and visual terrain from the approved v061 RAW
heightfield, including the new low wall-entry roller. TrackEd merges the
unchanged race/start routes. The new daylight file is explicitly installed.
Both native grids must match all 4,198,401 approved source samples; every MX
corner and all terrain outside the roller remain exact to v060.

A complete source checkpoint is saved before compilation, including all active
terrain images/shaders and resolved object textures. Native results are saved
to the draft release before final validation; the release is published only
after complete source, bitmap, geometry, height, race/lighting and archive
checks pass. The package budget remains 964,987,509 bytes. Actual game visuals,
riding and performance need the user's test.

`build-v064.yml` runs automatically for the final commit on `rebuild-v064`.
The long final step is named `FINAL NATIVE VISUAL TERRAIN COMPILATION AND
VALIDATION`. Once that step is observed running, return its run link and stop
polling as requested.
