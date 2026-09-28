# v010 implementation checkpoint

## Checkpoint 01 — gate terrain and race-data source

Baseline v009: 4bdb20c2c34ce91cdd15c63546d5f7b662d9c4a4.
Branch: rebuild-v010-irl-corrections.
Scope checkpoint: 5b5414b84da2ae8ea12f5321650759657bc2cbbe.

Implemented: configurable 24-stall grid at native (416,184), facing +Z; separate 115.9 m native start centerline into T05 at main station 455; level launch apron, gradual taper and blended grade; relocated 30-second board; 2 start-only checkpoints, 10 Both checkpoints from T05 onward and 4 normal-only checkpoints before the merge. Native shared gate follows the grid. Metric positions and widths are authoring estimates, not survey data.

Source checks passed: exact merge position/tangent, zero grid height spread/slope, zero main-lap terrain change from the apron operation, maximum changed start-area grade 0.2964, grid RDF reconstruction error 0.000007 m. Finish, splits, pits and pit boards preserved byte-for-byte. See v010_start_validation.json and v010_race_validation.json.

This is a source checkpoint, not a playable release. Native compile, TrackEd checkpoint-mode verification, first-lap timing and start resets remain pending. Fence placement, visual/physics masks and jump/corner changes are next. Retired-start mask is calculated but not yet applied to release surfaces.

## Resume

1. Read V010_SOURCE/requirements.json and review_section_sync.json. Keep ambiguous EX1/EX2 and R13 interpretation provisional.
2. Reconstruct v009 with python TOOLS/build_v009.py --source-only (full repository assets required).
3. Run python TOOLS/v010_common.py; copy V009_OUTPUT/terrain.raw to V010_OUTPUT/main_terrain.raw; run python TOOLS/build_v010_start_terrain.py and python TOOLS/build_v010_race.py.
4. Finish fence FBX relocation, new start/off/visual masks, v010 release staging and Windows compiler wrapper. Do not package using the old start.tcl or old start mask.
5. Apply reviewed geometry changes, validate actual encoded terrain and save another checkpoint before native build.

Old v009 sources/releases are intact. Generated V010_OUTPUT files are reproducible and should not be committed wholesale.
