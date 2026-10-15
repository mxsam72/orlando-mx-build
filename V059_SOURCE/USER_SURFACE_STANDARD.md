# User's perpendicular grooming standard

For this and future updates, “orthogonal to current” means an **additional pass at 90 degrees to the existing visible directional grooves**, with **irregular distances between adjacent marks, never more than 0.5 metres**. Preserve the existing pass beneath it. Follow the local track direction through curves; do not substitute a fixed diagonal world-axis pattern. This rule was stated explicitly on 2026-10-15.

## This review's requested edits

- Photo 04 / corner 01: add the perpendicular pass.
- Photo 07 / R03 takeoff: more lengthwise marks across the complete face.
- Photos 08–09 / corner 03: soften the abrupt bank drop, and add the perpendicular pass.
- Photo 10 / straight R04: add the perpendicular pass.
- All corners with one existing directional pass: add the perpendicular pass. All 14 current corners meet that criterion.
- Photo 15 / R07 takeoff: more lengthwise marks across the complete face.
- Photo 21 / corner 09: soften the abrupt bank drop. It also receives the all-corners perpendicular pass.
- Photo 22: translate the second and third visible mounds as a pair. The pair is R11, after the unchanged R11 entry single. Move the second mound to the third's former station, retaining the 9.9m crest spacing. The R11 pair moves 9.9m forward; the entry single and R12 roller crests remain fixed.
- Photo 25 / R14 takeoff: add perpendicular marks across the face.

Keep the C photographic loam and original fine normals, track boundaries, physical material layers, start route, asphalt courses, and approved van/sign/Cybertruck work. No added texture slots or layers. Render the revised track for user review **before final/native compilation**. The user has not approved compilation of these changes.

## Evidence

Nine local reference images were inspected: image(20261015-053648).png, image(20261015-053903).png, image(20261015-054152).png, image(20261015-054522).png, image(20261015-054622).png, image(20261015-054822).png, image(20261015-055035).png, image(20261015-055129).png, image(20261015-055322).png. These are the user's marked/cropped v058 source renders, not new game captures.

`v059_geometry.py` changes real terrain only inside the two bank regions and R11's old/new footprint. `v059_surface.py` adds normal relief into the existing 8K atlas and adjusts the existing wear-mask alpha. It checks line spacing in 3D on 37 lines across an 18m corridor, allowing for curved outer lines and terrain slopes. `v059_review.py` reuses the exact saved v058 world cameras for before/after comparisons.

`v059_scenery.py` seats the three affected boundary markers on the new ground. These are vertical shifts only; every other FBX object, including the approved vehicles, sign, road courses, materials and textures, stays exact. Because the marker vertices change, a future approved build must compile the updated scenery; it must not blindly reuse the saved v057 EDF. No native compilation has been started.

To reproduce from the generated v058 baseline, run `v059_geometry.py`, `v059_surface.py`, then `v059_scenery.py`. Run `v059_review.py` for the 38 full-course views and `v059_details.py` for the four close-ups. `v059_review.py --package` rebuilds the course gallery and nine comparisons; `v059_details.py --append` adds the close-ups to the checked ZIP. `v059_check.py` validates the complete source and review package. Code and generated validation records are checkpointed on `dirt-review-v059`.
