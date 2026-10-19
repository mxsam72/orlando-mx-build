# Bushnell Motocross / v001

A separate MX Bikes track project from the eight GoPro HERO9 Black walking clips recorded October 18, 2026. Work lives on **`bushnell-v001`**, under **`BUSHNELL/`**. Orlando and Moon source, geometry and physics are not used.

The first ride pass has **19 individually authored jump/rise profiles, 12 berms, shallow worn riding lines, variable lane widths and Bushnell reference landmarks**. It uses standard game physics. The approved route and the user's nine yellow connection corrections are retained. Camera excursions beside jumps do not become bends in the riding line.

## Downloads and build evidence

The [Bushnell workflow](https://github.com/mxsam72/orlando-mx-build/actions/workflows/bushnell-v001-source.yml) builds the source, scenery, native MAP/TRH and race setup, then publishes a separate **Bushnell MX v001 — first ride test** prerelease after validation. Check [releases](https://github.com/mxsam72/orlando-mx-build/releases) for that Bushnell title and tag prefix `bushnell-v001-first-ride-`.

Install **`BushnellMX_v001.pkz`** unchanged in the active MX Bikes `mods/tracks` folder and choose **Bushnell Motocross v001** in Testing. The downloadable installation text, validation JSON, source overview and preview ZIP accompany the PKZ. In-game load, riding, timing and FPS verification remain pending until a rider tests it.

## Reference and accuracy

- `references/videos.json`: all eight original clips in viewing order, exact byte counts and verified SHA256 hashes. Originals stay outside Git.
- `source/approved_layout.json`: immutable accepted plan, checked by SHA256.
- `source/terrain_features.json`: every jump and berm, with cited video/time spans and estimated dimensions. Shared features across clip boundaries are counted once.
- Heights, lengths, widths and landmark positions are **authoring estimates from the footage**, not surveyed measurements. GPS altitude is excluded because of drift.
- The riding line uses a 0.85 m smoothing kernel to remove footstep/GPS corners. Its maximum displacement from the accepted trace is about 0.54 m; the approved source file is unchanged. Native line/arc fitting is checked separately.
- Pits and the eight-rider test grid are provisional. The precise real start gate has not been established.

## Rebuild

```bash
python -m pip install -r BUSHNELL/requirements.txt
python -m unittest discover -s BUSHNELL/tests -v
python BUSHNELL/scripts/build_source.py
python BUSHNELL/scripts/build_race.py
python BUSHNELL/scripts/setup_blender.py
# Run the verified Blender path printed by setup_blender:
blender -b --factory-startup -t 8 --python BUSHNELL/scripts/build_scene.py
python -m unittest discover -s BUSHNELL/tests -v
python BUSHNELL/scripts/build_native.py bundle
```

The workflow authenticates the source archive before running the pinned official PiBoSo Windows converters. It checks fresh EDF/MAP/TRH headers, all 4,198,401 terrain samples in source/visual/collision grids, native scenery coordinate probes, embedded material pixel signatures, closed-centerline merging, reset boundaries, canonical archive naming and ZIP integrity before publishing. Source renders are labeled as source previews and are not in-game screenshots.

The older `01_source_foundation.svg` and `docs/source_validation_v001.json` record the initial flat foundation, before this ride pass. Current generated evidence comes from the workflow and the downloadable release validation.
