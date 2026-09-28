# v010 recovery checkpoint

Branch: rebuild-v010-irl-corrections. Baseline v009: 4bdb20c2c34ce91cdd15c63546d5f7b662d9c4a4.

## Saved checkpoints

- 00: 5b5414b84da2ae8ea12f5321650759657bc2cbbe — user-confirmed facility relationships and full P01–P14 review metadata.
- 01: f7bfd6cda5626d98ff718efbe23facafd434273b — generated T05 start connector, level grid apron, relocated grid/board and first-lap checkpoint source. Local geometric and RDF reconstruction checks passed.
- 02: 363ea55e542620b935998d62ddb259094dc38cbd — complete v010 source pipeline, differentiated jump profiles and corner pockets/rut paths, spectator-fence relocation, new start/retirement masks, Windows build workflow. Full asset/native build must pass before a candidate is considered compiled.

- 03 (this commit): open the outside entry bank where the new start joins T05. The actual start profile previously crossed a 1.16 m bank crest. A localized opening now cuts that obstruction and rounds its shoulders; normal centerline and terrain outside the merge are preserved. Local checks: grid height spread/slope 0, maximum start-centerline grade 0.1782, maximum changed grade 0.6721, zero centerline and protected normal-lap height change.

## Implemented

Gate: 24 stalls at native (416,184), facing +Z; 115.9 m independent start lane into T05 at station 455, tangent to race direction. Numbers are construction estimates within the user-confirmed zone. Grid and native shared gate move together. Two Start checkpoints, ten Both checkpoints from T05 through T14, four normal checkpoints before T05. Finish/splits/pits unchanged. Long-reset boundaries retain the normal-lap geometry; start-area reset behavior needs an in-game test.

Fence: rebind actual FBX meshes to the new terrain, relocate fence along the outside T14–R01–T01 frontage and place the gate to its right. Reuse original materials and meshes, recalculate normals, remove start-lane trees/stakes if they obstruct the new corridor, fail on fixed building conflicts. Latest fence line is moved slightly outward to retain track-edge clearance. Full FBX verification runs in CI because the large packed inputs are available there.

Main terrain: individually tune R01–R12 and R14–R18. R13 dimensions held pending interpretation. Stronger built faces at R03, R07, R09/R10 and R14; shorter crest transitions; distinct modest linking rises. All 14 corners have differentiated loading, carved pockets and authored rut paths. Remove the v009 whole-lap wave/twin-groove overlay and compensate the older v006 repeated corner rut recipe before new grooves. Main horizontal route remains unchanged; no unsupported new plan-view turn radii are claimed.

EX1 and EX2 remain disabled, with provisional records in V010_SOURCE/v010_geometry_spec.json. Their exact forms and stations require the user's clarification. This does not block other improvements.

## Build and resume

Windows: run BUILD_V010_LOCAL.bat, or push source changes on this branch to run .github/workflows/build-v010.yml.

Command line:

    python -m pip install -r requirements-v009.txt
    python TOOLS/build_v010.py --source-only
    python TOOLS/build_windows_v010.py

The source build materializes the hash-checked v008b baseline under BUILD/v009_work, reconstructs exact v009 for before/after comparison, generates v010, validates encoded geometry/start/RDF/scenery/masks, and saves DOCUMENTATION/v010_source_checkpoint.json before native compilation. New outputs stay in V010_OUTPUT and 12_RELEASE/orlandomx_2026_v010. v009 sources and releases are not changed.

GitHub artifacts:

- OrlandoMX-v010-source-checkpoint: actual RAW, start TCL, RDF, facility layout, source checks and QA plots; saved before the expensive compile.
- OrlandoMX-v010-build-evidence: diagnostics uploaded even on failure.
- OrlandoMX-v010-game-candidate: fresh PKZ, checksum, validation and install notes, only after native success.

If interrupted: fetch latest branch HEAD and read this file, then inspect the latest v010 Actions run and DOCUMENTATION/v010*validation.json. Do not infer success from the existence of old validation files: the workflow uploads current diagnostics. Fix the first failed stage and save a new checkpoint. Never reuse v009 start.tcl or start/off masks in v010.

## Still requires verification

Checkpoint 02 passed the complete Windows source/FBX/mask pipeline. Its source artifact 10971535377 was saved (5,417,907 bytes, SHA256 0cd4359fd477626cfe7b58d9ad92190170cca6ba67f7b694edaf42d8f804d9cc). Checkpoint 03 includes the locally verified T05 entry opening and requires a new native build. Superseded runs are canceled after a new source commit to avoid compiling obsolete candidates; already uploaded checkpoints remain available. The first pipeline run is https://github.com/mxsam72/orlando-mx-build/actions/runs/36423850568 (checkpoint 02). This commit triggers a newer run; use the run whose head SHA matches the latest source checkpoint, not an older candidate. After compilation, test the animated shared gate, all grid slots, full start lane, first finish crossing, full normal lap timing, checkpoints and short/long resets. Compare P01–P14 approach/face/landing and entry/apex/exit footage. Metrics and compilation cannot establish that the game now matches the real track.

More detailed woods/brush placement, local plan-view corner changes where supported, and EX1/EX2 feature completion remain after this candidate and ride feedback.
