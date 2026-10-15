# Orlando dirt: three v058 source-material trials

These are matched previews for choosing a dirt treatment. No full native build
has been started, and no method is approved yet. The canceled v057 dirt is not
the baseline: all four sets use v056 materials and terrain as their reference.

## What was making the photograph disappear?

The original photographic colour and fine normal maps are 4096 pixels across a
2 m tile. Their nominal texel spacing is 0.49 mm. The upper colour/normal atlas
is 8192 pixels across the entire 600 m terrain: 73.24 mm per texel, or 150 times
coarser in each direction. On the chosen section's centreline, this upper layer
blends over approximately 75–90% of the fine photographic colour and normal.
The median is 80.34%. This is an opacity measurement, not missing image area.

That coarse colour atlas was also authored using downsampled photographic
sources. It retains useful broad grooves and shading but cannot retain the
original scan's small clods. More image resolution alone would be a costly way
to solve this; separating tiled photographic colour from route-scale grooves
is more promising.

There was a separate preview problem. The old source renderer first baked a
large world rectangle to a small image and then projected the camera onto it.
That blurred foreground detail. The new renderer samples texture mip pyramids
at each terrain hit, with trilinear filtering and up to eight anisotropic taps.
This correction is applied equally to v056 and all three candidates.

The original source includes more channels than the current dry shader uses.
These studies use diffuse colour, normal and specular alpha. They do not add
physical clod displacement, a new PBR shader, or native-engine lighting.
The old photographic shaders contain `repetitions = 0`; these previews use the
same inherited-repeat assumption as the earlier source renderer. Its native
meaning is unverified. Any selected production integration should use explicit,
matching repeat values and be checked in MX Bikes.

## Same test section, three different changes

The test is the same approximately 210 m section, from route station 0 to 210 m:
the finish tabletop, connecting turn and flat, and triple approach. Changes
feather over 7 m at the ends and retain the existing photographic footprint.
All sampled material differences outside the section are asserted to be zero.

| Method | Changes | Purpose |
| --- | --- | --- |
| A — Original scan, 25% overlay | Reduce only the existing upper mask; preserve original photograph, fine normals and v056 macro atlas. Maximum alpha is 63/255, approximately 25%. | Isolate the overlay-coverage change without the canceled v057 normal reconstruction. |
| B — Photo colour + v056 grooves | Replace the coarse upper colour with the original 2 m tiled photograph. Retain v056's exact blended normal field and upper mask strength. | Recover fine colour while keeping the established groove depth. |
| C — Loamy scan + broken cultivation | Enlarge the original clods to a 3 m tile, add restrained normal-derived cavity shading, retain scanned fine normals, reduce the packed layer, and introduce broken lengthwise tine furrows. Upper normal blend is capped at 55%. | Test a loamier surface without diagonal vehicle tread stamps. |

C's cavity shading is a local concavity estimate from the scanned normal, not
a downloaded scanned AO map. It darkens cavities by at most 18% before restoring
the original mean colour. The new macro furrows follow local route direction;
their virtual relief is encoded only in a normal map. The physical terrain is
unchanged. There are no continuous paired skid-steer bands in the new treatment.

## Four matched views per method

1. Finish tabletop at riding height.
2. Forward view of the connecting flat/turn.
3. Triple approach and jump face.
4. Low close-up of soil detail near the track edge.

Every view uses identical camera, terrain, lighting and sampling for v056,
A, B and C. Each method sheet has v056 on the left and the candidate on the
right in four rows. The four all-method grids arrange v056 / A above B / C.
The ZIP includes all 16 individual 1600 × 1000 renders, the comparison sheets,
this explanation, the experiment recipe and the render manifest.

These are source-material studies, not MX Bikes screenshots. Scenery is omitted
from every dirt view so it cannot change the comparison. Native shader sampling,
lighting and appearance still require verification after a method is chosen.

## Approved work preserved

The van, alternating Cybertruck colours and readable cardboard sign are retained
from source commit `8903065aca3301fd0eed0522738f370eb69743ca`. Their scenery file
is byte-for-byte unchanged:

`59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604`

The accepted v056 terrain is also byte-for-byte unchanged, including the landing:

`ab99df42094ef29015f117babeffe555e814fc7f86cf836c60625b760868289f`

## Memory plan and limits

A reuses the current 14 layers and images, adding no image allocation. B and C
are designed for full-track integration by replacing the existing 8K macro
colour slot with a 4K tiled photographic colour slot while retaining the 8K
route normal atlas. Colour and normal repeats can be independent. Layer 3 must
be integrated at the matching colour repeat as well as the top pass.

For illustration, if both colour slots allocate RGBA8, replacing 8192² with
4096² saves 192 MiB before mipmaps. This is a size calculation, not a measured
reduction in game RAM or VRAM. The native compiled representation, compression,
deduplication and total peak memory have not been tested. These scoped CPU
previews use local sampler overrides; a separate native region-only package
would need an additional masked pass. A selected full-track method can reuse
the existing layer/image slots instead.

## Reproduce the review

Use the v057 source checkpoint and recovered v056 inputs. Do not run the canceled
v057 dirt authoring or a native compile. With NumPy, Pillow and SciPy available:

```bash
python -u TOOLS/v058_trials.py
python -u TOOLS/v058_render.py
```

The trial author validates the preserved hashes, unchanged macro texels outside
the region and matte specular alpha. The renderer checks identical cameras and
zero material changes outside the section. B's normal samples must be bit-exact
to v056 in all views. Generated products remain outside the tracked source tree.

The photographic source provenance is recorded in
`V045_SOURCE/visual_spec.json` and `V046_OUTPUT/v046_asset_provenance.json`.
Shader/track format references:

- https://docs.piboso.com/wiki/index.php?title=Track_Creation_Guide
- https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide

User selection is pending. A full version will start only after that selection.
