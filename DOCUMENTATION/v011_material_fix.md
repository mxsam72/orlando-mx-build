# v011 facility material fix

## Symptom

In the user's in-game v011 test, the new parametric facility objects render as plain white while the terrain and legacy scenery remain textured.

## Root cause

The v011 facility generator clones the validated baseline `marker_white` / `white` FBX material and then attaches generated per-material textures. The fallback FBX diffuse colour was left at `1,1,1` (white).

The native `fbx2edf` import did not resolve the generated facility bitmap links as intended, so the compiled scenery fell back to the cloned white diffuse material.

Adding TGA files to an already compiled PKZ cannot correct this: the material assignment is compiled into the scenery EDF / MAP during the native build.

## Source-level correction

Two source changes are required and have been committed:

1. `TOOLS/append_facilities_v011.py`
   - encode each intended PALETTE colour directly into the FBX material's `DiffuseColor` / `AmbientColor`;
   - retain the diffuse texture connection;
   - leave the diffuse scalar at 1.0.

2. `TOOLS/build_windows_v011.py`
   - stage each generated facility texture both in the native stage root and `scenery.fbm/` before `fbx2edf`, covering the two normal FBX relative-texture lookup conventions.

Relevant commits:
- `4aef58356fd3512efcc356e92965a097c14fa2e0`
- `e025ade00ac714fdebaf3e0cb09257efb3b5e435`

## Validation requirement

The correction requires a fresh native `fbx2edf -> terrained_map -> terrained_trh -> tracked_merge` build. A post-build PKZ file-copy patch is insufficient.

The corrected candidate must be tested after removing/replacing prior v011 packages and restarting MX Bikes. Verify at minimum:
- timber fence/stand is brown/dark timber;
- aluminum bleachers/roof pieces are gray metallic;
- office/restroom siding is gray with pale trim;
- vehicle bodies use red/navy/neutral materials rather than white;
- oak bark and leaf groups are brown/green;
- utility poles are timber and flag colors are visible.
