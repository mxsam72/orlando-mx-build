# Orlando MX — v027 versus IRL, and the v028 update

The largest remaining differences are the position of the new fence, foliage inside the practice approach, an overly bare and uniform-looking track environment, and weak separation between groomed soil, compacted riding lines and loose corner deposits. The new race footage provides useful side views of the berms and jump flanks. It supports a surface and scenery pass much more strongly than a wholesale change to the accepted jump dimensions.

This is an independent review of the supplied footage and the original correct-layout GoPro. The other ChatGPT instance's notes were not used to decide the changes. All times below refer to elapsed time in the actual supplied clip, not an on-screen YouTube player clock. Different speeds, camera heights and fields of view mean equal timestamps are not equal track locations.

## Sources and review method

| Short name | Actual source | Duration | Sampling and role |
|---|---|---:|---|
| Game lap | `test v027 multi lap.mp4` | 4:57.54 | 60 regular frames at 0:00–4:55, every five seconds, plus an end sample. Main riding, corners, jump transitions, pits and entry. |
| Game fence | `test v027 new fence area too far back must be closer to start gate.mp4` | 1:00.59 | 13 regular five-second frames plus an end sample. Slow inspection of the fence and apron. |
| Original GoPro | `Orlando MX 2026 GOPRO HD right layout with starting gate fenced area.mp4` | 5:33.08 | 67 frames at 0:00–5:30, every five seconds. Best continuous rider perspective and behind-gate topology. |
| New pit footage | `Orlando MX IRL footage of pits and start gate area and entry to track.mp4` | 0:42.88 | Nine regular five-second frames plus an end sample; additional one-second frames from 0:20–0:38. Best entry-sign, fence-corner and approach evidence. |
| New race footage | `Orlando MX IRL footage gold cup 2026.mp4` | 2:05.82 | 26 regular five-second frames plus an end sample. External views of riding lanes, grooming, berms, vegetation and jump flanks. |
| Marked image | `fence goes on edge of starting line clay, vehicles parked in that grass area.png` | Still | Direct placement instruction: fence on the clay boundary; vehicles in the adjacent grass. |

There are 175 regular five-second samples, four additional end samples and 19 dense pit-approach samples. Four dense samples duplicate regular timestamps, so there are 194 distinct sampled instants across the five videos. The original GoPro's 2:45 sample is black; it contributes no usable layout evidence. This is a frame-based review, with denser inspection of the critical pit transition, rather than a claim to have measured every frame or surveyed the property.

The race clip changes viewpoints and follows multiple riders. It is not reliable evidence of a continuous single-rider lap. Its camera pans are especially useful for cross-track profiles, but cannot establish the precise identity, height or spacing of every obstacle without a landmark match. No unverified jump number is assigned to a broadcast shot.

## 1. Starting gate, fence and behind-gate parking

**The new fence is too far from the clay edge.** In the game fence clip at 0:10, 0:30–0:40 and 0:50–0:55, the new timber boundary and the parked vehicles do not form the tight clay-edge/grass-parking relationship in the marked image. An extra grassy separation remains. In the original GoPro at 0:00–0:05 and 0:20–0:25, timber rails sit close to the staging and riding areas; bikes, pickups, stands and chairs occupy the shaded side of the fence. The fence should define that boundary, rather than look like a separate enclosure farther back in the paddock.

The source explains the offset. At the straight beginning of the accepted start route, the clay has an authored half-width of 19 m. V027 put the practice center 7.5 m beyond that edge and its inner rail 4.65 m toward the clay. That leaves a **2.85 m nominal gap**. V028 reduces the outer lane offset to 5.0 m. The rail then sits **0.35 m outside the nominal clay edge**, moving 2.5 m closer in the straight section. These are source-coordinate measurements, not IRL survey measurements. The physical mask has a feathered edge, so the visible in-game boundary remains a test item.

**The parking should read as a grass bay with wear, not one continuous pale apron.** The marked image explicitly places vehicles in the grass. Original GoPro 0:20–0:30 shows sandy wear under bikes and pickups, but the surrounding area remains a mixture of shade, grass and compacted ground. The new pit clip at 0:05–0:15 shows patchy grass beside the broad pit road. V027's newly added vehicles sit on a largely sand-colored staging rectangle. That makes the behind-gate area look like another roadway.

V028 places the added pickup, trailer, bike stands and bikes in the strip between the connector road and the starting-clay boundary. The new bay receives grass with local worn soil rather than full-strength pit sand. Existing custom vehicles and their textures remain in place. The new fence also follows the back edge of the accepted start apron, so the gate-side boundary has a coherent shape. Its western end remains open; the existing pit roads and pedestrian gate are retained. The supplied footage does not establish an exact surveyed track-exit location, so this opening is described as an authored open apron, not a proven IRL exit relocation.

**The shade should be overhead, with trunks outside the usable lane.** Original GoPro 0:05, 0:10 and 0:45 shows mature spreading trees with usable space beneath them. V027's approach at game lap 0:15 and 0:25 has low geometric foliage and a trunk close to the route. New shaded trees are useful, but adding more trees is not sufficient if older trees remain embedded in the path. V028 keeps the added shade over the parking side and checks the complete corrected approach for low geometry.

## 2. Practice entrance and corridor

**The entry has a distinct progression.** The new pit footage provides the clearest sequence: at 0:20–0:21, the rider is beside the small pit buildings and broad sandy frontage; at 0:22–0:25, the camera turns past the mature trees and dark timber-fenced island, with the white `TRACK ENTRY ONLY` sign visible; at 0:26–0:33, the sandy approach curves around the grass island; at 0:34–0:38, it narrows into the fence-and-vegetation corridor; at 0:40–0:42, it opens onto the active riding area. The lane is worn and sandy, with multiple tire grooves. It remains usable between the fence and woodland.

The original GoPro reinforces this relationship at 0:55–1:05: open sandy approach, fence and grass to one side, dense vegetation on the other. At 1:10–1:15, the entry continues through the metal barrier banks before joining the track. The sign, timber boundary, grass island, wooded edge and later barrier section are separate landmarks. They should not collapse into a long uniformly empty dirt strip.

**The tree problem is real, and it includes retained scenery.** Game lap 0:25–0:30 and game fence 0:35–0:40 show the route being crowded by trunks and low crowns. V027's validation covered its newly added meshes. It did not test all older foliage against the new route. The v028 source audit finds three retained objects crossing the corrected approach: `tree_414` at its first bend, `tree_474` along the straight entry, and `tree_500` farther along the corridor. All three are removed as complete objects. No general tree thinning is applied elsewhere.

V028 checks triangles, not just tree anchors. It samples retained and new geometry with triangle edges at most 0.5 m long and tests a 3.2 m rider headroom envelope with 0.65 m of lateral allowance beyond the authored lane. This catches a canopy that spans the lane even when its trunk or original vertices lie outside it. The final combined scenery must have zero detected low-geometry conflicts on the practice lane and connector. This is a source clearance check; collision flags, camera feel and the visible result still need a game ride.

**The merge should stay continuous.** Game lap 0:30–0:35 shows the transition onto the broader prepared riding surface. IRL pit 0:38–0:42 and GoPro 1:15–1:20 show a similarly continuous progression, rather than a curb or abrupt material strip. V028 moves the side approach and its masks together, retains the accepted terminal merge point and smooths only the authored approach. It does not move the race-start route or create a new join into an unrelated corner.

## 3. Dirt color and the separation of surface types

**V027 still reads as a broad brown carpet.** Across the game laps from approximately 0:35 onward, the prepared lane, large empty infield and adjacent bank surfaces are too similar in value and hue. Pale and dark selected lines exist, but they often read as markings on a uniform base. The real course has a clearer hierarchy: worked reddish-brown riding soil; darker compacted or moist lines; pale loose sandy margins; and green median islands or outer flanks.

This hierarchy is visible even in the sunny original GoPro: 1:20–1:40 shows darker riding strips beside lighter off-line ground; 1:50–2:20 shows greener lane dividers and a visibly different loose outer margin; 3:30–4:10 shows grass along berm interiors and jump sides. New race 0:00–0:10, 0:45–1:00 and 1:25–1:45 supplies useful cross-course views of the same distinction. V028 moderately darkens the prepared dirt and lowers the brightness of compacted lines, while keeping pit sand and loose shoulders lighter. The change is local and textured, not a flat whole-track dark overlay.

**Weather is a major confounder.** The game is shown in bright light. The new race views are softer and wetter, with standing water in some low off-line areas. The original GoPro is sunnier but also contains wet low areas around 1:35 and 4:15–4:20. It would be misleading to treat the race's darkest soil as a calibrated dry-track color. V028 retains a matte default with sparse damp-looking areas and existing wet material variants. It does not make the entire default track muddy and does not restore the previously removed drainage-water object.

**Close-up grain should remain distinct from medium-scale wear.** V027 has useful granular tile detail, but the real footage also shows organized grooming, local wheel paths and deposits. V028 retains the verified v027 grain and its granular normals, regrades its diffuse color, and adds stronger route-local grooming and wear on top. It avoids a low-resolution color atlas that would blur the surface at riding distance.

## 4. Grooming, straight riding lines and landings

**Longitudinal grooming is considerably more readable IRL.** Race 0:10, 0:40, 1:35–1:40 and 1:55 shows parallel ridges on worked faces and approaches. Original GoPro 1:45, 2:20, 2:40, 3:05 and 4:35–4:40 also shows the grain following the direction of travel. Game jump approaches around 0:55, 1:50, 2:20–2:30, 3:30 and 4:00–4:25 look comparatively homogeneous.

V028 strengthens the existing four-direction grooming treatment. The tile normal-height amplitude increases from an authored 4 mm to 7 mm, and the small diffuse ridge contrast increases as well. Direction blends still follow the accepted route heading. These are rendering parameters, not measurements of IRL rake teeth or a claim that the terrain rises by 7 mm everywhere. Normal-map grooves do not change jump takeoff height.

**Traffic breaks up fresh grooming.** IRL 1:20–1:35, 2:05–2:15 and race 0:50–1:00 show several usable lines rather than a single centered stripe. Some paths are compacted, some remain newly worked, and the pattern changes through entries and landings. V028 retains several gently wandering, interrupted straight-line masks and gives them more separation from the fresh groomed base. Packed masks take precedence over the freshest grooming. Landings receive some additional selected wear without creating a continuous dark centerline around the whole lap.

**Jump shoulders need environmental shape as well as ramp shape.** Side views in race 0:20–0:35, 0:55 and 1:05–1:15 show worked riding surfaces carried by rounded or uneven flanks, often with vegetation on their outside. GoPro 1:50, 2:10, 3:45 and 4:05–4:15 shows the same contrast from above. V027's tidier silhouettes and similarly colored sides make the jumps look isolated and artificial. V028 adds protected ground-cover masks on outer flanks and improves the dirt/loose-edge distinction. It leaves accepted takeoff, deck, landing and runout profiles unchanged.

## 5. Corners, berms and ruts

**Several corner lines should be visible at once.** Original GoPro 1:25–1:35, 2:05–2:15, 2:50–3:00, 3:10–3:20, 3:35–3:40 and 5:15–5:20 shows curved channels with raised loose soil between or beside them. Race 0:15–0:25, 1:10–1:20 and 1:50–2:00 adds an external view of riders selecting different lines. Game corners around 1:25–1:30, 2:05–2:10, 2:50–3:05, 3:40–3:50 and 4:20–4:35 more often read as a broad pale/dark ribbon, with limited separation between neighboring channels.

V028 uses the existing authored entry–apex–exit rut trajectories for both color and shallow terrain relief. Packed floors darken; loose banks remain lighter and more irregular. The additional channel-depth parameter changes from 24 mm to 36 mm, and the deposit-height parameter from 14 mm to 18 mm. The actual quantized terrain deltas are reported in the source validation and are bounded. These are modest authoring choices to make the existing lines readable, not an attempt to reproduce deep race-day ruts from uncalibrated footage.

**Corners should not all look like identical circular bowls.** IRL shows uneven deposits and changing line spacing through the turn. The accepted corner paths already differ by corner; v028 keeps those differences and the interrupted masks. It does not apply one identical offset ring to every berm. Outer radius, elevation and the accepted turn stations remain unchanged because the footage does not establish a reliable metric correction.

**The older R10/T09/R11 work remains protected.** The tree and marker removals previously planned as v026b are carried forward: `tree_215`, `tree_222`, and markers 53/55 remain absent. The accepted macro layout, including the existing R10 takeoff and relocated T09/R11 sector, is not rebuilt or shifted. The new relief follows the existing rut paths in that sector as elsewhere.

## 6. Infield, vegetation and distant appearance

**Grassy islands are an important missing cue.** Race 0:00–0:05, 0:25, 0:50–1:00 and 1:25–1:30 shows green areas dividing brown riding lanes. GoPro 1:50–2:00, 2:10–2:15, 3:30–3:50 and 4:05–4:15 makes them particularly clear from the rider's perspective. In the game, much of the equivalent space remains brown. That changes the apparent lane width and makes the course harder to read even where its centerline is already correct.

V028 adds irregular ground-cover masks between lanes and on outer jump flanks. It protects every nonzero accepted racing, shoulder, worked-berm and start-mask sample, plus the practice road and pit gravel. The new grass therefore cannot blanket the accepted riding core. Visual and off-line grass physical coverage are updated together; physical material declarations and the accepted main/start coverage stay intact. Exact grass distribution is an authoring estimate fitted to the accepted layout, not a georeferenced vegetation survey.

**The wooded perimeter still looks more simplified than IRL.** The real entry at pit 0:30–0:38 and GoPro 1:00–1:10 has dense lower vegetation, irregular trunks and overlapping crowns. The game's boundary has more evenly spaced, faceted canopy forms and less understory. V028 prioritizes removing the actual entry obstruction and correcting ground-cover context. It does not replace the entire existing tree asset set or add dense collision geometry beside racing lanes. Higher-quality perimeter foliage remains a useful later art pass after this version's ride test.

**Some green patches look geometric from the game camera.** Game frames around 1:15, 2:55, 3:30 and 4:10–4:30 include sharply outlined green forms on or beyond bank silhouettes. The frames alone do not establish whether each is a ground mask, distant foliage, shading, or an intersecting mesh. The retained source does not contain separately named grass planes that can safely be removed by name. V028 improves mask boundaries and adds source-grounded grass coverage; it does not delete unrelated scenery on the assumption that every green triangle is the same defect. These views should be revisited in the v028 ride, especially while cresting a jump.

## Implemented v028 scope

| Priority | Difference | Implemented response | Limit or next check |
|---|---|---|---|
| Immediate | New rail too far from starting clay | Move inner rail 2.5 m closer on the straight; follow the back edge of the start apron | Check visible feathered clay edge and fence end from the game camera |
| Immediate | Retained trees occupy the entry | Remove only retained trees 414/474/500; audit all nearby retained and new triangles | Ride slowly through both approach bends and under canopies |
| Immediate | Parking shown as a pale slab | Move added parking props into worn grass between road and clay-edge fence | Check vehicle spacing and bike stands from ground level |
| High | Brown infields obscure lane separation | Protected irregular grass islands and outer-flank coverage | Check grass does not create visual stripes or change edge grip unexpectedly |
| High | Grooming too faint | Stronger directional granular grooming, reduced by traffic wear | Check shimmer, tile seams and direction changes at speed |
| High | Corner channels merge visually | Darker packed floors, lighter loose deposits and slightly stronger shared relief | Check steering feel, deformation and reset after several laps |
| High | Dirt/shoulder hierarchy weak | Moderate darker prepared grade, stronger packed contrast, light pit sand | Compare using the same weather and game settings |
| Preserve | Unverified metric layout changes | Keep accepted route, jumps, turn stations and start geometry | New footage with a clear named mismatch would support the next geometry pass |
| Preserve | Existing custom work | Keep custom vehicle textures, signs, facilities, race/reset/marshal data and menu logo | Verify selection menu and race start in game |
| Later | Entire perimeter foliage quality | Keep useful existing shade; remove approach intrusions only | Consider an asset-quality pass after entry placement is confirmed |

## Verification and next ride

The source build verifies the tested v027 checkpoint before changing anything, protects accepted route and jump files, checks retained FBX records, and enforces the complete access clearance. The Windows build compiles fresh MAP and TRH files, checks native coordinate probes and decoded embedded terrain/prop texture signatures, and verifies the PKZ file set and ZIP CRC. The delivered validation JSON records actual hashes and sizes.

These checks establish that the candidate contains the intended source and compiled data. They do not establish MX Bikes loading, collision behavior, riding feel, deformation or performance. The next useful test is one slow lap through the pits, parking and entry, followed by several normal track laps. Film the fence from the starting-gate side, the route through the former three tree locations, the barrier merge, corners and jump crests. Review those frames every five seconds, using closer sampling around any fast transition. Compare FPS under the same bike, weather, graphics settings and camera, and verify start/reset behavior and deformation after at least five laps.
