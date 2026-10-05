# v025 video review and v026 changes

Source: `test v025 new dirt color.mp4`, 237.759979 seconds, 2560 × 1078, 30 fps. User requested sampling every **5 seconds**. Reviewed all 48 regular samples at 00:00, 00:05, …, 03:55. Also extracted and reviewed 63 supplemental frames at one-second intervals around 00:51–01:02, 01:12–01:23, 01:27–01:37, 02:38–02:50, and 03:42–03:56. Supplemental timestamps overlap some five-second samples. This is a frame review, not an FPS benchmark or an MX Bikes simulation.

## Observed visual issues

- A consistent orange/ochre cast is visible across the riding area and jump faces. The recent Orlando photographs instead support restrained brown, cocoa-taupe corners and lighter neutral taupe exposed faces.
- At 00:54–00:56, a broad smoother band crosses the jump face while adjoining earth keeps much coarser grain. Similar transitions are visible around 01:15–01:17, 01:27–01:37 and 02:43–02:47. The five-second samples at 00:55, 01:35 and 02:45 are useful anchors. Abrupt differences in apparent texture scale weaken the natural appearance.
- Some long curved wear paths resemble smooth ribbons. Fine granular texture is much less visible within these paths than beside them. The footage alone cannot establish the exact native normal-layer blend; the v025 source's high-opacity coarse color/normal atlas is a concrete contributing design risk.
- The tree canopies and some green scenery patches remain visibly stylized. Those are separate scenery assets and are preserved for this focused dirt/R10 revision; a terrain-material change does not fix their models.
- Crashes and camera motion occur in the clip. Do not attribute an individual crash to one geometry defect from a single still. The R10 change is explicitly requested by the rider and is corroborated by source station data.

## Source corroboration

v025 uses the accepted v024 terrain unchanged. R10's landing/runout ends at source station 813.2 m, while T09's curve begins at 798.733 m: the curve already begins about 14.47 m before that landing ends. The revision therefore needs a real route/terrain change, with matching graphics and collision output.

The four v025 dirt families derive from one generated image. v026 introduces four original structure families: granular soil, compacted dirt, loose fractured clods and finer shoulder sand. Packed and jump-face variants use the compacted family, with matching repeating normal maps. Palette targets are artistic adjustments, not calibrated albedo measurements.

## v026 implementation

- Neutral brown/taupe palettes replace the orange material family. Grain, clods and compacted soil remain structurally different.
- Remove the single non-repeating coarse diffuse/normal wear atlas. Use route-aligned masks of fine repeating materials, with discontinuous corner paths and localized clod banks. No layer uses the former smooth coarse color overlay.
- R10's designed lip height increases **4.55 → 5.00 m**. Its 70 m total footprint and 28.5 m landing length remain the design targets; its deck also rises to meet the higher takeoff. The designed face angle increases about **28.02° → 30.32°**. These are source profile values, not a predicted in-game flight height.
- Translate T09 **20 m forward along its incoming tangent**. Its authored bank height, width and rut recipe are retained. This creates about **5.56 m** from the landing end to the curve start in the revised source route. The entry bank blends in gradually.
- Carry R11's unchanged 20 m low-lip profile onto the new corner exit, 14 m after the revised arc ends, and rejoin the fixed following route. Other terrain outside the explicit patch stays byte-for-byte identical.
- Rebuild the native centerline, local physical-mask coverage, checkpoints and reset lines together. Starting grid and pit world positions, scenery, vehicle/sign graphics and menu-logo image stay protected.

## Acceptance still required in MX Bikes

Use the same bike, weather and graphics settings as v025. Check color in sunlight and shade; inspect the named transition windows' equivalent sections at rider height, while stopped and while riding. Confirm fine detail in worn paths and on jump faces. Ride R10 through T09 and R11 for launch height, touchdown room and corner flow. Test fresh terrain, five laps and a longer deformation session; check resets and compare performance. Source previews are not game screenshots, and native compilation does not validate handling or final appearance.

Native authoring controls are grounded in [PiBoSo's MXB Track Creation Guide](https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide): TGA textures, alpha-channel masks, matching repeating normal maps, and paired TerrainEd graphics/collision outputs. [TrackEd](https://docs.piboso.com/wiki/index.php/TrackEd) documents the centerline and race/reset data workflow.
