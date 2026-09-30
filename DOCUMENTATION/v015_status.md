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


## Native build complete

GitHub Actions workflow `Build v015 jump pit grass refinement` completed successfully.

- Workflow run: `36677294186`
- Build source commit: `9f30e988a06553941c48c0c42e9fad9b792fea62`
- Game artifact: `OrlandoMX-v015-game-candidate`
- Game artifact ID: `11080464297`
- Evidence artifact ID: `11080534203`
- Source checkpoint artifact ID: `11079863681`
- PKZ: `OrlandoMX_2026_v015.pkz`
- PKZ bytes: `137612370`
- PKZ SHA-256: `c8772ade97b915da1de4387f773ccc9155a886141f4b226f578725adc2d25c9f`

Source QA:
- 0 new excessive-grade nodes
- route unchanged
- outer terrain delta 0
- layout checks pass
- restroom is 10.0 m from RV02 center and inside the grass patch
- restroom has 3.93 m clearance from the nearest road edge
- RV/restroom grass patch area ~942.83 m², with road masks overriding grass
- release source checks pass

Native stages all succeeded:
- fbx2edf
- terrained_map
- terrained_trh
- tracked_merge

Remaining gate: in-game ride validation only.
