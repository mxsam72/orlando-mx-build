# Orlando MX v013 — user-directed jump refinement

Base: v012 branch head `1436f9d016d10fdfce8283311013dea6d7353173`.
Ride-test reference: `testing v012.mp4`.
Facilities, start lane, materials, turn banks and all unlisted obstacles are carried forward from v012.

## User-authoritative changes

- R01: shorten tabletop by one-third: 77.2 m -> 51.47 m overall. Height retained.
- R02: retain triple. Interpret “make double twice its current distance from take off” as first landing/gap 9 -> 18 m; move third landing another 5 m beyond the previous second-to-third spacing, 9.7 -> 14.7 m. Overall becomes 54 m.
- R03: extend table-single by 15 m, 35 -> 50 m. Added 5 m each to deck, single gap and landing.
- R05: move obstacle 40 m earlier along route and double its v012 length and height: 12 -> 24 m, 0.7 -> 1.4 m. All main horizontal components doubled.
- R07: retain ant-hill single at the former double landing; make it moderately larger/steeper: crest 2.8 -> 3.2 m, face 10 -> 9 m, longer runout.
- R09: double v012 overall scale: 25 -> 50 m and 2.4 -> 4.8 m height, with takeoff/gap/landing dimensions doubled.
- R10: lengthen tabletop 50 -> 75 m. Horizontal components scaled 1.5x; height remains 3.3 m.
- R12: keep four rolling singles but change crest spacing ~5 -> ~10 m; sequence 20 -> 40 m.
- R14: enlarge signature triple 35 -> 55 m. New distribution: 12 m face + 1 m lip + 14.5 m first gap + 14.5 m second gap + 13 m landing. Crest heights retained.
- R17: keep eight singles/rollers but change crest spacing ~5 -> ~10 m. Sequence moved 40 m earlier so its prior endpoint is retained and it does not collide with R18.
- R18: triple inside-line roller physical size: 6 -> 18 m overall, 0.5 -> 1.5 m high. It remains inside-line-only and does not span the main line.

## Carried forward unchanged

R04 no jump; R06 no jump; R08 no jump; R11 20 m low-lipped double; R13 no jump; R15 single; R16 tabletop; v012 bathroom/office positions; v012 start loop; facility materials and texture-staging fix.

## Metric caveat

All dimensions are tuning/authoring targets, not surveyed measurements. The user's ride-test changes govern v013.

## Build assumptions requiring ride validation

R02 wording is implemented as explicit landing spacing changes described above.
R05 “bring it back by 40 m” is implemented as -40 m along route station.
R09 “2 times current size” is implemented as 2x overall horizontal dimensions and 2x crest height.
R07 “slightly steeper and bigger” uses a conservative 3.2 m crest and 9 m face.
