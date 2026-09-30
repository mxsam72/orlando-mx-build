# v012 resume checkpoint — native build complete

Source/native input commit: `60b028fdc38f1c3e6470d4d7ae2ff61fee13e877`.
Branch: `rebuild-v012-final-obstacles-layout` in `mxsam72/orlando-mx-build`.
Actions run: `36660342389`.
Conclusion: **success**.

All requested R01–R18 geometry is authored; bathroom/office placement and outside-T05 start loop are implemented. All 18 encoded profiles, 24 gate positions, checkpoint modes, loop topology and 91 facility mesh clearances passed source validation.

Native compilation completed successfully:
- fbx2edf: success
- terrained_map: success
- terrained_trh: success
- tracked_merge: success

Artifacts:
- `OrlandoMX-v012-game-candidate` — ID `11074262287`
- `OrlandoMX-v012-build-evidence` — ID `11074092566`
- `OrlandoMX-v012-source-checkpoint` — ID `11074650064`

Verified PKZ:
- `OrlandoMX_2026_v012.pkz`
- SHA-256: `48345f6e11191e3c30291e45e5c507770de30cd82cd07b598d70809f8a265a25`

Final terrain after start grading SHA-256:
`51fdde42715d5494c6e33cd20740fde442ae51f55e4d99fd4567b21f6c4782ad`.

What remains:
1. Install and ride v012 in MX Bikes.
2. Validate 24-rider gate start and loop into T06.
3. Validate first finish crossing / lap timing.
4. Validate start-lane and merge resets.
5. Ride a full timed lap.
6. Confirm R01–R18 behavior against the checklist.
7. Confirm facility materials/colors in game.
8. Multiplayer test only if desired.

Native success is not an in-game ride-test claim.
