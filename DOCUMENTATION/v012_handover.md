# Orlando MX v012 — Final Obstacle Correction + Facility/Layout Fix Handover

**Prepared:** 2026-09-29  
**Project:** Orlando MX recreation for MX Bikes  
**Primary objective:** Build v012 from the latest corrected v011 source, replacing incorrect obstacle types, correcting the start-lane merge, and fixing key pit/facility placements.

---

## 1. Starting Point / Version Control

Begin from the **latest corrected v011 source state**, not from older v009 or v010 work.

### Required base

Repository:

`mxsam72/orlando-mx-build`

Current v011 branch:

`rebuild-v011-jumps-facilities`

Use the latest corrected v011 source that includes:

- v011 jump/facility geometry work
- successful v011 native Windows build
- corrected facility material handling
- corrected FBX diffuse-material colors
- corrected facility texture staging for `fbx2edf`
- existing spectator/pit/facility scenery
- existing start-gate / T05 work

### Important version-control rules

1. **Do not overwrite or damage v011.**
2. Create a **new v012 branch/version**.
3. Suggested branch name:

`rebuild-v012-final-obstacles-layout`

4. Preserve all prior stable versions.
5. Checkpoint frequently.
6. Keep the v012 rebuild reproducible from source.

### Output naming

Final package:

`OrlandoMX_2026_v012.pkz`

---

# 2. v011 Context That Must Carry Forward

v011 already introduced major work that should remain unless explicitly superseded below.

### Preserve from v011

- darker / improved dirt baseline inherited from v008b
- spectator fence system
- pit / paddock facility scenery
- RVs / campers / pickups / trailers
- office/check-in building asset
- restroom/bathroom asset
- bleachers and covered spectator structure
- utility poles
- trees / facility vegetation
- pale pit-road treatment
- working v011 source/build pipeline
- successful native PiBoSo build process
- facility-material fix so the new objects no longer rely on an unresolved white fallback material

### v011 material-fix context

The v011 white-object bug was caused by generated facility materials cloning a white baseline FBX material while their texture links were not resolving as intended during native import.

The source-level correction included:

1. encoding intended palette colors directly into the FBX material diffuse/ambient values;
2. preserving diffuse texture connections;
3. staging generated textures in both the build root and `scenery.fbm/`;
4. rebuilding through:

`scenery.fbx -> fbx2edf -> scenery.edf -> terrained MAP/TRH -> PKZ`

Do **not** regress this material fix in v012.

---

# 3. Primary v012 Objective

The goal of v012 is to make the obstacle sequence and track flow much closer to what the user wants.

The highest priorities are:

1. **correct every obstacle R01–R18**
2. **fix the starting-gate merge path**
3. **move key pit/facility objects**
4. preserve the successful v011 visual/material/facility work where appropriate
5. produce a working compiled v012 package

This is a **major geometry correction pass**, not a cosmetic pass.

---

# 4. Reference Sources

Use all available project references together.

## Track / riding references

- latest v011 test ride video
- prior v010/v011 test footage
- original real GoPro lap
- previous section-sync / track-review work

## Facility / spectator / start-area references

Use:

- `IMG_3591`
- `IMG_3592`
- `IMG_3594`
- `IMG_3595`
- `IMG_3597`

Important known observations:

- `IMG_3594` / `IMG_3595` strongly show the spectator fence, front tabletop, and portions of the starting area.
- the other facility videos show pit roads, camper/RV placement, buildings, bathroom, spectator seating, and facility context.

## Existing planning references

Use prior:

- R01–R18 obstacle map
- jump feature appendix
- v011 handover
- v009/v010 section sync
- gate/start-area markup
- track review PDF

Do not assume old obstacle classifications remain correct. The user-provided R01–R18 definitions below are now authoritative.

---

# 5. Facility / Pit / Start-Area Corrections

Apply the following exact changes.

## 5.1 Bathroom relocation

The current bathroom/restroom building is in the wrong place.

### Required change

Move the bathroom so that it is:

**between the campers in the pit area**

It should visually sit within the active camper/paddock cluster instead of appearing isolated or misplaced.

Use the facility reference videos to place it logically relative to:

- camper/RV rows
- pit road
- mature trees
- existing paddock layout

Do not invent survey precision that is not available, but the relational placement must match the user's instruction.

---

## 5.2 Front office / check-in building relocation

The current office/check-in building is also in the wrong place.

### Required change

Move the office/check-in structure:

**to the left of the red truck**

Preserve the existing building asset/material treatment unless a minor adjustment is needed for proper ground contact.

---

## 5.3 Starting-gate merge path

The current start path is wrong because it cuts directly into the corner.

### Required behavior

The start line should:

1. leave the gate area;
2. travel around the outside of the corner area;
3. **loop around rather than cutting directly through the corner**;
4. merge into the racing line **immediately before the right-handed corner**.

The path should feel like a deliberate motocross start chute.

### Do not

- merge directly into the apex;
- cut diagonally through the corner;
- create a collision or terrain ridge at the merge;
- break first-lap checkpoint logic;
- damage start reset behavior.

### Validate

- gate spawn
- 24-rider start
- start lane width
- merge width
- merge terrain
- checkpoint placement
- first-lap timing
- reset behavior

---

# 6. Authoritative v012 Obstacle Definitions

The following user instructions **supersede prior v011 obstacle classifications**.

Do not preserve old obstacle types merely because they already exist.

Distances are user-requested approximate overall feature lengths unless otherwise specified.

---

## R01 — Long Tabletop

### Target

**TABLETOP**

### Required change

Make R01 significantly longer.

Target:

**approximately double the current total length**

The obstacle should read clearly as:

`takeoff -> deck -> landing`

Do not convert it back into a rounded crest.

### Character

- major front tabletop
- clear deck
- sustained face
- distinct landing
- preserve spectator-side readability

---

## R02 — Big Triple

### Target

**TRIPLE**

### Approximate size

**~40 meters**

### Required character

This should be a major obstacle, not a roller.

Build it as a deliberate three-part motocross rhythm/jump feature.

The exact implementation should be rideable, but the visual and riding behavior must clearly read as a **big triple**.

Do not reduce it to:

- one rounded mound
- one tabletop
- small rolling bumps

---

## R03 — Table-Single

### Target

**TABLE-SINGLE**

### Approximate size

**~35 meters total**

### Required character

Large feature.

Interpret the user's intent as a combined table/single-style motocross obstacle rather than a generic roller.

Create:

- a meaningful takeoff
- elevated table-like geometry
- a distinct single/landing relationship
- approximately 35 m overall scale

Document exactly how the 35 m is distributed across the feature.

---

## R04 — Sweeping Corner Only

### Target

**NO JUMP**

R04 should be:

**just a sweeping corner**

Remove the existing jump/crest behavior if it currently rides like a jump.

The corner itself is the feature.

---

## R05 — Low Double Into Corner

### Target

**DOUBLE**

### Approximate size

**~12 meters**

### Character

- low height
- modest lip
- short double
- directly feeds into the corner

This should be a low motocross double, not a huge launch.

Corner approach and landing orientation are critical.

---

## R06 — Corners Only

### Target

**NO JUMP**

R06 should not contain a jump.

This area should consist of:

**corners approaching into R07**

Remove jump-like terrain here unless needed only as minor natural transition.

---

## R07 — Large Ant-Hill Single

### Target

**LARGE SINGLE / ANT-HILL STYLE**

### Important correction

R07 is **NOT a double**.

Remove the current double interpretation.

### Placement

The large ant-hill style single should be positioned:

**where the current double landing is**

### Character

- large rounded dirt mound
- standalone single
- no gap
- no separate landing mound
- visually substantial
- motocross ant-hill style

This is intentionally different from a tabletop or double.

---

## R08 — No Jump

### Target

**NO JUMP**

Remove the current jump/obstacle behavior.

Keep only the terrain needed for normal track flow.

---

## R09 — Big Double

### Target

**BIG DOUBLE**

### Approximate size

**~25 meters**

### Required character

- clearly defined takeoff
- visible/rideable gap
- independent landing mound
- real motocross double geometry

Do not soften it into a tabletop or rounded hill.

---

## R10 — Very Large Tabletop

### Target

**BIG TABLETOP**

### Approximate size

**~50 meters**

This should be one of the largest features on the track.

### Required character

- long progressive face
- clear lip
- substantial deck
- distinct landing
- around 50 m total scale

Do not turn it into a gap double.

---

## R11 — Very Low-Lipped Double

### Target

**DOUBLE**

### Approximate size

**~20 meters**

### Character

Very low lip.

The feature should rely more on speed and distance than height.

Required:

- shallow takeoff
- subtle lip
- visible gap
- independent landing
- ~20 m scale

Avoid supercross-style steepness.

---

## R12 — Four Rolling Singles

### Target

**ROLLING SINGLE SECTION**

### Count

**4 individual rolling singles**

### Spacing

**one every ~5 meters**

Create a rhythm sequence of four distinct rolling singles.

They should remain recognizable as four separate obstacles.

Do not merge them into:

- one long roller
- one tabletop
- one whoop mound

---

## R13 — No Jump

### Target

**NO JUMP AT ALL**

Remove any existing jump geometry.

This section should function only as normal track terrain / transition.

---

## R14 — Very Big Triple

### Target

**VERY LARGE TRIPLE**

### Approximate size

**~35 meters**

This should be a major signature obstacle.

### Required character

- large triple
- clearly defined launch
- substantial distance
- recognizable three-part geometry
- around 35 m

Do not preserve the v011 tabletop interpretation.

---

## R15 — Single

### Target

**SINGLE**

### Instruction

Current R15 is generally fine.

Preserve it unless minor adjustment is needed for blending after surrounding changes.

---

## R16 — Longer Tabletop

### Target

**TABLETOP**

### Important correction

R16 is **NOT a double**.

Remove the double interpretation.

### Length

Make it:

**approximately 5 meters longer than the current feature**

Preserve general placement while converting it into a proper tabletop.

---

## R17 — Eight-Roller Section

### Target

**ROLLER SECTION**

### Count

**8 rollers**

### Spacing

**~5 meters apart**

R17 should no longer be treated as a single jump.

Create a long rhythm section containing:

**8 sequential rollers**

Each roller should remain individually readable.

Spacing target:

~5 m from one roller to the next.

Ensure the entire sequence blends into the incoming/outgoing track.

---

## R18 — Inside-Line Roller Only

### Target

**INSIDE-LINE ROLLER**

### Important correction

R18 is **NOT a jump on the main straight**.

It should only exist as:

**an inside-line roller feeding into the corner**

### Requirements

- locate it on the inside option
- keep the main straight/normal line free of this obstacle
- make it useful as a line-choice feature into the corner
- do not build a full-width obstacle across the track

---

# 7. Summary Table

| Feature | v012 Target |
|---|---|
| R01 | Long tabletop — ~2x current length |
| R02 | Big triple — ~40 m |
| R03 | Big table-single — ~35 m |
| R04 | No jump — sweeping corner |
| R05 | Low double into corner — ~12 m |
| R06 | No jump — corners into R07 |
| R07 | Large ant-hill single at current double landing |
| R08 | No jump |
| R09 | Big double — ~25 m |
| R10 | Big tabletop — ~50 m |
| R11 | Low-lipped double — ~20 m |
| R12 | 4 rolling singles — ~5 m spacing |
| R13 | No jump |
| R14 | Very big triple — ~35 m |
| R15 | Single — preserve current |
| R16 | Tabletop — ~5 m longer than current |
| R17 | 8 rollers — ~5 m spacing |
| R18 | Inside-line-only roller into corner |

---

# 8. Geometry Authoring Rules

## Major jumps

For all doubles, triples, and tabletops, independently control:

- toe position
- face length
- lower-face curvature
- upper-face steepness
- lip position
- lip radius
- lip height
- deck/gap positions
- landing crest
- landing angle
- landing length
- runout
- track width
- side taper

Do not use one generic smooth mound formula.

---

## Tabletop requirements

Every tabletop must have a true deck.

A tabletop should visibly contain:

`face -> lip -> deck -> landing`

Avoid:

`rounded hill -> rounded hilltop -> rounded descent`

---

## Double requirements

Every double must have:

- independent takeoff mound
- actual gap/valley
- independent landing mound

Do not fake doubles with a shallow dip in a long roller.

---

## Triple requirements

Triples must clearly read as triple-type features.

For R02 and R14, document the exact geometry implementation so the user can understand how the requested ~40 m and ~35 m scales were constructed.

---

## Roller requirements

R12 and R17 are rhythm sections.

Do not turn the rollers into large jumps.

Maintain repeatable spacing and smooth entry/exit transitions.

---

# 9. Preserve / Remove Rules

## Preserve

Preserve the successful v011:

- material fix
- dirt/textures
- facility assets
- spectator structures
- fence style
- camper/RV assets
- utility poles
- pit-road surface treatment
- current build toolchain

unless an exact placement correction is required.

## Remove / replace

Replace any v011 jump classification that conflicts with the user-defined v012 list.

Particularly:

- R07 double -> large single
- R16 double -> tabletop
- R17 single -> roller section
- R18 main jump -> inside-line roller
- R14 tabletop -> large triple

---

# 10. Required Facility Placement QA

Before packaging, visually confirm:

### Bathroom
Bathroom is positioned:

**between the campers**

### Office
Office/check-in building is:

**left of the red truck**

### Start lane
Start lane:

- goes around the corner area
- does not cut directly into the corner
- merges immediately before the right-handed corner

Create a new overhead QA image showing these three corrected items.

---

# 11. Required Jump QA

Create an updated overhead map showing:

- R01 through R18
- each feature's new target type
- start/end station for each feature

Also create longitudinal side-profile QA plots for at least:

- R01
- R02
- R03
- R05
- R07
- R09
- R10
- R11
- R12
- R14
- R16
- R17
- R18

For each profile, label:

- takeoff
- lip
- deck / gap / roller sequence
- landing
- approximate total length

---

# 12. Required Machine-Readable v012 Spec

Create:

`V012_SOURCE/v012_geometry_spec.json`

Each obstacle should record at least:

```json
{
  "id": "R09",
  "target_type": "DOUBLE",
  "user_target_length_m": 25,
  "station_start_m": null,
  "station_end_m": null,
  "face_length_m": null,
  "lip_height_m": null,
  "gap_length_m": null,
  "landing_length_m": null,
  "notes": "Big double; user-authoritative target"
}
```

Also create:

- `V012_SOURCE/facilities.json`
- `V012_SOURCE/start_layout.json`

or equivalent clear source files.

---

# 13. Git Checkpoint Strategy

Recommended commits:

1. `v012: branch from corrected v011 material baseline`
2. `v012: rebuild R01-R05 obstacle group`
3. `v012: rebuild R06-R10 obstacle group`
4. `v012: rebuild R11-R14 obstacle group`
5. `v012: rebuild R15-R18 obstacle group`
6. `v012: correct bathroom and office placement`
7. `v012: reroute start lane and right-corner merge`
8. `v012: complete geometry and facility QA`
9. `v012: compile native candidate`
10. `v012: record final PKZ and ride-test checklist`

Do not place the entire rebuild in one commit.

---

# 14. Native Build Requirements

Compile through the existing official PiBoSo workflow.

Required chain:

`source -> terrain.raw -> scenery.fbx -> fbx2edf -> terrained_map -> terrained_trh -> tracked_merge -> PKZ`

Preserve the corrected v011 facility texture/material staging.

Output:

`OrlandoMX_2026_v012.pkz`

Record:

- file size
- SHA-256
- Git commit used for build
- GitHub Actions run ID
- native tool results

---

# 15. Required Ride-Test Checklist

The v012 ride test should explicitly verify:

## Start / facility
- gate start works
- start lane loops around correctly
- merge happens before the right-hand corner
- no collision/hump at merge
- first-lap timing works
- reset behavior works

## Obstacles
- R01 feels like long tabletop
- R02 clearly feels like a big triple
- R03 reads as table-single
- R04 has no jump
- R05 is low double into corner
- R06 has no jump
- R07 is a large ant-hill single, not double
- R08 has no jump
- R09 is a big double
- R10 is a very large tabletop
- R11 is low-lipped double
- R12 contains four rolling singles
- R13 has no jump
- R14 is a very large triple
- R15 remains good
- R16 is tabletop, not double
- R17 contains eight rollers
- R18 only affects inside line into corner

## Scenery / facility
- bathroom between campers
- office left of red truck
- facility colors/materials still work
- no white-object regression

---

# 16. Definition of Done

v012 is only complete when:

1. all R01–R18 obstacle definitions match the user-provided list;
2. the bathroom and office are relocated correctly;
3. the start lane no longer cuts directly into the corner;
4. v011 material fixes remain intact;
5. geometry QA passes;
6. native compilation succeeds;
7. a separate `OrlandoMX_2026_v012.pkz` is produced;
8. a ride-test checklist is included;
9. earlier versions remain untouched.

---

# 17. Final Instruction to Astra

Do **not** reinterpret these obstacle definitions using previous v011 assumptions.

The user's R01–R18 list in this document is the new authoritative design target.

The objective of v012 is to replace the remaining incorrect obstacle interpretations with the exact requested mixture of:

- tabletops
- doubles
- triples
- singles
- roller sections
- corner-only areas
- line-choice terrain

while preserving the improved Orlando MX facility visuals and stable build pipeline from v011.

Begin from the corrected v011 source, create a separate v012 version, checkpoint frequently, and carry the work through native compilation and a testable PKZ.
