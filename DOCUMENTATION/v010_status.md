# v010 recovery checkpoint — native candidate complete

## Current state

The v010 candidate compiled successfully with the pinned official PiBoSo tools on Windows. It is ready for an in-game test. In-game riding, first-lap timing, reset behavior and multiplayer validation have NOT been performed.

- Branch: rebuild-v010-irl-corrections
- Source commit used by the package: 87bd80b86ef99d7ebe0ed3ef5585532d38e83c9b
- Successful workflow: https://github.com/mxsam72/orlando-mx-build/actions/runs/36424583575
- Native artifact: 10971686023 (OrlandoMX-v010-game-candidate)
- Source checkpoint artifact: 10970962658
- Build evidence artifact: 10971228022
- Package: OrlandoMX_2026_v010.pkz
- Package size: 141,233,568 bytes
- SHA256: c05f241b877dc0f6bf82ea59123aecb83341717dcf670309d113f13bf56e586a
- Final terrain SHA256: 50c386cc5c4dc60f07d48b78998a3fe7b92a337bad163e1d767c3bfd00db04db

The downloaded artifact and PKZ CRC passed; every packaged support/MAP/TRH file matched its native-build hash. The native scenery-coordinate check passed 32/32 probes, including the relocated fence. Main and start centerlines merged successfully. Read v010_native_validation.json and v010_package_validation.json for machine-readable evidence. GitHub artifacts currently expire 2026-12-27; the committed source remains reproducible.

## What changed

1. Gate/grid moved to native (416,184), facing +Z, with 24 stalls at 1.5 m spacing. A separate 115.9 m start lane passes outside T01 and joins T05 at main station 455 with matching tangent. These are authoring estimates within the user-confirmed zone.
2. The apron is level across the stalls. A local opening through the outside T05 entry bank removes the obstruction across the start route. The normal main centerline and terrain outside the junction remain at the main-terrain elevations. The outside normal line changes locally to form the junction.
3. Native shared gate placement, grid stalls, start checkpoints and 30-second board move together. Two start-only checkpoints cover the connector; T05–T14 use Both; T01–T04 remain normal-lap checkpoints. Finish, splits, pits and pit boards are retained. First-lap flags require actual game verification.
4. Start/off/racing/grass masks retire the old race-start connector. Normal-lap reset boundaries remain compatible with the unchanged main centerline; start-area resets need an in-game test.
5. Relocated 68 fence meshes along the T14–R01–T01 spectator frontage, with the gate to its right. The 128.0 m authored frontage has 24 posts and at least 3.95 m clearance from the native track edge at sampled posts. Cleared 18 trees from the new start corridor; no fixed-building conflicts were detected.
6. Revised R01–R12 and R14–R18 profiles, especially R03, R07, R09/R10 and R14. All 14 corners now have different entry/apex/exit loading, pockets and drifting rut paths. Removed the v009 full-lap repeated wave/twin-groove overlay and compensated the older corner-rut recipe. Main X/Z route and station IDs are retained.

See v010_changes.md for the complete parameter table, actual encoded face grades and P01–P14 ledger. The legacy visual-mask coverage records in release_validation describe the main-lap preparation stage; final facility masks are identified by their input hashes and final start/off checks in the same report.

## Numerical checks

- Grid elevation spread and slope: 0.
- Maximum start-centerline grade: 0.1782.
- Maximum changed start/merge terrain grade: 0.6721.
- Normal centerline height change from start grading: 0.
- Protected normal-lap terrain change from start grading: 0.
- Gate-position RDF reconstruction error: under 0.000007 m.
- Encoded full-lap geometry, finite values, loop seam and grade limits passed.

These checks establish construction consistency, not an accurate IRL ride match.

## Recovery history

- 00 — 5b5414b84da2ae8ea12f5321650759657bc2cbbe: confirmed scope and reviewed section sync.
- 01 — f7bfd6cda5626d98ff718efbe23facafd434273b: gate terrain and race-data source.
- 02 — 363ea55e542620b935998d62ddb259094dc38cbd: full geometry/fence/mask/native pipeline. Source and native outputs were generated, but its workflow was superseded. Do not install its earlier merge shape.
- 03 — 87bd80b86ef99d7ebe0ed3ef5585532d38e83c9b: corrected T05 entry bank opening; this is the tested source commit used by the current PKZ.
- 04 — this documentation/evidence checkpoint: records native success and verified package hashes. It does not change the compiled sources.

## Resume or rebuild

Read this file and V010_SOURCE/requirements.json first. The last playable baseline v009 remains on rebuild-v009-geometry at 4bdb20c2c34ce91cdd15c63546d5f7b662d9c4a4; no v009 source/release is overwritten by this pipeline.

Windows: run BUILD_V010_LOCAL.bat. For a manual build:

    python -m pip install -r requirements-v009.txt
    python TOOLS/build_v010.py --source-only
    python TOOLS/build_windows_v010.py

The pipeline reconstructs the verified baseline, generates v010 into V010_OUTPUT, prepares 12_RELEASE/orlandomx_2026_v010, saves a source checkpoint, then compiles a new PKZ. Source-changing pushes on this branch run the same workflow. New source commits cancel obsolete runs, while uploaded artifacts remain. Never reuse the old v009 start.tcl or start/off masks.

## Next work

1. Install the current PKZ and test an actual race start from central and outer stalls. Confirm gate drop, convergence into T05, first finish crossing, then a complete timed lap without false checkpoint penalties. Test short/long resets on the start lane and T05.
2. Record a full v010 comparison lap against the existing P01–P14 anchors. Assess approach/face/landing and corner entry/apex/exit; recipe dimensions and compilation are not IRL measurements.
3. Resolve EX1: real 0:23–0:24 (repeat 2:23–2:24), separate mound versus raised T02 entry. Resolve EX2: real 1:38–1:40, the smaller rising section after the signature landing and before T11. Both remain disabled provisional records. R13 dimensions are held until the pre-signature disturbance is identified.
4. Based on that evidence, finish feature spacing and supported local plan-view corner changes. Close vegetation/brush detailing remains, beyond the completed frontage relocation and start clearing.

Do not mark the full IRL rebuild or ride validation complete before these tests and clarifications.
