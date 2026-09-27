# Reproduce Orlando MX v009

Use the `rebuild-v009-geometry` branch of `mxsam72/orlando-mx-build`.
Keep every BUILD_INPUTS, BUILD_V007 and BUILD_V008 archive part in the checkout.

On Windows, install Python 3.12 or newer and double-click `BUILD_V009_LOCAL.bat`.
The launcher creates a dedicated virtual environment, installs the pinned authoring
dependencies, restores verified inputs, applies the v008b correction once, rebuilds
all terrain sectors, runs source QA, rebinds scenery, prepares release support files,
downloads the hash-pinned official PiBoSo tools, compiles and packages v009.
Internet is required for the initial dependencies and compiler downloads.

The separate output is `12_RELEASE/OrlandoMX_2026_v009.pkz` with a SHA-256 file.
Copy the PKZ into `Documents\PiBoSo\MX Bikes\mods\tracks\motocross\` and select
**Orlando MX 2026 v009**. Keep the PKZ intact. Earlier versions remain separate.

For source-only authoring QA on Linux, macOS or Windows:

```sh
python -m pip install -r requirements-v009.txt
python TOOLS/build_v009.py --source-only
```

The native compiler requires Windows. The `Compile Orlando MX v009` GitHub workflow
performs the same complete build on a Windows runner and uploads both the installable
track and its evidence. A failed run must not be treated as a completed package.

Generated assets are isolated in `BUILD/v009_work`, `BUILD/v009_baseline`,
`BUILD/v009_cache`, `BUILD/v009_stage`, `V009_OUTPUT` and the v009 release folder.
The original versioned pipeline is retained. The baseline marker is only accepted
when the real texture, scenery and terrain hashes also match; a repeated build does
not recolor already-corrected inputs.

Inspect `DOCUMENTATION/v009_geometry_validation.json`,
`v009_scenery_validation.json`, `v009_release_validation.json`,
`v009_native_validation.json` and `v009_qa/`. Native failure logs are also written
there. Successful source QA does not establish in-game handling or replica fidelity;
complete `v009_ride_test_checklist.md` with cockpit footage.
