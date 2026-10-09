# Orlando MX v040 authoring checkpoint

Authoritative baseline: private v039 release 407858209, source commit
`d3b4ff10bc91a3b14ba7bcec92750faba796661d`. Its 843,301,025-byte checkpoint
has SHA-256 `f46e9424f70239f3caec1a0531ee4f994d773db23e985faad89889f685f2a172`.
The actual v039 native validation is included under BUILD.

The accepted MX course, colors, soils, race data, fences and four pit displays
are retained. The oval's original road geometry, markings, walls, surface and
red/black Cybertruck grass parking are retained. Both Qwikchute signs are
exactly the user-approved v039 meshes/materials. Do not reapply v039's UV flip.

v040 repairs remove the memorial's nearly coplanar full backing box, separate
its original artwork from supports by at least 23 cm, replace layered flag
geometry with opaque faces 30 cm apart, cut away wall/door backings and ribs
behind bathroom doors, and remove 1,050 inward/duplicate decal triangles.
Repaired decals move 4.5 cm outward. Opaque pit models use FBX exterior-face
culling. Original vehicle/sign UVs and texture files are retained.

The freestyle double points along native game +Z at X=535 m, from the
right/south grass island to the left/north island in image(10).png. Launch lip
Z=320.5 m, rise 8.5 m; landing crest Z=364.5 m, rise 7.8 m. Lip-to-crest
distance is 44 m. Actual heightfield and dirt/grass masks contain the mounds;
these are physical terrain, not floating display-only objects. Edits stay in
the two grass holes with a 0.75 m boundary guard.

Speed World entrance anchor is X=469 m, Z=340 m. Supports straddle the asphalt
access road. The image and upper structure rise 1 m for 3.98 m image headroom.
The already-corrected UVs remain exact on both faces.

For a standalone rebuild on Windows with Python 3.12, install
requirements-v009.txt and shapely==2.1.2, then run:

```
python TOOLS/build_v040.py
python TOOLS/verify_v040_source.py
python TOOLS/build_windows_v040.py
```

The checkpoint includes V039_OUTPUT, V040_OUTPUT, both version sources,
editable scenery FBX, terrain RAW, texture/mask/shader inputs, native build
templates, race/menu files, tools, and hash-pinned compiler download metadata.
Legacy reports inside V040_OUTPUT are historical reference. The authoritative
current reports are source_validation.json and the v040_*_validation.json
files. The FBX is authoritative for repaired meshes, rather than old mesh
manifests inherited from prior versions.

The existing Windows Actions workflow restores and authenticates v039 before
editing, builds v040, independently validates preservation/scope/winding,
compiles native MAP/TRH, verifies geometry/texture signatures, enforces the
499,999,999-byte package ceiling, then creates an unpublished private draft.
No game render or riding verification is claimed. The user tests flickering,
both sign faces, jump rideability, and placement in MX Bikes.
