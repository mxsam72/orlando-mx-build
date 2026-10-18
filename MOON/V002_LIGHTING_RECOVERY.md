# Moon v002: localized shadow recovery

Run [39121779597](https://github.com/mxsam72/orlando-mx-build/actions/runs/39121779597)
compiled the complete graphics without baked shadows in **56.8 seconds** and
passed every existing native height, coordinate, material and package check.
The diagnostic PKZ is 75,371,649 bytes, SHA-256
`d0f38fc0cc7b9a3ca789b3c50af84b5bcf7bd2dfb106b394e66bce35c30559a1`.
The subsequent shadow bake used scale 0.2, supersampling 1 and terrain casting,
but exceeded its 5,400-second limit. It consumed roughly one CPU core, had
plenty of disk space and wrote no MAP before termination. This isolates baked
shadow generation as the expensive stage; the exact internal algorithm is opaque.

## Change to shadow receivers

The scenery EDF spans -11,920 to +11,920 metres on both horizontal axes.
All sixteen distant massif patches were named `SHAD_massif_patch_*`, forcing
shadow receiving across a 23.84 km scene. This is a likely contributor to the
cost; the next native run tests it rather than treating the cause as proven.

The derived FBX changes those prefixes to ordinary `VIEW_` names. A structured
FBX 7400 node reader targets only Geometry/Model name properties under Objects.
Exactly 32 strings change, affecting 128 bytes. Reversing only those edits must
reproduce the entire original FBX byte for byte. Geometry, connections, normals,
UVs, transforms, materials and embedded textures are consequently unchanged.
The original FBX remains intact. Derived FBX SHA-256:
`cd951a4702ab9d74e1010d42ec4145ae2e163fd26fc46076185f18a532aa5dd1`.

The official converter then produces a new scenery EDF. Native coordinate
probes and receiver-name checks must pass before its checkpoint is uploaded.
Nearby measured terrain and illustrative clasts retain their `SHAD_` names.
The graphics compile retains terrain self-shadowing, uses scale 0.3 with
supersampling 1, and has a 20-minute process limit. Distant terrain remains
visible and receives directional sun shading, but no longer receives baked
shadows. That is a deliberate lighting compromise requiring an in-game check.
The scenery conversion has a separate 45-minute process limit; successful
conversion is checkpointed before the graphics job starts.

The receiver naming follows the official
[Track Creation Guide](https://docs.piboso.com/wiki/index.php?title=Track_Creation_Guide).
The quick rough-shadow settings (0.3 / 1) are given by administrator Snappe in
the [official forum](https://forum.mx-bikes.com/index.php?topic=1949.0).
These values do not guarantee a successful or visually acceptable bake.

## Independent diagnostic and reuse

The successful no-shadow PKZ is published as a separate, explicitly named
diagnostic prerelease. That job has no lighting dependencies. The final
shadowed publisher still refuses diagnostic-only or unshadowed reports.
Both packages use internal ID `taurus_littrow_mx_v002`; install only one.

Sky and collision/route outputs are imported from run 39121779597, compiler
commit `6e4f8fae94e913ae29b452c73fa456c38e09a3a1`. The no-shadow diagnostic
uses the same pinned provenance. Restoring them checks the full, explicitly
pinned context, exact file whitelist, CRC, length and SHA-256 of every file.
It does not relabel old outputs as compiled by the current run. The new
scenery/map checkpoints require the current run and commit. Original authored
input provenance remains pinned to run 39070771277 and its saved input hash.

A separate 15-minute probe retains the original scenery/receiver setup at
scale 0.2 but disables terrain self-casting. It records a timeout as an
inconclusive diagnostic, and does not block either release. Any successfully
compiled probe is labelled diagnostic and is saved separately. Its result
will help distinguish terrain casting from the distant receiver cost.

## Validation correction after run 39131482282

The revised scenery converter completed successfully in 1,685 seconds and the
sixteen coordinate probes passed. The subsequent name check failed because
the validator used `bytes_substring in mmap_object`. Membership does not
perform the required subsequence search on that object; a present name can
therefore be reported missing. This was a bug in the recovery validator,
not evidence of failed scenery conversion. It also made the negative name
check unreliable. Both checks now use `mmap.find`, with explicit missing-name
and unexpected-receiver errors. Regression checks use real memory-mapped
temporary files, including missing names and a forbidden original prefix.

That run did not upload the newly converted EDF after validation failed, so
one scenery conversion must be repeated. Subsequent runs write a separate
`scenery-localized-raw.zip` checkpoint immediately after conversion and upload
it even when validation fails. Its manifest explicitly says validation is
pending and `checks_pass=false`; it cannot be restored as the validated
scenery stage. Only the verified checkpoint can feed the graphics job.
Regression checks now run before native conversion on the Windows runner.

The green terrain-cast-off diagnostic job in that run recorded a 900-second
timeout, not a completed MAP. Its result is inconclusive. The unchanged probe
is removed from subsequent automatic builds to avoid repeating that cost.
The revised shadow bake was skipped after the scenery validation failure;
the effectiveness of limiting distant receivers remains untested.

Actual game loading, riding, timing, resets, appearance, FPS and multiplayer
remain untested. The PKZ does not set gravity. Use the separately installed
compatible Quiet Gravity plugin with `preset=half` for single-player Testing.
