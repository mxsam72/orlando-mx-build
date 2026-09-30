# Orlando MX v016 — v015 ride-test refinement

Base: completed v015 source branch `rebuild-v015-jump-pit-grass-refinement`.

Reviewed references:
- `testing v015.mp4`
- `make the anthill smaller by 10% and just get rid of that water near it.mp4`
- `bathroom in wrong spot needs to be close to that red truck and that whol patch should be grass too.mp4`

## Video-derived observations

- R07 is much improved from v014 but remains too large in v015. The focused clip also clearly shows the drainage-water patch beside the feature, which the user wants removed.
- The bathroom is still in the wrong visual cluster. The focused pit video shows the desired relationship farther toward the red-truck/canopy frontage rather than beside RV02.
- The rest of v015 is retained except for the explicit R10, R11 and R18 changes below.

## User-authoritative v016 changes

### R07
- Preserve ant-hill type and crest station s552.
- Scale v015 ant-hill to **90%** of its v015 longitudinal footprint, height and side support.
- v015: ~36.43 m / 6.15 m high.
- v016 target: ~32.79 m / 5.535 m high.
- Preserve 10 m riding width.
- Remove the visible water next to it by removing baseline scenery model `drainage_water_2`. Preserve `drainage_water_1` elsewhere.

### R10
- Start **5 m sooner**: s741.2 -> s736.2.
- Make takeoff **5% steeper** by increasing height/face grade exactly 5% at unchanged 3.3 m height; face becomes ~18.571 m.
- Make total feature **5 m longer**: 70 -> 75 m.
- Preserve 28.5 m landing.
- Adjust deck to ~26.429 m so exact total length remains 75 m.
- End remains s811.2.

Note: this intentionally creates ~5 m longitudinal overlap with the final R09 envelope because the user explicitly requested R10 begin 5 m sooner while leaving R09 unchanged. Validate this transition in game.

### R11
- Preserve 20 m feature length and location.
- Make low-lipped double 5% steeper by raising takeoff crest 0.500 -> **0.525 m** and landing crest 0.450 -> **0.4725 m**.

### R18
- Preserve inside-line-only placement and longitudinal shape.
- Increase authored riding width exactly **3 m**: 7.1 -> **10.1 m**.
- Preserve +3.4 m lateral offset and main-line exclusion.

## Pit / bathroom changes

The bathroom is moved out of the v015 RV02 location and into the red-truck/canopy frontage:

- Restroom center: **(288,145)**
- Red pickup `pickup_02`: **(295,147)**
- Canopy `canopy_01`: **(304,149)**
- Restroom is therefore ~7.3 m from the red truck and is west/left of the canopy.
- Bathroom shade oak moves to **(284,156)**.

A new grass paddock is added:

- X: **278–312 m**
- Z: **140–162 m**
- Covers restroom/red-truck/canopy/office frontage.
- Pit roadway masks override grass so road surfaces stay road.

The prior RV02 grass patch from v015 is preserved rather than reverted to dirt.

## Preserved systems

All other v015 obstacle geometry, start-lane routing, start checkpoints, office location, start-area tree clearing, facility materials, spectator scenery and native build tooling remain unchanged.

The Orlando MX Park logo preview should remain the user-facing preview in the distributed v016 candidate; if the reproducible source package still carries the legacy preview, patch only the preview TGA after the validated native build without changing track geometry/physics.
