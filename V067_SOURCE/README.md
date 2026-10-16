# v067 late-morning material review

Status: **source previews only; full native compilation requires user approval**.

Baseline: `rebuild-v066`, commit `8bb4d91722f4a70135b47f3c4dee9e038eb436e7`.
The successful v066 build is https://github.com/mxsam72/orlando-mx-build/actions/runs/38870858456.

The candidate retains the approved B-corner/C-course treatment, including C
start dirt and the cleared start strip. Terrain, wall-entry roller, route,
scenery, vehicles, memorial, crocodile, race/reset source and every material
mask remain unchanged. No terrain layer or image allocation is added.

Six existing material maps are refined. Three photographic soil colors gain
controlled local aggregate contrast and less obvious broad tile mottling, with
each original mean color channel retained within one 8-bit level. Loose soil
normal detail is slightly softened to avoid harsh speckle; compacted soil
relief is clarified. The unique 8K course normal gains 25% slope response and
a small, low-pass, photo-derived clod field within the existing dirt mask.
The native normal-map specular alpha remains exactly matte alpha 2.

The sun changes from v066's warm 28-degree southwest key to a 45-degree
southeast key, with neutral daylight, readable blue-sky fill and reduced haze.
This is an approximately 11 a.m. visual target, not an exact solar calculation
for a specified date. Runtime AMB and TerrainEd lighting directions are
generated from the same specification and verified equal. Existing shadow
map scale, supersampling, terrain casting and weather assets are retained.

## Reproduce the review

1. Install Python dependencies from the existing project (numpy, scipy,
   pillow, matplotlib), and use Blender 4.5.3 LTS for the offline renderer.
2. Run `python TOOLS/v066_lighting.py restore` to retrieve and hash-check the
   pinned self-contained baseline. This restores source only.
3. Run `python TOOLS/v067_surface.py`.
4. Run `python TOOLS/v067_prepare_previews.py`.
5. Run `blender -b --factory-startup -t 8 --python TOOLS/v067_render_previews.py`.
   Add `-- --draft` for smaller review images, or `-- --shots 02,03,07`.

The preparation copies actual FBX polygons, UVs, source textures, terrain
samples and scene placements. Cycles' lighting/shading is an offline source
preview, not an MX Bikes screenshot or proof of identical engine appearance.
No separate painted concept artwork, depth-of-field hiding, invented props or
geometry is used. Candidate AMB and MAP parameter files are ready for a later
approved native build. No native v067 build workflow is enabled in this branch.

Before a future full build, use the recorded v067 input hashes and a new v067
native staging/validation entry point. Do not run the v066 build unchanged:
its validation intentionally requires exact v066 material hashes.
