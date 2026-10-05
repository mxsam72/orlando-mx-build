# Orlando MX v026 in-game review -> v026b hotfix

## Evidence reviewed

- `test v026 1 lap.mp4`: 139.1 s, reviewed at 5-second intervals (28 regular samples).
- `test v026 tree and track marker in bad place.mp4`: 39.4 s, reviewed at 1-second intervals (40 samples) because the obstruction sequence is short and localized.

This is an in-game visual review. It does not infer exact world coordinates from screen pixels; scenery cleanup is validated against the authored v026 route and actual FBX object anchors during the build.

## What v026 improved

1. **The excessive orange/ochre cast is substantially corrected.** The course now reads as a neutral brown/taupe Florida dirt baseline instead of the strongly orange v025 surface.
2. **Close-range dirt grain is more consistent.** The old smooth/ribbon-like coarse wear overlay is no longer dominating the riding surface.
3. **Jump faces retain fine texture instead of becoming broad low-detail color bands.**
4. **The R10/T09 geometry revision is visibly present**, and the new route is the cause of the scenery conflicts addressed below.

## Remaining visual improvement opportunities

These are documented for a later visual pass rather than folded into the v026b obstruction hotfix.

### 1. More macro value separation
The track is still too monochromatic from rider height. Base soil, prepared dirt, packed line, jump faces and corner wear often sit very close in value. The next visual pass should increase *subtle* separation rather than saturation:
- lighter dry shoulder / exposed sand,
- medium prepared dirt,
- darker compacted racing line,
- darker/churned corner apex and exit zones,
- slightly lighter scraped jump shoulders.

### 2. Racing-line definition
The packed line is present but is frequently too faint to read at speed. It should be more legible through value and roughness variation while remaining irregular and avoiding a continuous painted stripe.

### 3. Berm-specific wear
Corners still look too much like the same granular material applied over different geometry. Add clearer compacted grooves at the common line, churned clods outside the groove, and localized braking/exit wear.

### 4. Jump-face and landing directionality
The fine granular texture is an improvement, but takeoffs and landings need stronger longitudinal riding/grooming cues so the slope and repeated wheel path read more naturally.

### 5. Track-edge transitions
Several sections show abrupt dirt/grass or dirt/green-mask transitions. Around ~45 s in the full-lap video a large green area reads more like a material patch than natural ground. Future work should soften these edges with patchy sand/grass breakup.

### 6. Repetition / uniform grain
The new fine texture solves the coarse v025 transition problem, but some long straights now have a very uniform high-frequency grain. A low-amplitude macro layer would help break repetition without reintroducing broad painted overlays.

### 7. Scenery quality is now a stronger contrast
Because the dirt improved, the very stylized low-poly tree canopy becomes more noticeable. Tree-model replacement is a separate scenery-quality project and is not part of v026b.

## v026b user-reported blockers

### Tree in the relocated T09/R11 corridor
In the short clip the moved route approaches a tree around **19-24 s**; the canopy/trunk occupies the rideable corridor. The same obstruction is visible again near the end of the full lap (~130 s).

**Fix:** remove only tree objects whose actual FBX ground anchor falls inside the localized v026 changed sector and within a conservative clearance of the new track edge.

### Track marker inside the riding surface
A pale rectangular track marker is clearly inside the riding surface around **28-30 s** of the short clip.

**Fix:** remove only `SOFTCPLAS_marker_*` objects in the same localized sector that are inside or immediately adjacent to the new track edge.

## v026b scope

v026b is intentionally a **surgical scenery hotfix**:
- keep v026 terrain geometry byte-identical,
- keep v026 race/reset data unchanged,
- keep v026 dirt materials and masks unchanged,
- keep pits, start, vehicles, facilities and unrelated scenery unchanged,
- remove only route-intruding tree/marker scenery in the localized R10 -> T09 -> R11 changed corridor,
- regenerate native scenery coordinate probes after removal,
- compile a new separate `OrlandoMX_2026_v026b.pkz`.

The larger material improvements above should be evaluated for v027 after v026b confirms the revised route is clear and rideable.
