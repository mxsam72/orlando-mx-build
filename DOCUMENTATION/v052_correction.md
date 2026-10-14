# v052 grass correction and straight grooming

The v051 video supplied as 20261014-0746-43.4376020.mp4 shows a broad carpet of grass between track sections. v051 expanded layer5's mask over the verges in addition to increasing blades from 4,546 to 18,000. The correction restores the ground mask and blade footprint to pre-v051 coverage, retaining the corrected green photo.

Grass uses v050's seed (500050), root counts (5 near / 3 distant), 22 attempts per historic scrub patch, jitter, height ranges and original blade width. No broad-field anchor sampling remains. The native build must verify exactly 4,546 clumps and the v050 triangle/batch budgets.

The v051 route-aligned furrows receive 30% more relief on straights, while clod relief receives 25% less. Normal-atlas blend increases by at most 0.08. A 3 m smoothing of route curvature fades the effect into corners. The v051 photo colour, compaction and fully curved section fields must remain exact.

The existing R03/R10/R17 layer experiments retain their exact authored masks. Terrain, collision, approved trees and all non-grass scenery remain exact. All renders are source previews. Native compilation and the user's next ride test are the validation sequence.

The screenshot image(20261014-075414).png shows almost-white needle clusters. Direct inspection of the pinned tree diffuse atlases finds 66 opaque white texels in over 1.1 million opaque pine texels and none in woodland. Both original foliage shaders enable specular shininess 8 without a mapped intensity. The likely cause is specular glare, not a white texture region. Both leaf shaders now receive the same explicit zero-alpha specular bitmap, using PiBoSo's documented specular-map format. Diffuse, alpha cutouts, tree shapes and positions remain exact. Verify the matte map in the compiled EDF before the slower TerrainEd step. In-game confirmation remains necessary.

Native specular record inspection (38536643719) confirmed that PiBoSo stores this specular-only map as a raw-deflate compressed 8-bit alpha plane, not a RGBA normal map. Both 16x16 native records decode to exactly 256 zero bytes and match the source alpha MD5. A dedicated validator checks every decoded byte in bounded named EDF and MAP records. Tests use the actual exporter packet and corruption / nonzero-alpha controls. The successful scenery export and reviewed source are restored by pinned archive SHA256, rather than reauthored or re-exported. The final terrain export and complete package verification remain required.
