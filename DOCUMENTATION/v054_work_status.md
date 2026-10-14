# Orlando MX v054 A/B/C update — native build in progress

User approved an A/B/C sketch over the delivered v052 track-info map. v053 dirt changes were cancelled. All work here starts from v052 commit 109bf8469e09d9653898f975c906729e1ca53530 and its delivered source/PKZ pins.

- A extends the approach/return and moves the outside corner east by roughly 25 m, following the drawing.
- B preserves the gate origin and 24 gate positions, creates an approximately 178 m start lane through the new gap, and merges farther along the main corner at old authored station 500 m. The bank opening uses a smooth elevation profile. Sector 1 moves after this merge, and the bypassed T05 checkpoint becomes normal-lap-only.
- C broadens the roller entry curve. R17 retains eight roller profiles, their heights, and 10 m authored spacing. A local smoothing of the transported underlying C floor removes residual historical roller impressions; an independent RAW-height check observes eight crests.
- Static v052 soil photographs, colour tiles, tiled normals and shaders remain byte exact. Only old/new corridor masks and the directional atlas move. Same 14 layers.
- All road/asphalt/concrete geometry and practice barriers stay exact. A rasterized road guard protects 139,879 terrain samples. Nearby necessary vegetation moves without increasing counts; disconnected grass blades bind individually to the edited terrain.
- 24 gates and 24 pit stalls retain world coordinates. Unrelated jump riding lines, lighting, cameras and logo are verified exact. The native main/start lines and reset stations follow the revisions. The UI map is updated.

The final source run is 38605191325, source commit 03b21cb68c34366ddc0f8a8a63995f9b31abc528. All authoring, material, scenery, race and independent checks passed. Matched A/B/C/source merge previews were downloaded, checksum checked and visually reviewed. They are source renders, not game screenshots.

Reviewed source is held in draft release ID 412990475, tag v054-start-corners-38605191325. Source checkpoint: OrlandoMX-v054-source-checkpoint.zip, 427895975 bytes. The metadata is authoritative in the release/checkpoint descriptor. Browser previews: https://github.com/mxsam72/orlando-mx-build/blob/rebuild-v054/PREVIEWS/v054/README.md

The Windows workflow .github/workflows/build-v054-native.yml restores baseline inputs, restores the exact reviewed output (without overwriting revised compiler/validator code), compiles FBX2EDF, checks zero-intensity foliage and exact scenery coordinates, compiles TRH and merges both TCL lines with TrackEd, then compiles MAP. It checks native object/terrain bitmaps and coordinates, changed collision, archive CRC/root/count and the existing 5% size budget before publishing.

Native EDF is preserved in the draft release before the slow MAP stage. PKZ and native compile results are preserved in that draft before final validation, allowing recovery if a validator requires correction. Publication is gated on checks. Actual in-game appearance, first-lap timing, resets, riding and FPS still require the user ride test.

Active native run: 38607699127, started 2026-10-14 17:33:48 UTC from compiler commit 76696afc917cbb8ade40e391c69ad2b2248cc7fc. Job 116002715793. Scenery export completed and was preserved at 17:40:19 UTC as OrlandoMX-v054-native-scenery.zip (228,735,136 bytes, SHA256 50e3d6ac7a96b9988f5c9cf23ccb3c72fdd7cabe9841fbd4af00b67a74e8e8ed). At 17:56 UTC the native compilation step remains active; no final PKZ or validation report has been uploaded yet. Monitor https://github.com/mxsam72/orlando-mx-build/actions/runs/38607699127. The final intended release is https://github.com/mxsam72/orlando-mx-build/releases/tag/v054-start-corners-38605191325, but do not give its download until verified publication.

New implementation files: TOOLS/v054_inputs.py, v054_geometry.py, v054_surfaces.py, v054_scenery.py, v054_verify.py, v054_previews.py, v054_transfer.py and build_windows_v054.py. All are saved in GitHub rebuild-v054. The original drawing is in V054_SOURCE/markup_reference.json. Current local source-review images/reports are in /workspace/scratch/95df4730d04f/review_v054_final_source.
