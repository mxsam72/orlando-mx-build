# Orlando MX v055 — published and verified

Download: https://github.com/mxsam72/orlando-mx-build/releases/download/v055-soil-landing-38658838015/OrlandoMX_2026_v055.pkz

Release: https://github.com/mxsam72/orlando-mx-build/releases/tag/v055-soil-landing-38658838015

Official successful build: https://github.com/mxsam72/orlando-mx-build/actions/runs/38658838015

Compiled code commit: `2417e74b57ad59945a63a0ab057ade29a60c9d82`. Published 2026-10-15T00:59:20Z.

## Changes and source verification

Baseline is delivered v054, from `rebuild-v054` at `029fe56a44834e9e3c6b568049564ca7dba0a02a`. It retains the accepted v052 racing palette and the accepted A/B/C start-path/corner changes; the rejected v053 recolour is excluded.

- Match the older pale shoulder soil families to the accepted racing photographic blend. Extend the same photographic skin across bare margins with a soft transition, excluding grass, roads and pits.
- Expose more photographic grain/clod detail by halving the coarse macro overlay. Keep the route-aligned 8K grooming normal atlas with compensated strength; soften tiled micro-normal relief. Preserve the mean racing-photo hue. The retained photo shaders are copied byte-for-byte so source previews and native staging resolve the same normals.
- Reduce photographic soil tiles from 4K to 2K, the low-frequency colour atlas from 8K to 4K and selected older dirt tiles to 1K. Still 14 layers, with no added texture allocations. The unique active terrain inventory implies 540 MiB less RGBA8 base-level allocation, or 720 MiB with complete mip pyramids. These are dimension-based allocation estimates, not measured game RAM/VRAM or FPS.
- Level the inherited lateral rise on R03's table-single landing/runout. Independently sampled maximum cross-width variation drops from 1.916383 m to 0.056242 m. Maximum centreline change is 0.012983 m. The table and single profile arrays, other jump centreline heights and all RAW samples outside the bounded repair stay exact. Only 9,040 RAW samples change; maximum reduction is 1.843809 m.
- Lower only `SOFTCPLAS_marker_18` by 1.082352 m to bind it to the repaired ground. All other scenery object records, material/media records, counts and horizontal placement remain exact.
- Preserve the v054 native main/start routes, race/checkpoint/grid/pit/reset data, road-course terrain, lighting/cameras and menu imagery. Only the display version changes to v055.

Final terrain RAW SHA256: `c8a5bbd9896216b6714fc76de3cdd6cffe48c8110ddd9b30dd05897e4b2f03cd`.

Source previews omit scenery and are explicitly labelled as source renders, not MX Bikes captures. They include matched landing/material views, a close photographic soil comparison and independent landing height sections. They are attached to the release.

## Native and publication checks

The successful Windows run passed input recovery, terrain/scenery/race checks, material palette/allocation checks, matched source renders, official FBX2EDF export, TerrainEd collision, TrackEd main/start merge and TerrainEd graphics. Final native bitmap/coordinate checks, matte-foliage checks, retained race-file hashes and the 13-entry PKZ CRC/root/size checks passed. Source and native checkpoints were preserved before publication.

The published asset's size and GitHub SHA256 digest were independently compared with the successful job's `V055_NATIVE_VALIDATED` line; both match.

- PKZ: **434,106,527 bytes**, down from **920,767,498 bytes** for v054.
- Saving: **486,660,971 bytes (52.85%)**; approximately **434 MB versus 921 MB**, below 500 MB.
- PKZ SHA256: `3325ffd188332c64676e0f4c440b7c539711e0ae02b5be69fd2cd86ec156e47c`.
- Validation report: 104,246 bytes; SHA256 `5eadee61cd90469dece5415d2d3e2b8002b7f990d509793fe5f087fbfa270276`.
- Source checkpoint: 420,405,554 bytes; SHA256 `6dd62900fa5e4c68fe1fd3e6939bb407b7eace89c35cb11c49776868bc3a4f3b`.
- Native scenery checkpoint: 228,735,036 bytes; SHA256 `22aab8752b7160a3c787bbcbdd27b425ae987ac5d54b2dfc75ddb496f956b5dd`.

The PKZ, checksum, validation report, installation notes, source checkpoint, native scenery and comparison images are available in release `v055-soil-landing-38658838015` (release ID 413295265).

## Remaining game test

Actual MX Bikes load, first-lap timing, R03 landing riding, dirt/shoulder appearance and FPS require the user's game test. No in-game visual/riding/performance pass is claimed. Select v055 and reset the track before testing. All multiplayer participants must use the same PKZ.
