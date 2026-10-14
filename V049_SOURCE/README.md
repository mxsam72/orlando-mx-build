# v049 matte accepted-colour dirt, finish through triple

The v048 ride clip shows broad moving glare on the finish face and a warmer,
different-coloured patch. Its added 2K clod normal was RGB, implicitly supplying
specular alpha 255, whereas every accepted v045/v046 dirt normal uses alpha 2.
The clod colour and macro palette offsets also changed the soil tone.

Keep every accepted v046 albedo, photographic micro colour/normal tile and
shader byte-identical. Reuse the original 14-layer HMF and 4 m cosmetic depths.
Remove v048 layers 14/15, their masks and clod tile. Change only the existing
macro normal atlas and wear mask from the finish tabletop through the connector,
all three R02 triple crests and its exit, ending at station 190 m. Preserve the
entire accepted macro normal specular channel at 2/255. No new textures, layers,
masks, resolutions or per-section atlas allocations: later extensions edit the
same fixed texture allocation instead of multiplying large maps.

Use the accepted jump-profile gradients to distinguish ascending faces, flat
crests/deck and descending landings, including the intermediate triple faces.
Retain wheel-path alignment with the unchanged accepted colour atlas. The new
detail is virtual normal relief; the delivered v047 terrain/collision, geometry,
trees (252 A / 45 B), race/reset files, lighting and deformation are exact.

Reconstruct and hash-check actual v048 source for comparisons. Source renders
must sample normal-map specular alpha and include a glancing highlight stress
view; they are approximate authoring renders, not game screenshots. Mipmap
normal RGB and specular alpha independently, never premultiply specular data.

Verify every altered pixel is within scope, the exact accepted albedos/shaders/
specular channel/depths, native terrain/object bitmap digests, all 2266 scenery
probes, unchanged collision/race/lighting and the final 13-entry ZIP CRC. Require
at least 10% reduction from v048 and no more than 5% growth from v047 before
publication. Preserve source and compiled native checkpoints before extended
checks. In-game colour/glare, deformation persistence and FPS require user tests.
