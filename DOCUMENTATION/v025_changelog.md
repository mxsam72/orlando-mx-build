# Orlando MX v025 — visual test candidate

This version upgrades the dirt and immediate track surroundings while preserving the v024 track and physical behavior at source. Its quality target comes from the supplied Moriarty screenshots; its palette and riding marks come from the supplied Orlando photographs.

## Changes

- Added original fine sandy-loam textures for base soil, prepared dirt, churned dirt and lighter loose sand, with dry/wet pairs.
- Added a non-repeating 4096 × 4096 wear atlas following the exact v024 route, corner rut trajectories, jump faces and landings. It includes primary/secondary compacted lines, interrupted tire marks, braking wear, exit churn and larger soil-color variation.
- Added granular normal maps and route-aligned wear normals with restrained specular alpha, using documented native SHD controls.
- Updated only the visual prepared/worked/grass masks. Grass margins have more irregular dirt intrusion; the existing grass detail has a modest green adjustment.
- Increased native shadow-map and shadow-volume supersampling from 1 to 2. Sun direction and environment settings stay the same.
- Added deterministic material generation, a versioned material specification, asset provenance, source-preservation checks and an isolated native build workflow.

## Preserved

v024 remains on its original branch and commit. All 593 baseline repository files are unchanged. The heightmap, route, jump profiles, berm geometry, physical masks, THT, scenery, vehicle/bike graphics, start, pits, signs, logo, cameras, race data and reset boundaries are protected. Racing/start runtime work remains deferred as in v024.

The source heightmap SHA-256 is `4befe79d6820865f4aba34649a5b54ed22472e7a3c1e7f8d3d56f53f3e340d91` for both versions.

## Performance design

Fine tiles are 1024² at roughly four metres per repeat. The non-repeating wear diffuse and normal maps are 4096², the wear mask is 4096², and the other visual masks are 2048². No additional vegetation objects or collisions are introduced. The conservative terrain-input estimate is 488.25 MiB as RGBA8, or 651 MiB with full mip chains. It includes the staged physical mask images and excludes scenery and driver overhead. Actual GPU allocation, FPS, loading time and stutter still need measurement in MX Bikes. The PKZ is 121,459,887 bytes.

## Verified build

Official native compilation and centerline merge passed. All 16 new terrain bitmap payloads and 40 vehicle/bike/sign texture payloads were verified in the compiled MAP. The downloaded PKZ matches the native build checksum.

The compiled TRH (physics/centerline), scenery EDF, timing/RDF, environment, cameras, logo, map image, marshals and reset boundaries are byte-identical to v024. Only the visual MAP and version identity change in the track package.

PKZ SHA-256: `54ce4074d62e0da0766561b1514c759f4afedf42876db6a1f8980553ecce4ecc`.

## Comparison files and testing

The included R10, T09, R07 and R17 comparisons are labeled **source material previews, NOT IN-GAME**. They use the same heightmap and camera. Objects, engine shadow behavior and native normal/specular shading are omitted, so they do not prove final game appearance.

Actual MX Bikes loading, a complete visual lap, stationary rider/elevated inspection, runtime deformation appearance and performance checks remain pending. v025 is a test candidate until those checks pass; it is not declared fully visually accepted.

## Source

Repository: https://github.com/mxsam72/orlando-mx-build/tree/rebuild-v025

Material implementation commit: `0d46a11113789c7ccef18f83431335af227577ef`.

Validated build commit: `2a0fe57d5ef86217c232fb9cf315e15c44e757ae`.

Native workflow run: https://github.com/mxsam72/orlando-mx-build/actions/runs/37337242369 .
