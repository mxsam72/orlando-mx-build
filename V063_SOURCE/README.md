# v063 — overlapping full-width B grooming

The user's marked screenshot identifies v062 B camera 04 and requests adjacent
marks, extra marks in the gaps, and work through the middle so the surface
looks repeatedly travelled over in both directions.

This variant starts from v062 B, preserving its photographic RGB, fine
normals, wear mask, shaders, 14 HMF layers, texture allocation and proposed
daylight. Only the existing macro normal RGB atlas and packed-soil blend alpha
change. There are no native collision or terrain edits.

Primary passes are spaced 0.25–0.31 m apart with overlapping 0.165–0.205 m
half-widths. A second shallow imprint lies at every midpoint, and a primary
pass is explicitly placed through the centre. The main route and wide start
are covered. Marks remain aligned with the route on bends and jump faces.
Alternating small displaced rims suggest opposite travelling directions.

Coverage validation samples the entire lateral interval -19 to +19 m at
different station phases, including the literal centre. The envelope is a
visual imprint coverage measure, not a tyre or MX Bikes simulation.

The whole v061 RAW heightfield and scenery remain exact, including the new
wall-entry roller. Its macro normal texels remain exact too. No final native
compilation or new PKZ is started by this branch.

From the repository root, after restoring/authored v061 and v062 inputs:

```bash
OPENBLAS_NUM_THREADS=1 python TOOLS/v063_dense.py
OPENBLAS_NUM_THREADS=1 python TOOLS/v063_review.py
```

The same seven v062 cameras are used for matching before/after plates. The
previous B photos are verified by their recorded SHA-256 before inclusion.
Source renders use actual material files and heightfields with approximate
lighting/filtering and omit scenery. In-game appearance remains unverified.
