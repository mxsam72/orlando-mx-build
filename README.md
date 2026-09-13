# Orlando MX v004 native build

Private compilation workspace for the estimated Orlando MX track.

The checked input bundle preserves the saved v004 terrain, surface masks,
textures, scenery FBX and race files. Its parts and every extracted file are
verified with SHA-256 before compilation. The editable source checkpoint is
`OrlandoMX_2026_v004_Compile_Ready.zip`.

GitHub Actions uses a Windows runner and the official PiBoSo authoring tools to
produce the native MAP and TRH, convert scenery to EDF, merge the racing and
start centerlines, and package the track. The downloadable Actions artifact
contains `OrlandoMX_2026_v004.pkz` and its checksum.

For a local Windows build with Python 3:

```
python TOOLS/unpack_inputs.py
python TOOLS/build_windows.py
```

Put the completed PKZ in `PiBoSo\MX Bikes\mods\tracks\motocross` and restart
MX Bikes. Do not rename the source bundle or any input part to PKZ.

The layout is an estimated recreation, not a surveyed replica. Compilation
and structural validation do not establish in-game loading or ride testing.
See `DOCUMENTATION/native_build_validation.json` in the build-evidence artifact
for the actual compilation and testing status.
