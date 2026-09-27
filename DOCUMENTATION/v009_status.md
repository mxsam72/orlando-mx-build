# v009 checkpoint

Verified branch `rebuild-v009-geometry` at `1bdf86d67796bf2450941b60cf4fdec0433ecd43`. The exact Git tree and original commit object were reconstructed from authenticated GitHub reads because direct clone credentials are unavailable. Original commit timezone is preserved. No stable branch changed.

All 73 native-input parts, 10 v007 parts, and 21 v008 parts passed their byte/hash checks. The v008b scripts and release workflow are present. Fresh v007 inputs were restored, v008 applied, and v008b correction applied exactly once. 580 source trees became 417, matching the deterministic correction report.

Both supplied videos inspected through frame sequences and detailed obstacle/landmark frames. GoPro content repeats the start-area sequence about 124 seconds later and stops riding before the 160-second file ends. S12-S14 are repeat views of parts of S01-S04, not a new quarter lap. Mapping explicitly records aliases; dimensions and boundaries are authoring estimates.

This checkpoint verifies inputs only. Terrain reconstruction and native compilation are pending.

## Checkpoint 4 — opening / utility-pole sequence

Activated S01–S03, including repeat observations S12–S13 and the shared S14 approach. Replaced the pole-side plateau with a broad progressive ramp and downhill landing; reshaped the first carved sweeper and linked crests. Actual encoded-heightmap QA passes with zero new excessive-grade nodes and no terrain change outside the protected corridor. The major profile plots were inspected. Source compilation and in-game validation remain pending.

## Checkpoint 5 — full-lap geometry

Activated the remaining S10–S11 physical sectors. All S01–S14 reference windows are now covered, with S12–S14 represented by their repeat-sector aliases. Final encoded heightmap passes the strict full-lap grade gate: maximum changed-terrain grade 0.77953, racing-corridor grade 0.56436, zero newly excessive grade nodes, zero outer-corridor delta and zero native loop height difference. The horizontal route remains unchanged. Native compilation, scenery integration and in-game testing are separate subsequent checks.

## Source integration — ready for native compile

The full seven-stage source pipeline completed successfully. Scenery rebind changed 179 models vertically while preserving 606,512 total vertices, X/Z coordinates, topology and materials. Racing-mask mean core alpha is 0.96; outside-corridor alpha is unchanged. Pit height delta is zero; maximum sampled start-lane change is 0.03195 m. Raw heightmap hash is reproduced across runs. The one-click Windows launcher and separate Windows CI workflow compile and package only v009. Native output and in-game ride checks remain pending at this checkpoint.
