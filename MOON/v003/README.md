# Taurus–Littrow Crater Send v003

Replace the v002 rollers with six 90–175 m crater jumps and an optional
220 m transfer across measured Shorty crater. The main craters are 200–270 m
in diameter, cut 18–32 m below their surroundings before launch/landing
earthworks. Takeoffs are 32 m wide; landings are 48 m wide and 85 m long.
Half gravity, **4.905 m/s²**, remains the design baseline.

The 1,600 m arena starts from the existing LROC 2 m elevation crop. The
central 90 m radius around Shorty retains measured heights. All giant outer
craters, ramps and landings are fictional additions. Native scenery uses
the measured near terrain and 23.84 km wide mountain context, with original
clasts and markers. No riding terrain is substituted with visual-only mesh.

The new sky contains 12,500 original star points and a photographic NASA
Earth disk. Its 12° diameter and 24° elevation are deliberate art choices,
not a reconstructed astronomical view. Sky/ambient files apply it to all
weather states, with no atmospheric fog. Static terrain occlusion is baked
into a masked texture using the same sun vector as the game. Native
shadow-map and shadow-volume baking is disabled to avoid the v002 bottleneck.

## Reproduce

Install `MOON/requirements.txt` and `psutil>=7,<8`. From the repository root:

```sh
python MOON/v003/scripts/build_v003.py
python MOON/v003/scripts/review_v003.py
blender -b --factory-startup -t 8 --python MOON/v003/scripts/scene_v003.py
python -m unittest discover -s MOON/v003/tests -v
python MOON/v003/scripts/native_v003.py source
```

`setup_blender.py` verifies Blender 4.5.3 against its size/SHA256. The source
bundle records every generated input and its originating commit/run. The
workflow runs sky, scenery and collision conversions independently on
Windows with the pinned official tools in `BUILD/tool_versions.json`.
Each conversion is preserved before validation, and validated assets are
uploaded separately. The graphics job restores those exact checkpoints.
Publication runs independently from the complete package checkpoint.
Rerunning a failed job therefore does not repeat successful native jobs.

Native validation compares all 4,198,401 RAW samples with collision and
visual heights, checks 20 geometry coordinates, native diffuse/normal
signatures, both sky bitmaps, centerline merge, reset file structure and
the canonical PKZ basename/internal directory. Final files must pass before
the workflow creates a GitHub prerelease. `taurus_littrow_mx_v003.pkz`
must retain that name, which matches its internal folder.

The source checks trace nominal ballistic paths against the quantized
heightfield and compare flight/landing slopes. They omit suspension, drag,
wheel contact and rider control. In-game load, rideability, lighting, FPS,
resets, lap timing and multiplayer remain separate tests. The previews
render exported source geometry and textures; they are not game captures.

## Sources and credits

- Existing LROC terrain crops and their projection/provenance records:
  `MOON/source/shorty_2m.tif`, `valley_context_20m.tif` and matching JSON.
- [NASA Earth Observatory — The Blue Marble](https://science.nasa.gov/earth/earth-observatory/the-blue-marble-2181/),
  NASA / Reto Stöckli / Robert Simmon / MODIS Science Team. Source JPEG SHA256:
  `df0434cf74a06e9dd3c7b9b197b6e215e13db70b4210115969eac9e89f6da502`.
- [KBOLTZ MOONED](https://mxb-mods.com/kboltz-mooned/) supplied by the user
  as a visual/technical reference. Its ZIP/PKZ is readable and includes FBX
  models plus compiled skies. No reuse license was found in the package
  or listing. **No KBOLTZ models, skies or textures are redistributed.**
  The new source geometry, materials and stars are authored here.
