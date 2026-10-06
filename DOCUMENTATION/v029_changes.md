# Orlando MX 2026 v029

Requested correction to tested v028: remove most grass, fully clear both marked start/practice corridor strips, correct the inverted TRACK ENTRY ONLY board, and improve dirt quality.

## Actual video review

Reviewed the complete 169.88-second supplied v028 recording as 34 regular five-second samples, plus the three marked stills. Reviewed the supplied correct-layout GoPro as 33 ten-second samples and the Gold Cup race clip as 25 five-second samples; source durations are 333.08 and 125.82 seconds. Sampling timestamps are interval midpoints (2.5, 7.5, etc. for five-second cadence). This is a sampled-frame review, not a claim of survey measurements or continuous real-time playback.

- Game 0:22.5-0:32.5: the entry board is inverted; the fence-side approach has a continuous grass strip. The user's stills identify the strip at roughly 0:28 and the starting-clay strip at roughly 0:33. Both are explicit complete-removal targets.
- Game 0:47.5-1:17.5: continuous green infields, including a sharply edged green area at 1:17.5, make the surrounding course resemble maintained turf.
- Game 1:27.5, 1:52.5, 2:17.5 and 2:27.5: broad green areas remain close to riding lanes and jump flanks. Dirt has granular detail, but cohesive clods and broken directional wear are comparatively weak.
- GoPro 0:55-1:15: entry is predominantly sandy/worn dirt. GoPro 1:35, 2:25-2:35, 4:25-4:55 and 5:05: substantial exposed soil divides the riding lanes; grass is irregular, with bare sandy patches.
- Race 0:02.5-0:17.5 and 1:02.5-1:32.5: discontinuous grass and large bare deposits, visually cohesive worked clods, curved channels, and grooming on the riding faces. Wet weather and different cameras prevent a calibrated colour match.

## Implemented

- Replace v028's high-opacity continuous grass with sparse irregular remnants, eroded edges and broader bare soil margins. Native 2048-grid visual and physical grass exclusions include the entire start clay plus a 3 m margin, and the connector/practice lane plus 2.6 m on either side.
- Grass is zero inside these exclusions, including both marked strips. No new grass is introduced anywhere. Removed grass exposes soil with local sand variation. The sandy approach surface is extended over its cleared rail-side margin while preserving the starting clay and active prepared lane.
- Correct the entry-board V coordinates; reverse faces also get the correct U orientation. The full FBX roundtrip proves that only the board's UV property changes. Sign position, mesh vertices, connections and texture are retained.
- Rebuild dirt families at 2048 pixels with accepted granular source detail, cohesive clod variation, correlated normal maps, finer dirt grain, darker compacted floors, and broken directional grooming. Wet variants and matte defaults are retained. Normals add visual detail without physical terrain changes.
- Preserve the complete v028 terrain RAW, route, start/main TCL, jump profiles, turn/geometry specifications, coordinate probes, race/reset/marshal data, custom vehicle/facility textures and menu logo. Only the grass physical mask changes; material declarations remain accepted.

## Source and native checks

Protected parent: d9e5ce03bd597cf5a87632387ec9f371ebe66ea2 (rebuild-v028). New work is on rebuild-v029. The immutable v027 checkpoint from workflow 37401771946 is restored and verified. Unmodified v028 generators reproduce delivered v028 terrain SHA-256 954bb88ab989959257fc481db0caf241bb65bf771d46739f79207a4501c203a7. V029 must retain that exact terrain.

Source validation records measured grass reduction, zero grass samples in the exclusions, two-sided board UV orientation, periodic tile/normal boundaries and protected hashes. The Windows workflow compiles fresh MAP/TRH, checks coordinate probes and embedded texture signatures, and verifies PKZ entries and ZIP CRC.

## Practical limits

Source previews are not game screenshots. Native checks do not establish in-game appearance, loadability, handling, deformation or FPS. The 2048-pixel dirt tiles use more texture memory than v028. The native validation records an estimated resident/mip footprint; compare in game under identical settings.

## Next ride

Inspect the entry sign from both sides. Ride the complete connector, fence-side corridor and start area slowly, checking the former grass strips. Record a normal lap showing grass remnants and dirt at ground level and jump crests. Check deformation/reset after several laps, and compare FPS with v028 using identical weather, bike, camera and graphics settings.
