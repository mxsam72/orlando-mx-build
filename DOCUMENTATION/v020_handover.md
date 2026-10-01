# Orlando MX v020 — active asset correction checkpoint

Base: delivered rebuild-v019 commit 002ab59e00200b5c64ee735bd8769f77d3e95bee; native Actions run 36776256304 succeeded. Work continues separately on rebuild-v020.

## Authorized changes

- Review supplied 71.94 s game clip `test v019 truck bikes and stop sign.mp4`.
- Relocate Bithlo sticker sign earlier on the road, left shoulder where pale gravel ends, as marked in `image(9).png`; replace oversized confetti-like geometry with faithful thin aluminum panels and reference artwork.
- Remove only old generic `pickup_03` at [321,149], heading -15, circled in `image(10).png`.
- Replace four crude bikes with realistic three-dimensional forms; investigate mxb-mods.com source assets.
- Improve Premier Power pickup geometry and continuous red/white/blue wrap.
- Preserve accepted Jordan Cybertruck, Sam King Ranch, Shane van, their placements, track terrain, start/race settings, pit roads and other facilities.

## Video evidence and current diagnosis

0–6 s: bathroom approach and proposed sign area. 9–18 s: oversized old sign beside office. 21 s: pickup_03. 24–36 s: four owner assets; 42–57 s: rear/side views. 60–66 s: Premier side/rear and Jordan bike.

Graphics visible in v019 software mesh renders are absent in actual game: Premier side wrap is white and bike number/shroud plates are blank. Solid diffuse colors survive. This strongly suggests native texture or UV export failure. Do not treat another successful source render or existing FBX-link check as sufficient verification. Diagnose with small FBX/EDF probes and verify bitmap data in the native output.

## Reference observations

- Bithlo sign: slender stickered metal pole, broad silver upper rectangular sign back with mounting rails, central red/white octagon densely covered in racing-number stickers, smaller lower rectangular sticker board. Old random colored raised blocks are incorrect.
- Premier: squared Chevrolet-style crew cab, dark off-road wheels, black bumpers and steps; white front door, large red power symbol spans rear door and window; blue lightning bed wrap with printed portrait. B&B logo belongs to adjacent van in reference and must not appear on this truck.
- Jordan: Husqvarna #759, black/white Rockstar, black rims in photo, white guards, FMF exhaust.
- Premier bike: blue Yamaha 450, #277 as interpreted from supplied photo, Premier Power shrouds, blue rims, gold forks.
- Sam: Yamaha 250F #373, blue/black, blue rims, black stand.
- Shane: Yamaha 450F #927, Central Florida Powersports graphic, worn blue seat, silver/black rims in photo.

## Recovery and external asset research

Current attachments exist locally in upload; original reference photos recovered in review_v020/references. Do not re-fetch current attachments from Library. Source recovered into orlando_v020 (no local Git checkout); remote branch exists. Use GitHub API commits for checkpoints. All 86 selected source files from delivered v019 have been recovered.

mxb-mods.com/2016-husqvarna-model-swap/ credits Jay's 2016 Husqvarna template/blend and links original release forum.mxsimulator.com/viewtopic.php?t=40364. Current OEM additional downloads mostly expose PSD graphics and compiled model swaps, not editable source. Direct HTTP retrieval of the Husky release and Yamaha Model Updates topic 43937 succeeded; HTML is in review_v020. Need inspect download/source permissions and usable model files before deciding whether to import. Do not claim downloaded or reused assets until actually integrated.

## Pending next steps

1. Diagnose native textures with a minimal Windows FBX2EDF workflow.
2. Inspect available real bike source models; implement replacements and preserve attribution.
3. Rebuild sign and Premier wrap, relocate sign, remove pickup_03.
4. Compare preserved vehicle meshes and terrain/start/race hashes; check all clearances and actual mesh previews.
5. Compile fresh v020 MAP/TRH/PKZ, validate native bitmap presence and package CRC; deliver test candidate with honest in-game-test status.

This checkpoint contains analysis, not a finished v020 game package. v019 remains the latest delivered build.
