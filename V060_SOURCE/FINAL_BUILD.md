# v060 final build

The user requested tighter grooming spacing, then extended it to every area with the added grooming and authorized final compilation immediately afterward. This supersedes v059's preview-approval hold. The user subsequently authorized continued monitoring through completion; the workflow handles native validation, source/native preservation and gated package delivery.

All 16 perpendicular grooming regions (14 corners, R04, R14 face) use irregular target gaps of 0.18–0.28m, with a 0.3m maximum validated in three dimensions across an 18m corridor. Added lengthwise grooves on the complete R03/R07 faces are also tightened, from 52 to 88 tines. The source checks report the actual physical spacings; those can be smaller on inner curves and cross-slopes.

Only the existing macro normal RGB atlas changes. Colour scans, fine normals, masks, specular alpha, image sizes, texture count and terrain layers stay exact to v059. RGBA8 source allocation remains 1,447,297,024 base-level bytes. Actual game RAM/VRAM and FPS are unmeasured.

The entire terrain grid, jump profiles, route, start path, track edges and scenery are byte-identical to v059. This retains the two smoothed corner banks, moved R11 pair, grounded markers and approved Express/sign/Cybertrucks. It deliberately retains the v059 scenery correction, rather than reverting to the earlier saved v057 EDF.

Four matched close-up comparisons check corner 01, R04, R03 and R14. These are terrain/material source renders with scenery omitted, not game captures. Their camera coordinates and file hashes are recorded in `photo_check_D01.json` through `photo_check_D04.json`.

`v060_inputs.py restore` recovers pinned accepted dependencies and rebuilds v058, v059 and v060 in order. `expected_inputs.json` pins the reviewed final terrain, routes, HMF and all active terrain images. Scenery is anchored to the authenticated saved v057 source archive and descriptor; only the three specified marker records may change. The saved Windows FBX is allowed to have a different whole-file hash from the local preview fixture, and its actual before/after hashes are recorded. HMF and generated dirt shaders use canonical LF text on both Linux and Windows. The final native stage resolves each active image through the same authoritative source resolver as the preview, then verifies all image and shader hashes.

`build-v060.yml` runs on the `rebuild-v060` branch. It preserves checked source, freshly compiles scenery, collision and visual terrain, merges the unchanged centerline, and validates every native height sample, texture payload, scenery probe and package CRC. `v060_transfer.py` publishes the versioned PKZ only after all gates pass. In-game appearance, riding and performance remain for the user to test.
