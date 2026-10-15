# C loam with B jump-face grooves

The user prefers C's overall dirt and B's lengthwise lines on jump faces. This
review combines those properties on the same 210 m section and four matched
cameras used for the original trials. The approved sign position is retained.

The combined treatment keeps C's exact 3 m photographic tile, restrained cavity
shading and original scanned fine normal. Flats and tabletop decks retain the
reviewed C material exactly. On sloped jump faces, the route-normal atlas blends
toward the original B/v056 groove atlas and its stronger mask. The increased
face mask also reduces the packed-colour contribution on those faces; it does
not substitute B's smaller-scale photographic tile. The blend follows absolute
grade along the route, fading in between 6% and 19% grade, and is confined to
the reviewed jump envelopes rather than applied to corner banks.

Both takeoff and landing slopes can receive the grooves. C remains the treatment
on level ground and decks. Terrain, race layout and scenery geometry are
unchanged. The close-up still uses C's clod/cavity photograph and 3 m scale.
The image list and flat-preservation checks are in `hybrid_recipe.json`.

No new terrain images or layers are required by this design. Production
integration can reuse C's existing colour tile, 8K normal atlas and upper mask;
the hybrid modifies the contents of those slots. The earlier smaller-colour-atlas
memory plan remains applicable. Native compiler allocation and game RAM/VRAM
remain unmeasured. This review is a source-material experiment and does not
start a native build.

## Placement preview orientation correction

The existing vehicle number/logo bitmaps were pre-flipped in v021/v024 to
compensate for the native importer's orientation. The placement-only software
preview omitted that known compensation and therefore showed the numbers
backward. The preview now applies the documented 1-U compensation for precisely
that legacy artwork. It does not flip the whole scene, move props, or change any
vehicle/sign source texture or UV.

The new sign's four triangles match the same serialized projection convention
used for the repaired v032 entry sign and v033 billboard. Front and back are
shown separately in `Sign_Front_Back_Orientation_Check.jpg`. This checks the
saved sign mapping; the new sign has not yet been tested in MX Bikes. The saved
scenery SHA-256 remains:

`59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604`

The sign remains approximately 2.98 m clear of the van nose. Source evidence and
the preview correction are recorded in `orientation_review.json`.

## Reproduce

Use the existing v056 recovered inputs and v058 C textures:

```bash
python -u TOOLS/v058_hybrid.py
python -u TOOLS/v058_orientation_review.py
python -u TOOLS/v058_hybrid_package.py
```

The placement image can be regenerated with `TOOLS/v058_placement_review.py`.
It uses VTK only to hold decoded mesh data and a software depth-buffer renderer,
so it does not require an X server or GPU context. The optional preview-only
Numba runtime was isolated in `BUILD/v058_cpu` using Numba 0.62.1 and llvmlite
0.45.1; invoke it with that directory on `PYTHONPATH`. It samples the original
FBX diffuse texture bindings and the accepted terrain, with approximate review
lighting. It does not invoke a native track compiler.

The source renderer now rebuilds a corrupt or mismatched ray cache, and writes
new ray caches atomically. Completed hybrid views are checkpointed so a failed
later camera can resume without regenerating checked images.
