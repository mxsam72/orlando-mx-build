# Orlando MX v043 editable update

Baseline: delivered private v042 draft release 408329509, source commit
98d799dd455b968b5b0c5665c9fea123579347cb. The full 1,449,475,471-byte source
checkpoint and its actual native validation are authenticated by SHA-256
before editing. All previous versions remain separate.

The user's v042 screenshots confirm that the pit-facing American flag is
correct, while the track-facing flag has its canton at the free edge away from
the pole. The previous screen-direction check wrongly required a standard
left-canton image from both sides. A real flag has its canton at the hoist;
the reverse side naturally displays the canton on the viewer's right when the
pole is on that side. v043 flips only U values 6 through 11, for the two
track-facing triangles of `front_flag_red`. The six pit-facing UV values,
vertical UVs, geometry, normals, winding, pole, materials and original 2048 x
1024 opaque artwork remain exact. The accepted 30 cm separation is retained.
Independent validation measures the physical image-edge distances to the pole
on all four triangles, rather than assuming screen-left is correct.

An **additional** Sam Ford F-150 King Ranch is parked at native X/Z 470 / 400 m,
heading +X, beside the Qwikchute billboard by the figure-eight course. Its 14
parts come directly from `truck_sam_` in v042, including the repaired King
Ranch, Ford and 4x4 graphics. The original Ford remains in the pits. A rigid
terrain fit uses wheel-contact points, retaining topology, UVs, opaque
materials, face culling and all original textures. No textures are added or
resized. Independent checks cover pavement, wall and obstacle clearance,
protected riding corridors, billboard proximity, ground contact, normals,
material bindings and exact preservation of every original scene object.

All accepted v042 terrain, MX layout/jumps/soils, freestyle double, race/start
data, roads, wall-gap fill, seating, crocodile, Cybertrucks, fences, signs,
memorial, restroom, pit displays and optimized artwork remain exact.

Windows rebuild:

1. `python TOOLS/v043_release_transfer.py source`
2. `python TOOLS/build_v043.py`
3. `python TOOLS/verify_v043_source.py`
4. `python TOOLS/build_windows_v043.py`
5. `python TOOLS/v043_release_transfer.py deliver`

The checkpoint includes complete current editable output, pinned v042 output,
build scripts, official tool inputs, actual baseline validation, and current
native game files. Previous derived caches and native MAP files remain in
their prior private releases. Copied historical reports retain their original
version meaning; the current v043 reports are authoritative for this update.
The release stays an unpublished private draft. The PKZ must remain below
500,000,000 bytes. In-game appearance and riding confirmation require the
user's test; no preview renders are required.
