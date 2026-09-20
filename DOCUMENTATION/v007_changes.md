# Orlando MX v007 — jump rebuild

Built from the user's verified v006 package and its exact authoring terrain.
The centerline, corner layout, racing widths and sequence of 18 obstacles are retained.

## Geometry changes

- Eleven jumps now have an eased toe, a steady final face, a longer curved lip,
  a defined table and a landing with a gradual four-metre exit transition.
- Seven low features use rounded roller profiles without the repeated short
  flat tops used in v006.
- Tabletop face design angles range from 19 to 25 degrees. Heights remain at the
  previous design crests; the build is not an across-the-board height increase.
- J06 moves 5 m earlier and J12b moves 8 m earlier on their existing lanes.
  Their modeled landings finish approximately 8.1 m and 2.4 m before the next
  mapped corner. These are construction coordinates, not surveyed measurements.
- The full earthen shoulders follow the new profiles. A local slope pass removes
  projection artifacts near curved approaches; its maximum adjustment is recorded.
- Seventy-four existing scenery meshes are rebound to the revised ground. Mesh
  topology, materials and coordinate conventions are retained. Fence-rail normals
  are recalculated when their slope changes. Marshal and camera elevations follow
  the revised ground where relevant.

## Evidence and limits

`v007_terrain_validation.json` checks the actual encoded RAW. `source_validation.json`
checks height encoding, native centerline reconstruction, start and pit placements,
reset boundaries and race data. `v007_jump_validation.json` records profiles and
clearance to corners. Its analytic lip-curvature comparison is a geometry metric,
not a prediction of suspension response or in-game ride quality.
`v007_scenery_validation.json` verifies a byte-identical unmodified FBX round trip
and the hash-checked vertex patch. The native compiler checks the actual outputs.

The comparison and preview PNGs are authoring views, not game screenshots.
No in-game riding, bike-physics simulation or multiplayer test has been performed.
The user should ride v007 before calling handling and real-track fidelity validated.

## Reproducible native build

The v006 `BUILD_INPUTS` manifest and 73 parts remain immutable. The unpacker verifies
those files, then verifies and applies `BUILD_V007` to install the revised terrain,
v007 race/selection files and a compact scenery patch. The patch preserves untouched
FBX properties and recomputes binary node offsets. Windows uses the same hash-pinned
official PiBoSo tools as v006 and creates a separate v007 PKZ.

For authoring, recover `OrlandoMX_v006_Assets_Checkpoint.zip` and overlay repository
source. `TOOLS/refine_jumps.py` needs NumPy, SciPy and Pillow; `rebind_scenery.py`
generates the scenery patch; `qa_jumps.py` also needs Matplotlib. The original v006
Blend file remains a historical reference; the patched FBX and new RAW are the
canonical v007 native geometry. Private reference videos are not in this repository.
