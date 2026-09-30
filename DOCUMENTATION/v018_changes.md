# Orlando MX v018 — obstacle and Bithlo pit refinement

Base: completed v017, including the preserved Orlando MX Park menu artwork requirement.

## User reference reviewed
- `Bithlo bathroom.MOV`
- `bithlo sign 1.jpg`
- `bithlo sign 2.jpg`
- `bithlo sign 3.jpg`
- Prior pit-layout reference videos carried forward from v017.

## Track changes

### R07
- Keep the ant-hill crest at route station **s552**.
- Shorten the footprint from **32.79 m to 29.0 m**.
- Use **14.5 m face + 14.5 m landing**.
- Set crest height to **5.45 m**.
- Reduce shoulder mass and support width so it reads as a compact mound, not a tabletop.
- The resulting authored face is modestly steeper than v017.

### R10
- Make the tabletop larger.
- Start the takeoff **2 m earlier**, at **s739.2**.
- Increase total authored length from **72 m to 74 m**.
- Increase crest height **3.30 m -> 3.75 m**.
- Shorten takeoff face to **17.5 m**, increasing takeoff angle.
- Expand deck to **28.0 m**.
- Preserve the established 28.5 m landing.

### R11
- Preserve the **20 m** low-lip double footprint and position.
- Increase takeoff and landing crest heights another **5%** versus v017.

## Pit changes

- Restroom remains at **(274,112)**, but rotates to **heading 0°** so the modeled double-door/front wall faces +Z toward the spectator fence.
- Expand grass across the lower and upper parking/paddock areas.
- Preserve authored gravel as the higher-priority surface wherever roads cross grass.
- Re-author the pit road system as one connected network:
  - main frontage road
  - lower pit road
  - west connector
  - mid connector
  - east connector
  - office apron
- Add the signature **Bithlo sticker-covered stop-sign / number-board assembly** at **(307,143)** near the sign-in office. The mesh includes the tall pole, octagonal stop plate, lower rectangular board, upper street-sign plank, and dense deterministic motocross-style sticker plaques based on the supplied photos.

## QA intent

The v018 source build explicitly checks:
- R07 is shorter and steeper than v017 while remaining one ant-hill crest.
- R10 begins earlier, is larger, and has a steeper takeoff than v017.
- R11 is steeper than v017.
- Restroom door/front vector points toward the spectator fence.
- Pit road mask is a single connected network.
- Grass coverage is materially expanded.
- Sticker-stop mesh exists near the office with multiple sticker materials.
- Native compilation and actual in-game riding remain separate validation gates.
