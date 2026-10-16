# v065 — C start dirt and cleared left grass band

The v064 overlay masks were empty over the opening start straight. v065 extends
the accepted C photographic soil, packed-soil contrast and virtual relief over
that missing area. It also clears the circled visual grass band between the
straight and the adjacent course. Its far end has an explicit world-space
window, preventing projection onto the bending start route from leaving grass.

Only five existing terrain images change. Mask RGB and the normal atlas's
specular alpha remain exact. Image dimensions, slots, 14 layers and source
texture allocation stay unchanged. Pixels outside the scoped start/strip edit
remain exact; the adjacent B course is protected from C material replacement.
Pit grass behind the start area remains outside the edit.

Terrain RAW and scenery FBX are byte-exact to the successful v064 source. The
wall-entry roller, all other jumps, corners, vehicles, sign, race data and game
lighting are retained. The authenticated unchanged native EDF is reused.

`TOOLS/v065_inputs.py restore` recovers the self-contained v064 checkpoint and
authors these edits. Generated material hashes must match the reviewed
`native_expected_inputs.json`. The Windows workflow stages all references,
preserves a complete source checkpoint, compiles native terrain/collision,
merges race routes, verifies both complete height grids and texture payloads,
then publishes a validated PKZ. Actual game appearance, riding and runtime
memory use require a game test; source allocation checks do not measure FPS.

The cinematic scripts use actual source geometry, UVs, photographic maps and
scenery. Their lighting is for presentation, so the images are source renders,
not native game captures. They do not change the game lighting file.
