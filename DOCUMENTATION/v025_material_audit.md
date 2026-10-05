# v024 audit and v025 terrain implementation

Baseline: `d70efa2d1da5cec4ed93182a4efb762028b991b6`, `rebuild-v024`.
Read-only source audit: Actions run `37331348224`, successful.

## Current v024 system

The native terrain is a 2049 × 2049 unsigned 16-bit little-endian heightmap on a 600 × 600 m domain, with an 18 m vertical scale. HMF determines appearance; THT determines physical surfaces and deformation materials. Both use the same heightmap and scenery. Separate `visual_racing`, `visual_worked` and `visual_grass` masks already decouple the visible track from its physical `racing` and `grass` masks.

| Layer | Texture resolution | Repetitions | Nominal tile width | Visual thickness |
|---|---:|---:|---:|---:|
| Basemap | 2048² | 1 | 600 m | omitted |
| Soil, dry/wet | 2048² | 96 | 6.25 m | 0.15 m |
| Prepared, dry/wet | 2048² | 118 | 5.08 m | 0.09 m |
| Sand, dry/wet | 1024² | 155 | 3.87 m | 0.05 m |
| Grass | 2048² | 82 | 7.32 m | 0.03 m |
| Worked, dry/wet | 2048² | 124 | 4.84 m | 0.015 m |
| Pit gravel, appended during staging | 256² | 95 | 6.32 m | omitted |

Soil, prepared and worked have mean RGB values of approximately (105,84,73), (107,87,78) and (93,73,63). They share closely related photographic patterns. This is a limited distinction between material states; they are already subdued brown rather than saturated orange. The available inspection copies reveal repeated recognizable clods, and the source masks emphasize lane coverage more than distinct section wear. Repetition from actual rider height remains untested.

SHD files use a `bump` normal map, `repetitions = 0` to match the diffuse tile, and specular shininess 10. Specular strength is carried by the normal alpha channel. There is no PBR roughness/metalness workflow in this implementation. Native TGA/BMP power-of-two formats and these shader controls are documented by PiBoSo: https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide .

THT uses surface classes off/pit/start and material classes compact soil, soil, soft soil, sand and grass. Its material thicknesses and all physical masks stay exact in v025. The source audit's raw height, scene, route, jump, race and centerline hashes are recorded separately. v024 race starts remain deferred.

Grass comes from a tiled ground texture plus mask, while trees and other vegetation belong to the existing FBX scene. v025 preserves every object and distribution. HMF contains no new procedural 3D grass density block. Native compilation already enables object shadows, terrain self-shadowing and shadow maps. v025 retains light direction and environment settings while increasing both native shadow supersampling settings from 1 to 2. This raises bake quality rather than object density. Source software previews cannot reproduce these engine shadows.

Existing edge treatment uses alpha masks between grass, sand, prepared and worked material. The old release pass reduces the worked mask to 45% to avoid painted twin grooves. Physical corner ruts follow distinct authored paths; those paths are used for v025 appearance rather than carved again.

## New v025 material system

An original soil image provides fine grain detail. Deterministic periodic-plus-smooth processing removes edge discontinuities and produces related sandy base soil, prepared dirt, churned dirt and pale sand tiles. Dry/wet pairs share stable coordinates, and normal maps use low alpha specularity. The source image, generation prompt, provenance, seeds and specification are retained in versioned source.

The 4096² world wear atlas does not repeat. It follows the exact v024 route, each corner's entry/apex/exit rut trajectory, jump toes/lips and landing stations. It combines broad soil-color patches, primary/secondary compacted paths, localized braking and exit churn, broken longitudinal tire marks and loose shoulders. Corner widths and line spread vary. Normal detail is visual only and adds no terrain/collision displacement. The atlas has approximately 14.65 cm per texel; fine sand grains therefore belong to the tiled textures, not the atlas.

Visual prepared/worked/grass mask siblings improve lane coverage, corner activity and irregular grass margins. The original physical masks are never replaced. A modest green adjustment retains the existing grass's detail while giving disturbed Florida ground more separation from the dirt.

The atlas is an additional native visual layer with no new physical layer. All six inherited visual thickness values remain unchanged. Its behavior during runtime deformation must still be checked in the game; exact physical inputs do not prove identical appearance after deformation.

## Performance and intentional exclusions

Fine dirt tiles are 1024², at roughly 3.7–4.4 m per tile, giving approximately 3.6–4.3 mm per source texel. Grass is 1024². The full-domain diffuse wear and normal atlas are 4096², within the documented texture dimensions; the wear mask is 4096² and other visual masks are 2048². This allocates resolution to route-specific detail rather than enlarging every texture. The native build records a conservative RGBA8 input-memory estimate with an optional full mip-chain factor. This is not a measured GPU allocation or FPS test.

No jumps, berm heights, corners, centerline, start, pits, vehicles, bikes, signs, menu logo, timing, reset boundaries, sky, cameras or vegetation objects are redesigned. No additional rocks or visible collision obstacles are introduced. No Moriarty assets are copied. No undocumented shader features, true displacement, realtime reflections or PBR properties are invented.

## Validation boundaries

Source safeguards require the exact v024 terrain, scene, start and RDF hashes, exact copied physics masks, unchanged THT and resolved native texture references. Native compilation must pass EDF/MAP/TRH/centerline stages, archive checks and decoded-pixel texture checks. The new branch remains separate from v024.

Matched source previews are labeled **NOT IN-GAME**. They show common heightfield/albedo lighting with objects and engine-specific shader/shadow behavior omitted. Actual MX Bikes load testing, rider/elevated visual inspection, a complete lap, runtime deformation appearance, loading/stutter and FPS/VRAM comparison remain pending until performed in MX Bikes. These limitations prevent claiming full visual acceptance from compilation or software previews alone.
