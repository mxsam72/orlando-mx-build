# Orlando MX v031 - scanned soil and sign correction

The tested v030 entry sign is upright but horizontally mirrored. Flip U on all
four native triangles and check the UV projection from each native polygon's
viewing direction. V, vertices, normals, materials, textures, connections and
all other scenery properties are preserved. Both faces are readable in the
source projection. This source check is not an in-game capture.

Replace the repeated dirt recipe with twelve independent photographed soil
materials from pinned CC0 Poly Haven scan sets: compact earth, prepared dirt,
worked clods, sand, jump-face soil, packed dirt, pits dirt, damp mud and four
grooming materials. Use the matching scanned OpenGL normals, height and
roughness data, physically scaled tiling, coherent muted soil color, restrained
specular alpha and separate wet responses. The native engine's supported
normal/specular shader is used; this does not add physical micro-displacement.
A thirteenth scan adds low-strength broad variation on track dirt. Its mask
is zero on every existing grass sample and the protected main pits area.

Preserve tested v030 terrain, routes, jumps, race boundaries, physical masks,
every existing visual mask, grass textures, pits grass, the bare starting
section and the existing 50% course-grass reduction. Preserve custom scenery
textures, menu art and all other FBX properties. Compile a separate v031.

Sources: https://polyhaven.com/license and each asset page recorded in
V031_SOURCE/scan_catalog.json. Native shader reference:
https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide

Source and native verification do not replace an MX Bikes load, appearance,
ride or performance test. Those tests require the game and remain pending.
