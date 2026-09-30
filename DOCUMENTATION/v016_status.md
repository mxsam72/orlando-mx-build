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


## Native build complete

GitHub Actions workflow `Build v016 jump water pit refinement` completed successfully.

- Workflow run: `36680836162`
- Build source commit: `fcc51f24ff24d7c43f07f5f6b33ec6ced48a4d6c`
- Game artifact: `OrlandoMX-v016-game-candidate`
- Game artifact ID: `11082545331`
- Evidence artifact ID: `11081929021`
- Source-checkpoint artifact ID: `11082425420`
- Native PKZ: `OrlandoMX_2026_v016.pkz`
- Native PKZ bytes: `137643626`
- Native PKZ SHA-256: `6ebf9f8070b7fc8cbd88ceef74183d2ef761240bdd7ee720ae90bc0d48b01049`

Source QA passed:
- geometry checks pass
- R07 encoded as one ant-hill crest, ~32.79 m authored length
- R10 encoded 75 m tabletop with ~26.43 m deck
- R11 remains a distinct 20 m double
- R18 remains main-line excluded and inside-line only
- `drainage_water_2` removed; `drainage_water_1` preserved
- bathroom is ~7.28 m from red pickup_02, left of canopy_01, inside the new grass patch
- road-edge clearance ~4.95 m
- combined authored grass-patch area ~1604.2 m² with road override
- release source checks pass

Native stages succeeded:
- fbx2edf
- terrained_map
- terrained_trh
- tracked_merge

### Distributed preview-patched candidate

To preserve the Orlando MX Park logo preview requested in v015, the user-facing distributed v016 candidate replaces only:
`orlandomx_2026_v016/orlandomx_2026_v016.tga`

No MAP/TRH/RDF/race/scenery/physics bytes are changed by that preview-only patch.

- Distributed PKZ SHA-256: `33fe6e7bd32cca1325c82360132bfe4660066ab7f261c9a593fe1c6ce65bac3c`

Remaining gate: in-game v016 ride validation only.
