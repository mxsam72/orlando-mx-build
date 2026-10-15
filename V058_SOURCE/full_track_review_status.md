# v058 full-course C+B review

The user selected the C photographic loam with B's jump-face grooves. The method is now authored across the entire accepted v056 dirt footprint, including the starting path. All 14 corners, the corrected R03 landing, every heightmap sample and the racing layout are retained exactly. The saved, approved v057 Chevy Express, cardboard sign and alternating Cybertruck colours are copied unchanged.

The source photograph is byte-identical to the approved C comparison. Original scanned fine normals are retained. The original route-normal atlas is blended into C cultivation on sloped jump faces. All 15 jump groups are tested, including R18's actual inside-line offset rather than its intentionally flat main line. No diagonal tread stamps are authored. Visual and physical mask footprints remain exact.

Existing colour slots now use the 4K C scan at 3m repeats; the existing macro-normal slot remains 8K at one repeat. No terrain layers or image slots were added. The complete active image inventory saves 201,326,592 bytes (192 MiB) at RGBA8 base level, approximately 256 MiB with a full mip chain. These are source allocation estimates; game memory, frame rate and native appearance remain unmeasured. PiBoSo's MXB Track Creation Guide confirms that bump repeat zero inherits HMF repeats and positive values set independent normal repeats. Explicit repeats avoid ambiguity in the new loose, packed and macro shaders.

## Review gate

The latest user instruction is to render photos around the whole course and wait for approval **before final compilation**. Do not start a native build in response to the earlier approval of the small C+B trial. No v058 native workflow has been launched.

`TOOLS/v058_full_review.py` reads the actual production HMF, shaders, masks, photo mipmaps and accepted terrain. The review is complete: 38 numbered perspective views, a camera-location map, five contact sheets and a ZIP of full-resolution photos. These are terrain/material source previews, not MX Bikes captures. Scenery is omitted so the soil can be inspected. Approved scenery remains saved and unchanged.

The renderer checkpoints each completed photo by camera, input hashes and image hash. It uses top-down over-composition to avoid sampling fully occluded layers; this affects preview time only. It preserves per-pixel perspective mip selection and directional texture footprints. The accepted trial controls are not overwritten.

`TOOLS/v058_full_review_check.py` passed. It verifies visible dirt from all 14 corners and all 15 jump groups in their dedicated views, exact approved terrain and scenery, production shader repeats, every individual photo hash and the complete ZIP. The R02 production view differs from the approved hybrid preview by only 0.124 mean RGB levels on the 0–255 scale; 99.4% of pixels differ by fewer than four levels in every channel. Small boundary feather, 8-bit mask and JPEG differences are expected.

The photo images were rendered from source checkpoint `e72d68cef0acb8640e20871ddf90438e13c268ea`. Subsequent review changes make ray-cache writes safe between processes, verify large scenery copies and ZIPs before atomic publication, separate two overlapping map labels, and remove empty contact-sheet space. These changes do not alter the photo material or geometry. The completed archive digest and full camera evidence are recorded in `full_track_review.json` and `full_track_review_check.json`.

## Reproduce locally

Recover tested v056 inputs and the pinned saved v057 scenery with `TOOLS/v058_inputs.py` when needed. Run retained-input copying before surface authorship, because it also restores the baseline HMF.

```bash
python TOOLS/v058_retained.py
python TOOLS/v058_surface.py
OPENBLAS_NUM_THREADS=2 python TOOLS/v058_full_review.py
```

If generated textures already exist, `python TOOLS/v058_surface.py --validate-existing` validates them without regenerating. Individual camera IDs can be passed to the review script. A complete invocation reuses only matching, hash-checked photos, then rebuilds the review package.

Source allocation and physical preservation evidence are in `full_track_material_validation.json` and the retained-output validation reports. The final photo manifest records every camera and bound image. Native compilation, native map checks and an in-game visual check remain subsequent steps after the user's photo approval.
