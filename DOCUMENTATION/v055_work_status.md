# Orlando MX v055: source checked, native build pending

Baseline: delivered v054, branch `rebuild-v054` at `029fe56`, with the accepted v052 racing palette and A/B/C starting-path/corner changes. The rejected v053 recolour is excluded.

Source work:

- Match older pale shoulder dirt families to the accepted racing photographic blend; extend the same photographic skin with a soft transition across bare margins, excluding grass, roads and pits.
- Reveal more photographic grain and clod detail by reducing the coarse macro overlay. Keep the route-aligned 8K grooming normal atlas; soften tiled micro-normal relief. Preserve the mean racing-photo hue.
- Reduce photographic soil tiles from 4K to 2K, low-frequency colour atlas from 8K to 4K and selected older dirt tiles to 1K. Still 14 layers with no added texture allocations. The unique active terrain inventory implies 540 MiB less RGBA8 base-level allocation (720 MiB with complete mip pyramids), a 44.25% reduction before mipmaps. This is an estimate based on dimensions, not a measured game RAM/VRAM or FPS result.
- Remove the inherited lateral hump on R03's table-single landing/runout. Maximum cross-width difference over the checked landing sections drops from 1.916 m to 0.056 m. The centreline changes by at most 0.013 m; jump-profile arrays and all unrelated jump centreline heights stay exact. Only 9,040 RAW samples change. All samples outside the bounded repair scope stay exact.
- Lower one marker, `SOFTCPLAS_marker_18`, by 1.082 m to bind it to the repaired ground. All other scenery object records, texture/media/material records, counts and horizontal positions remain exact.
- Native race/start lines, all race/checkpoint/grid/pit/reset references, road-course terrain, lighting/cameras and menu imagery remain exact from v054.

Local source height/palette/allocation checks and a complete native staging preflight passed (92 object bitmaps, five object normal maps). Matched source views show the landing repair and the shoulder blend. These previews omit scenery and are not MX Bikes captures. The close material view resolves photographic detail directly rather than pre-blurring it into a large-area preview atlas.

The official Windows workflow must compile FBX2EDF, TerrainEd collision, TrackEd line merge and TerrainEd graphics; then verify native texture signatures, object coordinates, matte foliage, retained race files and the 13-entry PKZ. Publication is gated on these checks and a package no larger than v054's 920,767,498 bytes. Source and native checkpoints are saved before publication for recovery.

Actual game load, first-lap timing, R03 riding, appearance and FPS still require the user's game test. This document does not claim a completed native build until the release section is added.
