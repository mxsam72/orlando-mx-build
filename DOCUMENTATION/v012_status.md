# v012 status

Authoritative instructions: `DOCUMENTATION/v012_handover.md` (2026-09-29).
Base: corrected v011 commit `56b7fed68c210c6090458d046a6ddc7490be9267` on `rebuild-v011-jumps-facilities`.
Its native workflow run `36481701635` completed successfully. The older v011 build-record file predates the material fix; use the corrected commit/run above.

New branch: `rebuild-v012-final-obstacles-layout`. Previous versions remain intact.

Checkpoint 01: corrected base and authoritative instructions captured. All R01–R18 types in the handover supersede earlier interpretations. Geometry, facility relocation and new start loop are in progress; no v012 native compilation or game test is claimed yet.

Material invariants: palette colors encoded in FBX diffuse/ambient properties, diffuse bitmap connections retained, generated textures staged at root and in `scenery.fbm/` before native import.

Available references: v011 test ride; all five IMG_3591/3592/3594/3595/3597 clips; prior GoPro and section mapping. Metric authoring dimensions use the user's requested approximate lengths, not claimed survey measurements.

Checkpoint 02: R01–R05 authored. R01 is 77.2 m, R02 triple 40 m, R03 table-single 35 m, R04 has no obstacle, R05 low double 12 m immediately before T05. Source primitives validated; terrain QA follows after all groups.

Checkpoints 03–07: remaining obstacle groups authored; bathroom and office relocated; start loop rerouted. New start is 166.79 m long, with 38 m apron, 7 m minimum corridor and tangent join at s493 (4.694 m before T06). Three start-only checks, nine Both turn checks, five normal-only turns.

Checkpoint 08: all 18 encoded profiles pass; R12/R17 counts are four/eight; decks and independent valleys survive encoding. R01's inherited s21 ledge was removed by grading its actual deck to a continuous plane. R07's rounded crest is authored at s552; the encoded terrain maximum falls ~1.05 m later because of underlying ground, still within the former landing area. All 91 facility meshes clear racing/start lanes and pit spawns. New start leaves the main centerline exactly unchanged. Source/native material assertions added for intended FBX RGB, diffuse bitmap links and dual texture staging. Native build is now verified successful. Runtime riding, first-lap timing, start reset behavior, multiplayer behavior and in-game material appearance are not yet claimed.


## Verified native build

GitHub Actions workflow `Build v012 final obstacles and layout` completed successfully.

- Workflow run: `36660342389`
- Build source commit: `60b028fdc38f1c3e6470d4d7ae2ff61fee13e877`
- Branch documentation head at cleanup: `e18ffaaa4f9e43611cb9b13346b742b4724d7456`
- Game artifact: `OrlandoMX-v012-game-candidate`
- Game artifact ID: `11074262287`
- Build-evidence artifact ID: `11074092566`
- Source-checkpoint artifact ID: `11074650064`
- PKZ: `OrlandoMX_2026_v012.pkz`
- PKZ SHA-256: `48345f6e11191e3c30291e45e5c507770de30cd82cd07b598d70809f8a265a25`

Native stages all returned success:
- fbx2edf
- terrained_map
- terrained_trh
- tracked_merge

The remaining gate is in-game validation only.
