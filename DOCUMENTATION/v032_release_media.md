# v032 release media

The release gallery contains eighteen external renders of the real v032 source,
at 2560 x 1440. Views cover the whole track, pits, the Pup memorial, entry and
Bithlo signs, all four custom vehicle/bike pairs, seven jump views and the start
lane. These are not MX Bikes screenshots or synthetic track illustrations.

`TOOLS/render_release_media_v032.py` reads `V032_OUTPUT/scenery.fbx`, the native
height field, FBX-connected textures, and the fifteen dry native HMF layers.
It preserves source coordinates and UVs, renders in right-handed XZY axes, and
uses facing triangles on explicitly double-sided artwork boards. Regional
terrain crops use the exact native height samples; distant ground uses a coarser
sampling of the same field. Camera, sky background and lighting are external.
Game-specific normals, wetness, shaders and vegetation animation are not fully
reproduced. Every image is labelled as a source render.

Dependencies: Python 3.12, NumPy, SciPy, Pillow, VTK 9.5.2, and a supported
offscreen OpenGL implementation. This build used VTK's OSMesa window with
Mesa 25.1.7 and llvmpipe. `MEDIA_VTK_WINDOW` can select an alternate VTK window
class. Linux installations need libOSMesa on their library search path.

Restore the complete v032 source checkpoint first. From the project directory:

```bash
python TOOLS/render_release_media_v032.py --draft --width 1280 --height 720
python TOOLS/render_release_media_v032.py
python TOOLS/package_release_media_v032.py
```

Optional `--only 04_` selects a single numbered view. Output is written to the
project parent's `deliverables-v032-media` directory; temporary terrain texture
caches are in `v032-media-work`. The packaging step expects the post draft and
reusable template in the output directory. It validates image hashes/dimensions
and the finished archive, adds a cover/contact sheet, and excludes draft images.

The terrain, FBX and HMF hashes are checked before and after rendering. The
compiled PKZ is never edited by either script.

The current memorial's three support posts cross narrow portions of its artwork
on both sides. The gallery preserves that geometry. No supports were hidden,
removed or moved for a better screenshot. The v032 package has not been rebuilt
or changed as part of this media task.

The public-post draft retains placeholders for the public download URL, tested
MX Bikes version and any remaining contributor credits. A native in-game test
is still needed before claiming v032 load, appearance or multiplayer support.
