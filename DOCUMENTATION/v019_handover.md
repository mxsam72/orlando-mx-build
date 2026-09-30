# ORLANDO MX BIKES — v019 HANDOVER
## Add real user/friend trucks to the pit area

Continue the existing Orlando MX MX Bikes track project from the completed and validated **v018** build.

This is a continuation of the existing project. Do NOT start a new track, rebuild the layout, or regress earlier work.

Repository:
mxsam72/orlando-mx-build

Validated v018 source branch:
rebuild-v018

Validated v018 source commit:
5738c81931f6547044fa29f0cf323b4642f22055

The v018 GitHub Actions build completed successfully, including:
- source validation
- terrain generation
- scenery generation
- EDF compilation
- MAP compilation
- TRH compilation
- PKZ packaging

Create **v019 as a completely separate new version**.

New branch:
rebuild-v019

Do NOT overwrite, rename, delete, or damage v018.

---

# PRIMARY v019 OBJECTIVE

Add photo-derived 3D models of my actual trucks and my friends' actual trucks into the Orlando MX pit area.

I will provide:
- photos of each truck
- multiple angles where available
- photos/videos showing the pit area
- reference images showing approximately where the vehicles should be located

These vehicles should make the track feel much more like our actual riding days at Orlando MX / Bithlo.

The trucks should look like identifiable representations of the real vehicles in the supplied photos, rather than generic pickup-truck placeholders.

---

# VERY IMPORTANT — PRESERVE v018

Do NOT alter any existing track geometry unless explicitly necessary for a tiny scenery-clearance correction.

Preserve the completed v018 work, especially:

- R07 compact ant-hill geometry
- R10 larger / earlier / steeper tabletop
- R11 steeper low-lip double
- current start layout
- current racing line
- current terrain
- current track width
- current berms
- current spectator fence
- current bathroom location and orientation
- bathroom doors facing the spectator fence
- connected pit gravel-road network
- expanded pit-area grass
- sign-in office
- pit structures
- bleachers
- trees
- existing vehicles unless specifically being replaced
- Bithlo sticker-covered stop-sign landmark
- current race checkpoints
- starting-grid functionality
- current physics/material masks

v019 should primarily be a **pit-scenery / vehicle-detail update**.

---

# ORLANDO MX MENU ARTWORK — DO NOT REGRESS THIS

Previous builds accidentally reverted the track-selection preview to old terrain artwork.

DO NOT allow that to happen again.

The MX Bikes track-selection image must continue to use the proper:

**ORLANDO MX PARK logo**

matching the good v015/v017 presentation.

Do NOT use the old v007 terrain/jump preview.

The track-selection artwork and course-map artwork are separate files.

For v019:

orlandomx_2026_v019/orlandomx_2026_v019.tga
= Orlando MX Park logo preview

orlandomx_2026_v019/orlandomx_2026_v019_map.tga
= actual course map

Explicitly validate this before packaging the PKZ.

---

# TRUCK MODELING REQUIREMENTS

For EACH supplied truck, inspect all available photographs before modeling.

Create a separate identifiable 3D vehicle asset for each truck.

Match visible characteristics as closely as practical, including where visible:

- pickup make/model/body generation
- cab configuration
- bed length
- body proportions
- body color
- grille shape
- headlight shape
- bumper design
- hood profile
- fender shape
- mirrors
- wheels
- tire diameter
- wheel offset
- ride height
- lift or leveling kit appearance
- running boards
- bed cover
- toolbox
- camper shell
- racks
- hitch
- tow mirrors
- decals
- stickers
- window tint
- license plate placement
- scratches / wear if visually significant
- aftermarket accessories

Do not make all trucks from the same generic pickup mesh.

They should visibly differ from one another.

---

# PHOTO-DERIVED MODELING RULE

Use the supplied photographs as the authoritative visual source.

If the vehicle's exact model/year can be confidently identified from the photos, use real-world dimensions as an approximate scale reference.

If exact model/year is uncertain:

DO NOT hallucinate an exact year or trim.

Instead document it as something such as:

"Photo-derived full-size crew-cab pickup; exact year uncertain."

Use conservative dimensional estimates.

The goal is visual fidelity in-game, not falsely claiming survey-grade dimensions.

---

# LEVEL OF DETAIL

These vehicles are scenery assets, not drivable vehicles.

Optimize them for MX Bikes scenery performance.

They should look convincing from:

- normal riding distance
- pit-road distance
- roughly 2–30 meters

Prioritize recognizable silhouettes and visible details rather than excessive hidden geometry.

Use reasonable polygon counts.

Avoid unnecessarily huge texture files.

Where appropriate use:

- separate body mesh
- windows
- tires
- wheels
- grille
- lights
- bumpers
- mirrors
- bed / tailgate details

Avoid creating a single crude rectangular vehicle block.

---

# TEXTURES

Create proper textures/materials for the vehicles.

Do not rely only on FBX diffuse-color fallback.

Where useful create dedicated textures for:

- paint
- windows
- tires
- wheels
- lights
- grille
- chrome
- plastics
- decals

Keep textures deterministic and stored in the repository.

Do not reference temporary local paths.

Do not use inaccessible external textures at runtime.

---

# PIT PLACEMENT

Study the supplied pit-area reference photos/videos before deciding placement.

The current pit layout is already established in v018.

Do NOT randomly scatter trucks around the pits.

Use the supplied references to approximate:

- which road they are parked beside
- orientation
- spacing
- distance from bathroom
- distance from office
- distance from canopies
- distance from spectator fence
- grass vs gravel parking
- realistic vehicle spacing

The vehicles should look naturally parked as they would on an actual riding day.

Avoid perfect grid placement unless the reference shows it.

Small heading variations are desirable where appropriate.

---

# EXISTING GENERIC VEHICLES

Review the generic trucks/RVs/trailers currently in the v018 pit scenery.

Where a supplied real truck is intended to occupy roughly the same position as an existing generic pickup:

REPLACE the generic pickup rather than stacking two vehicles in the same location.

Do not create intersecting vehicles.

Do not create duplicate trucks occupying the same parking space.

Preserve unrelated vehicles.

---

# COLLISION / SPAWN SAFETY

The vehicles must NOT interfere with:

- rider spawn points
- pit spawn points
- start grid
- race checkpoints
- track surface
- pit road driving lines
- spectator fence openings
- bathroom access
- office access

Use the existing scenery-clearance QA system.

For each new truck calculate/document approximate clearance from:

- main track edge
- start route
- pit spawn positions
- nearby buildings
- nearby vehicles

Do not simply disable clearance checks to force a model into the map.

Fix the placement instead.

---

# TERRAIN / SURFACE RULE

Truck placement must NOT unintentionally alter the terrain.

No major terrain changes should be necessary.

If a truck is sitting on grass:
- keep grass underneath/around it

If it is sitting on gravel:
- keep gravel road/pit material underneath it

Do not create new large dirt patches merely to accommodate vehicles.

---

# BITHLO PIT CHARACTER

The pit area should continue moving toward the real-world Bithlo/Orlando MX appearance.

Preserve the v018 signature elements:

- sticker-covered Bithlo stop sign
- grass/dirt/gravel mixture
- sign-in office
- bathroom
- spectator fence
- canopies
- trailers
- parked vehicles
- informal Florida motocross pit appearance

The added trucks should strengthen this visual identity.

---

# ASSET NAMING

Use clear asset names such as:

truck_sam
truck_friend_01
truck_friend_02
truck_friend_03

If the owner/name is clearly provided with the images, descriptive names may be used.

Example:

sam_f150
shane_silverado
friend_ram

Do NOT embed private information such as addresses, phone numbers, VIN numbers, or full license-plate numbers into source filenames or metadata.

If a plate is visible in a photo, it does not need to be reproduced accurately.

---

# v019 VERSION ISOLATION

All new generated outputs must use v019 naming.

Examples:

V019_SOURCE/
V019_OUTPUT/

orlandomx_2026_v019

TOOLS/build_v019.py
TOOLS/v019_common.py
TOOLS/build_windows_v019.py

DOCUMENTATION/v019_changes.md
DOCUMENTATION/v019_vehicle_validation.json
DOCUMENTATION/v019_source_checkpoint.json

.github/workflows/build-v019.yml

Do not package files internally as v018.

---

# SOURCE CONTROL PROTOCOL

1. Verify the latest validated v018 source commit.
2. Create:
   rebuild-v019
3. Branch from validated v018.
4. Make all v019 work only on rebuild-v019.
5. Commit work in logical checkpoints.
6. Do not rewrite v018 history.
7. Do not force-push over v018.
8. Keep enough documentation to reproduce the v019 build.

Suggested checkpoint commits:

- v019: initialize from validated v018
- v019: add photo-derived truck assets
- v019: place trucks in Bithlo pit area
- v019: validate pit scenery clearances
- v019: finalize native build workflow

---

# REQUIRED DOCUMENTATION

Create:

DOCUMENTATION/v019_changes.md

Include a table such as:

| Asset | Photo-derived vehicle | Approx dimensions | Position X/Z | Heading | Surface | Confidence |
|---|---|---:|---|---:|---|---|
| truck_sam | description | ... | ... | ... | grass | high |
| truck_friend_01 | description | ... | ... | ... | gravel | medium |

Also document:

- which supplied image(s) were used for each truck
- what details were directly visible
- what details were estimated
- any uncertainty about model/year
- any generic vehicles replaced
- final clearance values
- final asset/material counts

---

# VISUAL QA

Before native packaging, generate review images showing the ACTUAL authored scenery meshes.

Create at minimum:

1. Entire pit overview
2. Truck cluster overview
3. Individual view of each new truck
4. Bathroom / truck area
5. Office / stop-sign / truck area
6. Top-down pit layout showing vehicle positions
7. Vehicle placement relative to gravel roads and grass

These should come from the actual generated meshes and placements.

Do not use concept art as QA evidence.

---

# AUTOMATED VALIDATION

Create a dedicated:

DOCUMENTATION/v019_vehicle_validation.json

Validate at minimum:

- all expected truck assets exist
- each truck has nonzero geometry
- vehicle meshes contain finite coordinates
- all referenced materials exist
- all referenced textures exist
- no vehicle overlaps pit spawn points
- no vehicle overlaps the main track
- no vehicle overlaps the starting route
- no severe vehicle/building intersections
- no duplicated vehicle placements
- gravel road remains connected
- bathroom remains correctly oriented
- Bithlo stop sign remains present
- Orlando MX menu logo requirement remains preserved
- terrain remains valid
- race layout remains valid

Do NOT mark:
"in_game_riding": true

unless it has actually been tested in MX Bikes.

---

# NATIVE BUILD PROTOCOL

Once source QA passes:

Run the same validated native-build process used for v018.

Compile fresh:

- EDF
- MAP
- TRH
- race files as required
- centerline integration
- PKZ

Do not merely rename the v018 PKZ.

The package must genuinely be:

OrlandoMX_2026_v019.pkz

Run the complete GitHub Actions workflow and require success.

---

# FINAL ARTIFACTS

Produce:

OrlandoMX_2026_v019.pkz

OrlandoMX_2026_v019.pkz.sha256

OrlandoMX_v019_Validation.json

Install_v019.txt

v019 source checkpoint artifact

v019 build-evidence artifact

---

# FINAL COMPLETION CRITERIA

DO NOT tell me v019 is complete until ALL of these are true:

- v019 source branch exists
- vehicle assets are modeled
- vehicles are placed in the pit
- visual QA images have been reviewed
- scenery clearance checks pass
- geometry QA passes
- pit-road connectivity still passes
- race/start QA passes
- Orlando MX Park track-selection logo is correct
- native EDF compilation passes
- native MAP compilation passes
- native TRH compilation passes
- PKZ packaging passes
- GitHub Actions run reports SUCCESS
- final PKZ artifact exists
- SHA-256 is generated and verified

Actual MX Bikes ride testing is a separate final user-validation step.

---

# IMPORTANT WORKING BEHAVIOR

Do the work rather than merely describing what should be done.

Inspect the supplied truck and pit reference images first.

Before making major placement assumptions, correlate all available views.

If a truck detail cannot be determined from the photos, use a conservative approximation and DOCUMENT the uncertainty instead of inventing a factual detail.

Keep frequent GitHub checkpoints so work survives compute/session limits.

If a build fails:
- inspect the actual error
- correct it
- rerun validation
- do not bypass validation merely to obtain a PKZ

The final goal is a playable **Orlando MX 2026 v019** that retains everything good about v018 while adding recognizable versions of our real trucks to the Bithlo pit area.