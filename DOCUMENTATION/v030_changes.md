# Orlando MX v030 — corrected grass scope

Starts from the tested v028 source and grass, because v029 removed too much grass in the pits and on the course.

- Preserve main pits and parking grass coverage and the grass tile exactly from v028. Protect the paddocks below the spectator-fence boundary (Z ≤ 174 m, X < 373 m), encompassing both original pit grass parcels.
- Remove all visual and physical grass inside the supplied yellow circle, registered against the source overview using the start clay, approach road and main-loop shapes. Also keep the actual start/practice/connector corridor bare. The staging strip inside the explicit starting-section circle is part of this requested clearance.
- After that clearance, remove 50% of the remaining track-area grass within X 208–467 m, Z 174–442 m. Shrink every original grass patch independently by half, so the large outer field cannot dominate the reduction and erase smaller infield islands; surviving interiors keep v028 opacity. Calibrate the target against the encoded native visual-mask alpha sum, with tolerance ±0.01 percentage points.
- Preserve all other v028 visual surface masks and physical masks. Outside the defined track/start changes, grass remains v028.
- Retain the v029 2048-pixel dirt-material recipe and the corrected entry-board UV orientation on both faces. Restore v028 pits, sand and worked masks instead of carrying v029's broad exposed-soil or enlarged pits overlays.
- Preserve the entire tested v028 terrain, routes, jumps, race/reset/marshal data, scenery except the single corrected board UV property, custom textures and menu logo.

The hand-drawn circle is an approximate authoring boundary with 1.2 m padding. Previews show authored sources, not the game renderer. Source and native package checks do not replace an MX Bikes ride, loading test or performance test.

Immutable baseline: v028 commit d9e5ce03bd597cf5a87632387ec9f371ebe66ea2. v028 terrain SHA256: 954bb88ab989959257fc481db0caf241bb65bf771d46739f79207a4501c203a7.
