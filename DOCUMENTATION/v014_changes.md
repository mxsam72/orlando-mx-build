# Orlando MX v014 — v013 ride-test refinement

Base: v013 final branch head `9764acecab6ae697c89b7baa485b076ed2654d21`.

References:
- `testing v013 long video.mp4`
- `bathroom location movement.png`
- `inside single to extend horizontally.png`
- `trees to remove inside track.png`

All unlisted obstacle types, the v012/v013 start-lane routing, office placement, facility material fix, pit roads, spectator structures, fence system, and stable native build toolchain are preserved.

## Obstacle changes

- R02: 54 -> 49 m triple. First 18 m gap retained; second gap reduced 14.7 -> 9.7 m.
- R05: moved +15 m along route (399.6 m start), total length 24 -> 29 m. Existing v013 height retained; extra 5 m goes into the gap.
- R07: ant-hill crest remains at route station 552. Height increases exactly +5 m, 3.2 -> 8.2 m. To satisfy “5% less steep,” the v013 takeoff maximum grade is reduced by 5%, requiring ~24.28 m face length. Landing is lengthened to 24.3 m to keep the encoded terrain within grade QA.
- R09: total 50 -> 60 m. Takeoff and landing mound length/height are each reduced 20%; the added distance becomes a 35.68 m gap.
- R10: tabletop 75 -> 65 m by reducing deck 25.5 -> 15.5 m; takeoff and landing retained.
- R11: same 20 m low-lipped double shifted 5 m earlier.
- R12: four rolling singles. First two crest intervals remain ~10 m; last crest interval is ~5 m. A custom non-uniform roller profile is used.
- R14: same 55 m triple shifted 30 m earlier. Final landing crest reduced 10%, 3.0 -> 2.7 m.
- R16: same 46.3 m tabletop shifted 5 m earlier.
- R18: same inside-line-only 18 m roller; authored racing width doubles 2.8 -> 5.6 m with proportional side taper. Main-line exclusion remains active.

## Pit / scenery changes

### Bathroom
The v013 screenshot shows the desired restroom location in the grass patch close to RV02, to the right/east of its prior position. v014 uses an authored restroom center of **(365,119)**. The shade oak moves to **(369,126)**. These are relational, not surveyed, positions.

### Start-area trees
The user marked the trees inside the starting/track area for removal. v014 removes baseline `tree_` and `scrub_` scenery inside the authored native-X/Z box:

- X: 285 to 435 m
- Z: 180 to 320 m

This spans the infield left of the rightmost starting gate through the approach before the corner sequence toward R09. Parametric facility oaks below Z=174 m are intentionally preserved.

## Ride-validation emphasis

The most aggressive change is R07: +5 m height while simultaneously reducing takeoff steepness requires a much longer ant-hill footprint. Confirm visually and by riding that this matches intent.

Also verify:
- R09 has visibly smaller takeoff/landing mounds but a longer flight distance;
- R12’s fourth single is visibly closer to the third;
- R14 starts materially earlier but retains overall 55 m size;
- R18 is visibly wider only on the inside option;
- restroom matches the screenshot grass patch;
- the user-marked start-area trees are gone without stripping desired perimeter/facility trees.
