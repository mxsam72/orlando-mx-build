# v065 feature photos

Twelve cinematic views of the released v065 source: the four pit vehicles and
candy board, individual vehicle portraits, Pup Whatley's memorial, the crocodile
pond, speedway, tabletop and berm. The delivered PNG originals are 2560 × 1440.

These are Blender Cycles source renders with cinematic lighting and depth of
field. Native track geometry, scenery and texture assets are retained. The
cardboard material's U orientation is translated for readable lettering in the
renderer. The native FBX and terrain RAW hashes are checked during packaging.

Reproduction requires the released v065 source checkpoint extracted at the repo
root, the existing cinematic preparation step, and a Python 3.11 environment with
`bpy==4.5.3`, `numpy==1.26.4` and `Pillow==12.3.0`.

1. Run `TOOLS/v065_cinematic_prepare.py` with the authoring Python.
2. Run `TOOLS/v065_feature_cinematics.py` with the bpy environment's Python.
   Use `--draft` for camera checks or `--shots 08,09` to select numbered views.
3. Run `TOOLS/v065_feature_deliver.py` with the authoring Python to validate the
   images and package the originals, contact sheet and provenance.

`renders.json` records the final cameras, sun settings, image hashes and asset
provenance. The photo workflow does not invoke the native MX Bikes compilation.
