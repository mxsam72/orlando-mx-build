# Orlando MX v042 editable update

Baseline: actual delivered v041 checkpoint from private draft release 408279561,
commit f52483021b07ab918b45ce35bef8b082be3c1417. SHA256 authentication of the full
checkpoint and actual native validation precedes authoring. v041 remains separate.

The American flag `front_flag_red` had negative horizontal screen-U on both faces
when viewed using MX Bikes' native X/Z/Y camera orientation. Only its horizontal UV
array is corrected once with U = 1 - U. The image pixels, vertical UVs, source
vertices, mesh normals, winding, model/material/texture records, pole and existing
30 cm opaque face separation remain exact. Earlier v040 validation checked winding
and separation but omitted this camera-facing horizontal orientation test. Both
corrected faces now have positive screen-U and screen-V. No Speed World or Qwikchute
UV operation is repeated.

Three **additional** Cybertrucks continue the ordered colors after v041's existing
blue, purple and green: **pink, orange, yellow**. The accepted Jordan Cybertruck's
eleven source parts, UVs, topology and original non-paint materials are reused.
New 256 px opaque paint textures preserve the existing optimization. Each truck is
parked at a distinct pit grass location, fitted to terrain using wheel contact
points and a rigid rotation, and audited for clearance from gravel roads, low
existing assets and all race/practice/connector corridors.

| Truck | Color | Native X/Z metres | Heading |
|---|---|---|---|
| 04 | Pink | 305 / 103 | +X (0 degrees) |
| 05 | Orange | 295 / 127 | +Z (90 degrees) |
| 06 | Yellow | 353 / 125 | -Z (-90 degrees) |

Every original scene object/connection is retained, with only the named flag UV
array changed; no original geometry is removed. All original texture files and
the entire heightfield, masks, freestyle double, race/start data, road markings,
wall-gap infill, stadium seating, crocodile, pit displays, prior trucks, memorial,
restroom and corrected signs are preserved byte for byte.

Rebuild sequence on Windows:

1. Restore authenticated baseline: `python TOOLS/v042_release_transfer.py source`.
2. Author separate source: `python TOOLS/build_v042.py`.
3. Independent source audit: `python TOOLS/verify_v042_source.py`.
4. Official compilation and native verification: `python TOOLS/build_windows_v042.py`.
5. Preserve private draft assets: `python TOOLS/v042_release_transfer.py deliver`.

The first/last step uses the existing workflow's GitHub repository/token variables.
The current editable output, pinned v041 editable baseline, original photographic
crocodile PNG, scripts, official tool/build inputs, baseline validation and complete
v042 native files are included in the checkpoint. Historical V039/V040 derived
output caches and the old v041 native MAP are not v042 rebuild inputs and remain in
their original private releases. Historical reports inside copied outputs keep
their original version meaning; current v042 reports describe this update.

Internal checks do not establish in-game appearance. User load, flag orientation,
vehicle placement, flicker, riding and multiplayer checks remain pending.
