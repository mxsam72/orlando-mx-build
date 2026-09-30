# v015 status

Branch: `rebuild-v015-jump-pit-grass-refinement`.

v015 branches from successful v014 and applies the September 30 v014 ride-test changes to R03, R07, R09, R10, R16, R17, R18 plus the RV/restroom paddock.

Source geometry: `V015_SOURCE/v015_geometry_spec.json`.
Pit/facility source: `V015_SOURCE/pit_facilities.json`.
Workflow: `.github/workflows/build-v015.yml`.

Important interpretation:
- “R07 25% smaller” is implemented as 75% of v014 longitudinal/vertical ant-hill size, not a change to the 10 m riding width.
- “R09 less steep” is implemented as 10% lower takeoff/landing crest height while shortening its gap and moving the feature 5 m earlier.
- “R03 landing less big” is implemented by taking the full 3 m reduction out of its landing.
- R14 remains the v014 55 m triple.

Native compilation and in-game validation remain pending until the latest workflow completes.
