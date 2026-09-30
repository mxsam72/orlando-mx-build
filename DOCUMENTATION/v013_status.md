# v013 status

Branch: `rebuild-v013-jump-refinement`.

v013 branches from the completed v012 source and preserves the v012 facility/start/material fixes. The September 29 ride-test update changes only R01, R02, R03, R05, R07, R09, R10, R12, R14, R17 and R18.

Source spec: `V013_SOURCE/v013_geometry_spec.json`.

The native GitHub workflow is `.github/workflows/build-v013.yml`. Source/native QA and an in-game ride test are required before v013 is considered complete.


## Native build complete

GitHub Actions workflow `Build v013 jump refinement` completed successfully.

- Workflow run: `36666031058`
- Build source commit: `3906fba27accd45f9848ee129b12f32187a01005`
- Game artifact: `OrlandoMX-v013-game-candidate`
- Game artifact ID: `11076179370`
- Evidence artifact ID: `11076422043`
- Source checkpoint artifact ID: `11076084383`
- PKZ: `OrlandoMX_2026_v013.pkz`
- PKZ bytes: `139974255`
- PKZ SHA-256: `5c0cd44627845bf629d06262e50c9375f973b38f6686666e5f401b7b07f44adb`

Source geometry QA passed:
- 0 new excessive-grade nodes
- route unchanged
- outer terrain unchanged
- R12 encoded as 4 rollers at ~10 m spacing
- R17 encoded as 8 rollers at ~10 m spacing
- R18 remains inside-line-only
- all requested v013 profile changes encoded

Native stages succeeded:
- fbx2edf
- terrained_map
- terrained_trh
- tracked_merge

Remaining gate: in-game ride validation only.
