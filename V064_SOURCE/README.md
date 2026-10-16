# v064 — original B corners, C elsewhere

Use the original v062 B flowing cultivation throughout all 14 mapped corner
arcs, with original v062 C ridden loam on the remaining MX surface: straights,
jump faces, landings, and start lane. The rejected dense v063 method is absent.

The corner intervals come from the authenticated v044 source checkpoint and
are mapped through the retained v054 station mapping to the current route.
Five metre smooth blends just before and after each corner avoid hard joins.
Inside each named arc the existing B texels remain exact. Beyond those blends,
C texels remain exact. Only existing macro normal RGB and packed/wear mask
alpha are combined; no extra texture images or terrain layers are introduced.
Normal specular alpha, mask RGB/nonzero boundaries, photographic colour, fine
normals, shaders, proposed daylight and texture allocation stay unchanged.

The complete v061 heightfield and v060 scenery remain byte-exact, preserving
the speedway wall roller, van/sign, alternating trucks and every other saved
geometry change. The roller's material texels are also preserved.

After restoring v061 and generating v062 sources, run:

```bash
OPENBLAS_NUM_THREADS=1 python TOOLS/v064_hybrid.py
OPENBLAS_NUM_THREADS=1 python TOOLS/v064_review.py
```

Seven matching source cameras show corners, jump faces and straight sections.
Comparison plates place original B left, original C centre, and hybrid right.
These use the real heightfield and material maps with approximate daylight
and filtering. Scenery is omitted; these are not in-game screenshots.
Final native compilation remains on hold for preview approval.
