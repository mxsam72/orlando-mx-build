# Orlando MX v019 — four owner pit pairs

Base: validated v018 commit `5738c81931f6547044fa29f0cf323b4642f22055`. Branch `rebuild-v019`. This is a scenery-only continuation; track terrain, start, race layout, pit roads, buildings and unrelated vehicles are preserved.

## References and interpretation

| Pair | Supplied references | Visible details represented | Estimates / limitations |
|---|---|---|---|
| Jordan | Jordan Cyber Truck 1(1).jpg; Jordan Bike 1(1).jpg | Stainless wedge body, sloping tinted glass, black angular arches/rims and tonneau; white/black Husqvarna 450, Rockstar-style gold-star graphics, 759 plates, silver rims | Unprovided model year, exact dimensions and hidden mechanical details estimated |
| Premier Power | Premier Power Truck 1–3(1).jpg; Premier Power Truck Video.MOV; Premier Power Bike 1(1).jpg | Squared Chevrolet crew cab, white cab, large red power symbol, blue lightning bed wrap, dark wheels/steps; blue Yamaha 450F, blue rims, gold fork, Premier graphics | Exact year/trim uncertain; wrap is a clean recreation, not a photographic scan; tiny sponsors/portrait simplified; bike number read as 277 from the photo |
| Sam | Sam Truck 1.JPG; Sam Truck 2.jpg; Sam Truck 3(1).JPG; Sam Truck with Bike 1(1).jpg; Sam Dirtbike 1(1).jpg | User-identified F-150 King Ranch, dark upper/tan lower body, chrome grille/mirrors/steps, crew cab and open bed; blue Yamaha 250F with 373 plates | Exact year and dimensions estimated; bike placed beside the truck as requested |
| Shane | Shane Van 2–5(1).jpg; shane bike 1(1).jpg; shane bike 2.jpg | Black Chevrolet cargo van, solid cargo panels, cab glazing, short nose, steel wheels, twin rear doors and vertical lamps; blue Yamaha 450F with 927 plates, gold fork and local dealer graphics | Wheelbase/body length conservatively estimated; paint wear approximated; hidden details simplified |

No private plate numbers, VINs, addresses or phone numbers are reproduced. Vehicle dimensions are photo-derived estimates, not survey measurements. These are static scenery assets.

## Placement

The supplied marked `image(7).png` identifies the grass strip right of the flag/frontage red pickup, toward the covered spectator stand. Four naturally staggered pairs face generally toward the pit road. Each bike stands beside its own vehicle. Existing generic vehicles occupy other positions and remain in place; none is duplicated or replaced.

Exact positions, headings, actual mesh dimensions, material counts and triangle counts are generated in `V019_OUTPUT/vehicle_catalog.json`. Footprint clearances are generated in `DOCUMENTATION/v019_vehicle_validation.json`. The 0.15 m route-sampling grid is supplemented with exact convex footprint/segment distance checks for roads, buildings, other vehicles and fence.

## Rendering and materials

Actual source meshes are used for every QA view. Body panels, wheels, arches, glass, lights, mirrors, open pickup beds and bike components are distinct geometry. Shared small material textures plus dedicated graphics have explicit per-polygon UVs. Hash-pinned PNGs are stored in `V019_SOURCE/vehicle_textures_packed.json` and deterministically restored before export. Runtime textures are relative-path TGA files and embedded FBX media; no temporary/external asset path is required.

The corrected v018 Orlando MX Park menu logo is preserved byte-for-byte from the previously delivered corrected package, independently of the course map. The logo payload and digest are versioned in source.

## Validation status

Work in progress. Native compilation and final review are not yet claimed. In-game riding has not been performed. Final source and native evidence will be recorded before delivery.
