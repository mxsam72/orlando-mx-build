# Orlando MX v009 - Real Track Rebuild Specification

**Date:** 2026-09-26  
**Purpose:** Section-by-section construction specification for a close MX Bikes replica of the real Orlando MX track shown in the supplied GoPro footage.

## 1. Interpretation and accuracy rules
- **Source priority:** Use the real GoPro footage as the primary geometry reference. User-provided gametoGoPro times are approximate search anchors, not exact synchronized frames. When current game geometry conflicts with the real sequence, the real footage wins.
- **Do not preserve wrong geometry:** v007/v008/v008b proved the route is playable, but geometry is only approximate. Preserve only portions that agree with the real footage. It is acceptable to move jump faces, landings, turn apexes, and local centerline alignment.
- **Continuous terrain:** Do not model isolated jumps on a flat plane. Every section should be a continuous system of approach undulation, braking terrain, face, crest, landing, berm, exit, and next feature.
- **Corners are physical geometry:** Berms/ruts must exist in the heightmap/collision terrain. Visual rut masks alone are insufficient.
- **Width:** Separate total cleared dirt width from effective racing width. The visible dirt can remain broad while terrain shoulders, berms, ruts, and crossfall create a narrower usable corridor.
- **Jump individuality:** Do not reuse one generic tabletop template. Each major obstacle should have a unique face length, curvature, crest character, landing, and relationship to adjacent turns.
- **No false precision:** The footage is not a survey. Any dimensions used during construction are tuning estimates. Prioritize visual proportion, riding rhythm, and section sequence, then refine through in-game testing.
- **Visual baseline:** Preserve v008b's improved darker-brown dirt and reduced/cleaned tree treatment unless a terrain change requires scenery re-binding. Do not revert to orange dirt or the original dense blob-like tree wall.
- **Version safety:** Build v009 separately. Do not overwrite v007, v008, or v008b. Keep reproducible scripts and backups.

## 2. Approximate synchronization anchors
| Anchor | Real GoPro | MX Bikes v008/v008b |
|---|---:|---:|
| A | ~0:00 | ~1:50 |
| B | ~0:20 | ~2:14 |
| C | ~0:44 | ~0:47-0:48 |
| D | ~0:58 | ~0:54 |
| E | ~1:10 | ~1:03 |
| F | ~1:19 | ~1:19 |
| G | ~1:35 | ~1:35 |
| H | ~2:04 | ~1:52 |
| I | ~2:12-2:20 | ~2:03 |

These are search neighborhoods only. They are not frame-perfect synchronization.

## 3. Section-by-section real-track specification

### S01 - Opening fast straight and low rolling crest (0:00-0:12)
**Current-game search neighborhood:** Near Anchor A (~1:50 game), extending forward from that neighborhood.

**What the real footage shows**
- Fast, relatively open straight with a clearly used center corridor rather than a perfectly flat full-width surface.
- The surface rises and falls gently; the bike repeatedly loads and unloads even before the larger features.
- A low crest / shallow jump is integrated into the straight. It should feel like natural motocross terrain, not a standalone tabletop.
- Ruts and darker worked lines are concentrated through the useful riding corridor while the shoulders are less travelled.

**Current v008/v008b problem**
- v008/v008b is broader and smoother, with too much neutral flat terrain between modeled features.
- The low crest does not carry the same continuous approach-to-landing character seen in the GoPro.

**How to build it in MX Bikes**
- Keep the section fast. Do not overbuild it into a large jump.
- Create a shallow longitudinal wave before the crest so the suspension is already active on approach.
- Use a rounded, progressive face, a short rounded crest rather than a long flat top, and a gradual landing/runout.
- Shape the usable lane narrower than the cleared dirt by giving both edges slight shoulder falloff and irregularity.
- Blend this section continuously into S02; there should be no visibly flat reset between them.

**Ride-test validation:** At speed, the rider should feel continuous small vertical movement, then a noticeable but low crest, with no long flat platform.

### S02 - First major carved sweeper (0:12-0:22)
**Current-game search neighborhood:** Centered around Anchor B neighborhood (~2:14 game), but treat that time as approximate.

**What the real footage shows**
- A sustained banked corner dominates this portion of the real lap.
- The corner is deeply worked with several visible lines and a raised outer wall/berm.
- Entry, apex, and exit are not on one flat plane; the outside edge is materially higher than the inside line.
- The rider can carry momentum because the berm supports the bike rather than forcing a flat, open-radius turn.

**Current v008/v008b problem**
- The current game substitutes a much broader, smoother sweeper with weak cross-track elevation.
- Visual rut textures exist, but the heightmap does not provide enough physical bank or channelization.

**How to build it in MX Bikes**
- Rebuild this as actual cross-track terrain geometry: lower inside groove, progressively rising outside half, defined outer berm crest.
- Use asymmetric crossfall; do not make the corner a symmetric bowl.
- Tighten the effective riding radius while allowing a broader cleared dirt footprint outside the main line.
- Carry roughness and braking chop into entry, smooth slightly through the loaded apex, then add acceleration chop on exit.
- The exit elevation should flow directly into S03.

**Ride-test validation:** From cockpit view the outside berm should visibly rise beside the rider, and multiple usable lines should exist at different heights.

### S03 - Corner exit, crest sequence, and transition (0:22-0:34)
**Current-game search neighborhood:** Between Anchors B and C. The game recording wraps through its end/start here; do not infer a fixed timestamp.

**What the real footage shows**
- The rider exits the previous berm onto a shorter acceleration zone.
- There are repeated small elevation events: a low rise followed by a more obvious crest/jump.
- The terrain stays active all the way into the next direction change; it does not flatten completely.
- The second crest is broad enough to unload the bike but still reads as part of the track surface.

**Current v008/v008b problem**
- Current geometry spaces features too cleanly and tends to isolate them on flat terrain.
- The sequence loses the compact, linked rhythm visible in the GoPro.

**How to build it in MX Bikes**
- Use two linked longitudinal undulations rather than one generic tabletop.
- First feature: low rounded roller/crest; second feature: stronger rise with a longer landing transition.
- Keep the distance between them short enough that suspension movement from the first influences the second.
- Begin the next corner's crossfall before the landing/runout is fully finished.

**Ride-test validation:** The rider should never feel that the track 'resets' to flat between the previous berm and the next corner.

### S04 - Long bowl-like banked corner (0:34-0:46)
**Current-game search neighborhood:** Approaches Anchor C neighborhood (~0:47-0:48 game).

**What the real footage shows**
- A long, visually dominant bermed turn with a high outside wall and deeply worn inner-to-middle grooves.
- The bank develops progressively: entry is flatter, apex is strongly supported, exit opens and lowers.
- The corner occupies more of the rider's attention than any single jump in this section.

**Current v008/v008b problem**
- v008/v008b over-emphasizes a clean mound/tabletop in this general area and under-emphasizes the corner itself.
- The modeled surface is too broad and uniform.

**How to build it in MX Bikes**
- Make the corner the primary feature. Reduce any isolated-tabletop feel that competes with it.
- Use a long outside berm with non-uniform height; highest around the loaded middle/apex, tapering on both ends.
- Carve two or three usable grooves into the physical terrain at shallow depth rather than relying only on textures.
- Use a compact exit that immediately sets up S05.

**Ride-test validation:** When riding, the defining memory of this section should be the long supported berm, not a standalone jump.

### S05 - Linked turn complex into first clearly airborne jump (0:46-0:58)
**Current-game search neighborhood:** Anchor C to Anchor D neighborhood (~0:48 to ~0:54 game).

**What the real footage shows**
- The course continues through linked direction changes with heavy rutting.
- Near the end of the section, the track rises into a distinct jump face; by approximately 0:58 the camera/bike is clearly unloading or airborne.
- The face grows out of the preceding corner/exit terrain rather than appearing after a long flat run-up.

**Current v008/v008b problem**
- Current terrain is too clean and leaves too much separation between corner exit and jump face.
- The game mound is too mathematical and visually isolated.

**How to build it in MX Bikes**
- Shorten the neutral distance between corner exit and takeoff.
- Build the face as a progressive ramp: mild initial grade, stronger upper third, rounded lip.
- Avoid a long flat tabletop top unless the video clearly supports one; favor a rounded crest/short deck with a defined downslope.
- Shape the landing so the rider touches down already pointed toward the next section.
- Keep shoulders rough and uneven so the main line reads as intentionally prepared.

**Ride-test validation:** The jump should feel like the natural consequence of the preceding turn exit, not a separate obstacle placed afterward.

### S06 - Landing, rough acceleration lane, and next berm (0:58-1:08)
**Current-game search neighborhood:** Anchor D (~0:54 game) progressing toward Anchor E (~1:03 game).

**What the real footage shows**
- Landing transitions immediately into a visibly rough, rutted acceleration lane.
- The rider then commits to another strongly shaped corner.
- The real section has constant longitudinal texture and no broad smooth plateau.

**Current v008/v008b problem**
- The current game has too much smooth runout and an oversized open corner.
- Cross-track banking remains too weak.

**How to build it in MX Bikes**
- Give the landing a long progressive runout with small braking/acceleration waves embedded in it.
- Begin corner banking before the rider is fully finished with the landing runout.
- Build a raised outer berm and a lower inside rut, with a narrower effective lane than the visual dirt width.
- Use subtle height noise/chop aligned with travel direction; avoid random large bumps.

**Ride-test validation:** Landing compression should transition directly into corner setup. No long flat coast zone.

### S07 - Major elevated transition / jump into constrained corridor (1:08-1:18)
**Current-game search neighborhood:** Anchor E (~1:03 game), allowing a broad search window around it.

**What the real footage shows**
- A meaningful vertical feature is present here: the rider rises sharply and spends part of the sequence unloaded/airborne.
- Vegetation and track edges visually close in, making the corridor feel more constrained.
- The landing does not open into a giant flat area; it feeds the next direction change.

**Current v008/v008b problem**
- The corresponding game neighborhood is substantially flatter and more open.
- The vertical event is understated or misplaced.

**How to build it in MX Bikes**
- Add or relocate the missing vertical feature so it is a defining event of the section.
- Use a longer face than the existing generic low roller, with a clear crest and a landing that carries speed.
- Narrow the effective corridor using terrain shoulders, not invisible barriers.
- Blend landing crossfall into the next berm rather than flattening the terrain first.

**Ride-test validation:** From cockpit view the horizon should rise toward a distinct lip/crest, then the landing should immediately reveal the next corner.

### S08 - Deep carved berm and compact exit (1:18-1:30)
**Current-game search neighborhood:** Centered around Anchor F (~1:19 game), but do not demand frame-perfect equality.

**What the real footage shows**
- A deep, heavily used berm/corner is the main feature.
- The outside wall is clearly higher than the active groove and the bike is supported through the turn.
- The exit is relatively compact and quickly establishes the approach to the next major feature.

**Current v008/v008b problem**
- The game uses a much broader, more neutral turn with too much open dirt.
- The relative spacing between the preceding vertical feature and this corner is too loose.

**How to build it in MX Bikes**
- Treat S07 and S08 as one compound terrain system.
- Tighten the corner radius and raise the outside berm substantially relative to the inside groove.
- Use a clearly lower rut/channel through the preferred line, but keep alternate outer and middle lines rideable.
- Shorten the exit so the next approach begins immediately.

**Ride-test validation:** The rider should feel physically held in the berm and should arrive at the next approach sooner than in v008.

### S09 - Wall-like turn exit into the signature major jump (1:30-1:41)
**Current-game search neighborhood:** Anchor G neighborhood (~1:35 game).

**What the real footage shows**
- The section exits a tall banked wall/berm and rapidly presents a large, visually dominant jump face.
- Around 1:34-1:36 the jump face fills much of the forward view; it is one of the clearest signature obstacles in the footage.
- The face is long and naturally graded, not a short peaked bump.
- The landing/next terrain becomes visible progressively after cresting.

**Current v008/v008b problem**
- This is the strongest single geometry mismatch in v008/v008b: the corresponding game terrain is far too low/flat and the signature face is missing or dramatically understated.

**How to build it in MX Bikes**
- Make this a signature obstacle for v009.
- Start the face shortly after the berm exit; do not insert a long flat approach.
- Use a long progressive ramp with a stronger upper third and rounded lip.
- The face should visually obscure much of the horizon on approach.
- Use a distinct landing downslope with enough length to absorb speed, then immediately begin the next course direction change.
- Do not simply raise an existing mound vertically; reshape approach, face, crest, landing, and surrounding terrain as one sector.

**Ride-test validation:** A rider who knows the real track should recognize this section from the approach alone. The jump must be visually dominant before takeoff.

### S10 - Landing corridor, tree-side acceleration, and berm (1:41-1:54)
**Current-game search neighborhood:** Between Anchor G and Anchor H; current mapping is approximate and should be solved by sequence, not time.

**What the real footage shows**
- After the signature jump, the rider lands into a narrower corridor bordered closely by vegetation.
- There is additional low vertical movement / wheel unloading through the acceleration lane.
- The section then transitions into another pronounced carved turn near the end of the window.

**Current v008/v008b problem**
- Game terrain is too open and does not preserve the same close jump-to-corner rhythm.
- The next turn lacks the same physical berm presence.

**How to build it in MX Bikes**
- Use a landing that narrows into the corridor rather than opening outward.
- Add one or two low rollers/terrain waves after touchdown instead of a flat straight.
- Begin braking chop and crossfall before the next berm.
- Build the berm with a physically raised outer edge and a lower preferred groove.

**Ride-test validation:** The rider should land, settle once or twice through low terrain, and immediately be committed to the next berm.

### S11 - Berm exit and fast tree-lined acceleration (1:54-2:05)
**Current-game search neighborhood:** Approaches Anchor H neighborhood (~1:52 game).

**What the real footage shows**
- The rider exits a strongly carved turn onto a fast lane with vegetation relatively close to one side.
- The straight is not dead flat; it rolls subtly and carries visible ruts.
- The section acts as the setup for the utility-pole / major-ramp neighborhood.

**Current v008/v008b problem**
- The game tends to flatten this setup and make the lane wider and more featureless.

**How to build it in MX Bikes**
- Keep speed high but maintain subtle longitudinal relief.
- Use a shallow crown or directional crossfall rather than a perfectly planar strip.
- Preserve visible track-side openness/vegetation relationships from v008b where they agree with the footage.
- Gradually build elevation toward S12; do not introduce an abrupt isolated ramp.

**Ride-test validation:** The rider should sense that terrain is building toward the next feature before the main face is visible.

### S12 - Utility-pole approach and broad ramp (2:05-2:16)
**Current-game search neighborhood:** Anchor H (~1:52) through Anchor I neighborhood (~2:03).

**What the real footage shows**
- This is one of the best landmarked sectors because utility poles / track-side infrastructure help identify the area.
- The approach is rolling and slightly directional rather than a flat runway.
- A broad ramp/crest develops around the 2:10-2:14 neighborhood.
- The face is long and continuous; it looks like a shaped hill/ramp rather than a compact tabletop mound.

**Current v008/v008b problem**
- v008/v008b has recognizable general topology here but the approach is too flat, too open, and the main feature is too mound-like.

**How to build it in MX Bikes**
- Keep the utility-pole environment as a hard alignment reference.
- Introduce low pre-ramp undulation and slight crossfall before the main face.
- Lengthen the main face and spread its elevation over more distance.
- Use a rounded lip/crest with a clear downhill landing, avoiding a blocky flat top.
- The landing should already orient the rider toward the next turn.

**Ride-test validation:** The section should read as a long rising piece of terrain, not 'flat straight then jump'.

### S13 - Post-ramp direction change and second crest (2:16-2:28)
**Current-game search neighborhood:** Immediately after Anchor I; use sequence continuity from S12.

**What the real footage shows**
- The rider changes direction after the ramp and quickly encounters another rise/crest.
- The track remains heavily worked with several parallel grooves.
- The second elevation feature is medium-scale and integrated into the turn exit.

**Current v008/v008b problem**
- The game generally leaves too much smooth, open transition area and separates the next crest from the turn.

**How to build it in MX Bikes**
- Start the turn geometry during the landing/runout from S12.
- Use a raised outside shoulder/berm with a lower inside groove.
- Place the second crest close enough to the exit that throttle application and suspension load carry directly into it.
- Keep the second crest smaller than the signature S09 jump.

**Ride-test validation:** The rider should transition from landing to turning to cresting without an obvious neutral zone.

### S14 - Rough finishing straight and final sweeper (2:28-2:38)
**Current-game search neighborhood:** Following S13; the exact game timestamp is not considered authoritative.

**What the real footage shows**
- A rough, rutted acceleration section leads into the final visible sweeping turn before the reference video ends.
- The surface contains broad worked lines and low rolling/chopped relief rather than a polished flat straight.
- The final corner again relies on banking and rut structure more than on a discrete jump.

**Current v008/v008b problem**
- Current terrain is generally too planar and the final turn is too smooth/featureless.

**How to build it in MX Bikes**
- Add low-amplitude longitudinal roughness with coherent directionality.
- Use a compact bermed final sweeper with actual cross-track height difference.
- Blend the end of S14 into the beginning of S01 so the lap closes naturally with no seam or sudden terrain reset.

**Ride-test validation:** The final corner should feel like part of the same continuously worked motocross surface and should connect seamlessly back to S01.

## 4. Implementation plan for Astra
1. Create a new branch/version named rebuild-v009-geometry and retain v008b as the visual baseline.
2. Before editing terrain, create a section_station_map.json that maps S01-S14 to route station ranges in the existing route.npz/centerline. Use the GoPro sequence, the approximate A-I anchors, the game video, and environmental landmarks. Mark confidence per boundary.
3. Do not assume current J01-J12b IDs are correct physical equivalents. Use them only as editable source geometry. If the real feature occurs elsewhere, move/replace the profile and update IDs/metadata accordingly.
4. Represent each section as a sector-level terrain operation, not only a jump profile. Each sector may modify centerline elevation, cross-track banking, berm height, shoulder falloff, rollers, jump face/crest/landing, and transition blending.
5. Use smooth C1/C2-continuous blends between terrain operations to avoid artificial kinks. Keep lips purposeful but not polygonal.
6. For berms, create asymmetric cross-sections with a lower preferred groove and progressively raised outside terrain. Taper berm height before entry and after exit.
7. For jumps, use progressive faces and long landings. Avoid identical face lengths and flat-top dimensions across obstacles.
8. After major geometry edits, regenerate terrain.raw/terrain_16bit.png, rebind scenery to the new terrain, rebuild race/start data if centerline changes, then compile MAP/TRH with official PiBoSo tools.
9. Create before/after evidence: overhead heightmap, centerline with S01-S14 boundaries, longitudinal centerline elevation, cross-sections through major berms, and per-section screenshots.
10. Compile and ride-test v009. Evaluate recognizability by section sequence and riding rhythm, not by one-frame screenshot matching.

## 5. Ready-to-copy Astra master prompt

```text
You are continuing the Orlando MX 2026 MX Bikes track rebuild. Your task is to create v009 as a separate geometry-focused version using the real GoPro footage as the authoritative reference.

FILES / BASELINE:
- Start from the proven playable v007/v008 source in repository mxsam72/orlando-mx-build.
- Preserve the v008b visual improvements: darker neutral-brown Florida loam and the reduced/cleaned tree treatment.
- Do not overwrite v007, v008, or v008b.
- Use both reference videos: the real Orlando MX GoPro lap and the current MX Bikes test lap.
- Read the detailed section specification OrlandoMX_v009_Real_Track_Rebuild_Spec_2026-09-26 before making edits.

SYNC RULE:
User-provided GoProtogame timestamps are approximate section anchors, not exact frame sync. The current game track is known to contain real geometry differences, so a mismatching screenshot can be evidence that the game geometry is wrong. Compare short windows and topology: turn order, jump order, approach/landing/turn relationships, terrain rise/fall, utility poles, vegetation, and what comes before/after each feature.

PRIMARY GOAL:
Make v009 feel recognizably like the real Orlando MX lap section-by-section. Correct not only jump height but feature placement, obstacle spacing, berm geometry, crossfall, effective track width, continuous terrain between obstacles, and local centerline alignment where required.

MANDATORY WORKFLOW:
1. Build a section_station_map.json mapping S01-S14 from the specification to current route station ranges, with confidence levels.
2. Reconstruct the highest-confidence / highest-impact sectors first: S09 signature jump, S07-S08 jump-to-berm compound section, S04-S06 corner-dominated complex, and S12-S13 utility-pole ramp sequence.
3. Treat terrain as continuous sectors, not isolated jump objects.
4. Build real heightmap berms and ruts; visual masks alone are not sufficient.
5. Give each jump a unique profile derived from the real footage.
6. Preserve v008b visual baseline and rebind scenery after terrain changes.
7. Compile v009 with official PiBoSo tools and produce a separate PKZ.
8. Save all scripts, source changes, validation results, and a concise ride-test checklist.

QUALITY BAR:
- No long flat reset zones between features unless the real footage clearly shows one.
- No repeated generic tabletop recipe.
- Corners must have meaningful cross-track elevation and physical berm support.
- The signature jump near GoPro ~1:35 must be visually dominant on approach.
- The utility-pole sector must read as rolling approach -> long ramp -> crest -> landing -> immediate direction change.
- The lap should be judged by recognizability and rhythm relative to the GoPro footage, not by preserving legacy v007 geometry.

Read and follow every section S01-S14 in the specification. If a current jump ID or route segment conflicts with the real footage, change it. Do not hallucinate surveyed dimensions; use estimated geometry, document assumptions, and keep all changes reversible.
```