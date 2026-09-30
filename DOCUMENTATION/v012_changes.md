# Orlando MX v012 — obstacle and layout changes

Built on the corrected v011 material baseline, `56b7fed68c210c6090458d046a6ddc7490be9267`, in the separate branch `rebuild-v012-final-obstacles-layout`. The September 29 v012 handover is authoritative. Older versions are preserved.

## Track changes

- R01: long tabletop, 77.2 m overall, twice the former 38.6 m raised feature. Its 45.6 m deck has been graded to remove a buried legacy step. The existing finish plane remains at s23, on the extended deck.
- R02: 40 m triple, using three crests and two real valleys. Distribution: 8 m face + 0.8 m lip + 9 m first gap + 9.7 m second gap + 12.5 m landing.
- R03: 35 m table-single. Distribution: 9 m face + 0.8 m lip + 7 m deck + 9 m gap to the separate single + 9.2 m landing.
- R04, R06, R08 and R13: remove the former jump envelopes; retain ordinary ground, corner banks and small local braking relief.
- R05: low 12 m double moved to end 2 m before T05 begins, so its landing leads into the corner.
- R07: one 2.8 m ant-hill mound with authored crest at s552, the former double's landing. The old takeoff and gap are removed.
- R09: 25 m double with independent takeoff and landing.
- R10: 50 m tabletop, including a 17 m deck and 19 m landing.
- R11: 20 m shallow double, only 0.5 m at the takeoff crest.
- R12: four individual rolling singles, 5 m crest spacing.
- R14: 35 m large triple, replacing the tabletop. Distribution: 8 m face + 0.8 m lip + 9 m first gap + 9 m second gap + 8.2 m landing.
- R15: retain the existing single's location and dimensions.
- R16: replace the double with a 46.3 m tabletop, 5 m longer than the former feature; 21 m deck.
- R17: eight individual rollers, 5 m crest spacing.
- R18: a 0.5 m roller on the inside-left line entering T14. The obstacle is only 2.2 m wide, centered 3.4 m left of the route. The normal line has no R18 jump envelope.

All overall dimensions exclude zero-height sampling padding. Heights and absolute positions are construction estimates, not surveyed measurements. Gap and triple arrangements follow the explicit handover; they supersede earlier provisional GoPro interpretations. The encoded-profile sheet shows actual terrain, including ground effects, alongside authored earthwork.

## Start and facilities

The gate remains to the right of the spectator frontage. Its 24 stalls span 34.5 m on a level 38 m apron. The new 166.79 m chute loops outside T05 and meets the normal route at s493, 4.694 m before the T06 right-hand corner. It is 7 m wide at the tightest point; its minimum edge clearance to the separate R08 lane is about 0.78 m. Its final segment converges along T05's outer exit shoulder, with the normal route centerline unchanged.

First-lap source data uses three start-only checkpoints, T06–T14 as Both, and T01–T05 as normal-only. Normal-lap reset boundaries, finish and splits are preserved. These source checks must still be confirmed by an in-game 24-rider start, timing and resets.

Bathroom: moved between the eastern RV and toy hauler, with its shade tree, clear of the pit-road connector and spawn rows.

Office: moved left of the red pickup nearest the spectator frontage. “Left” is negative X when viewed from the pit road toward the fence (+Z); the marked overhead shows the chosen truck and orientation. This assumption needs the user's visual confirmation in the next test.

Existing camper/vehicle, building, seating, fence and vegetation assets are retained. Pale pit roads and the corrected v008b dirt texture baseline are preserved. Intended facility colors are stored in FBX diffuse/ambient values, with diffuse bitmap links retained; generated textures are staged in both the build root and scenery.fbm before native import.

## Reference use

The v011 test ride and all five IMG_3591/3592/3594/3595/3597 clips are available. The newly available 3591/3592 show the open camper/paddock setting, pale access roads, shade trees and facility frontage. The prior 3594/3595 side views establish the front tabletop and spectator fence/seating character. Prior GoPro station mapping anchors the R sections. None provides surveyed dimensions or speed-locked telemetry; the user's v012 type/count/length list governs this build.

## Source QA completed

All 18 encoded profiles pass. The two rhythm sections retain their four/eight crests. Independent valleys remain visible in the doubles and triples, and the tabletops retain decks. No excessive new slope spikes occur; untouched surrounding terrain is unchanged. Start grading leaves the normal centerline unchanged, and all 24 gate levels match. All 91 facility meshes clear the main lane, start lane and pit spawn points. FBX color/link assertions and dual texture-stage checks guard the previous white-object failure.

The final native result, build SHA, run ID, file size and SHA-256 are recorded separately in `v012_build_record.json`. Native success does not replace the supplied ride-test checklist.
