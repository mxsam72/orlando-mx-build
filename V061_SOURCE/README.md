# v061 wall roller — preview attempt 1

Request: a low, broad takeoff outside the south speedway wall, aligned with the
existing big double. Land on the original asphalt. Review the renders before
authorizing native compilation.

The accepted baseline is published v060, source commit
`a5b490fd19a7679444509a1de5ea32fd636aece7`. `TOOLS/v061_inputs.py` pins the
v060 source ZIP and older immutable material dependencies by SHA-256. It never
uses older terrain or scenery in place of v060.

`roller.json` defines a C2 continuous, broad, shallow entry roller. Its maximum
added height is 1.90 m, maximum approach angle about 9.1 degrees, riding crest
width 9 m and total rounded-shoulder footprint 15 m. The profile starts at Z220
and returns to the unchanged ground before the wall at Z249.24. Axis X535,
travel towards +Z. No landing ramp is added.

Only the new footprint's height samples and four existing material images are
edited. The photographed soil section mask and macro wear mask extend onto the
roller, the grass physics mask clears underneath it, and the existing route
normal atlas receives lengthwise cultivation. Image sizes, texture slots,
14 HMF layers and base RGBA8 texture allocation are unchanged. The full v060
FBX, road, wall, grandstands, vehicles, sign, big double, main course, start and
route files are retained exactly.

Reproduce locally, from the repository root:

```bash
python TOOLS/v061_inputs.py
OPENBLAS_NUM_THREADS=1 python TOOLS/v061_roller.py
OPENBLAS_NUM_THREADS=1 python TOOLS/v061_review.py
```

Python dependencies used: NumPy, SciPy, Pillow, Shapely, Matplotlib and Numba.
The review uses the actual saved FBX meshes/embedded diffuse textures and the
actual heightfield/HMF texture stack, rendered in software with perspective,
depth testing, material mips and approximate lighting. Camera coordinates are
native XZY with vertical last, preserving the game's orientation.

`geometry_validation.json` records the source checks and simplified clearance
estimates across the riding width at 30–50 mph. It models point-contact
ballistics, not MX Bikes suspension, tyres or rider input. In-game clearance
and ride quality require a riding test after approval and compilation.

**Native final compilation has not been started. No new PKZ is published.**
