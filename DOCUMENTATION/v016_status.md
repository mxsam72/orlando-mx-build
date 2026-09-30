# v016 status

Branch: `rebuild-v016-jump-water-pit-refinement`.

v016 branches from completed v015 and changes:
- R07 ant-hill scale and adjacent drainage-water removal
- R10 start/steepness/length
- R11 steepness
- R18 width
- bathroom placement
- new front grass paddock around bathroom/red truck/canopy

Source geometry: `V016_SOURCE/v016_geometry_spec.json`.
Pit/facility source: `V016_SOURCE/pit_facilities.json`.
Workflow: `.github/workflows/build-v016.yml`.

Interpretation notes:
- R07 “10% smaller” = 90% of v015 height, longitudinal footprint and side support; 10 m riding width retained.
- R10 “5% steeper” = exactly +5% takeoff height/length grade at unchanged height.
- R11 “5% steeper” = +5% takeoff and landing crest heights at unchanged horizontal dimensions.
- R18 “3 m wider” = riding width 7.1 -> 10.1 m.
- Bathroom is now tied relationally to red pickup_02 and canopy_01, not RV02.

Native compilation and in-game validation are pending until the final workflow run succeeds.
