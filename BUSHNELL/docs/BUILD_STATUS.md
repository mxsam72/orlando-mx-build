# Bushnell v001 first ride pass

**Native build and download verification: passed.** [First ride-test release](https://github.com/mxsam72/orlando-mx-build/releases/tag/bushnell-v001-first-ride-39193039049), built from commit `c3d473ac122dff9828ac2c3f21190e485e40adf3` in [run 39193039049](https://github.com/mxsam72/orlando-mx-build/actions/runs/39193039049).

The 23,142,442-byte PKZ has SHA256 `5419d0aed15781111b156a52fb8a268f4b57091f695817c4cc39a292cc3fed07`. All four native stages completed successfully, the centerline merged, all 4,198,401 terrain samples matched in source/MAP/TRH, eight material payloads were found, and all 24 scenery coordinate probes matched in EDF and MAP. The published download was independently retrieved and checked again for its SHA256, thirteen canonical archive members, CRC and complete height grids.

The source-stage flags in the nested source validation remain `native_compiled: false` because source generation does not compile the game files. The top-level [native validation](BushnellMX_v001_Validation.json) records the completed compilation.

The eight supplied originals were downloaded, byte-count verified, hashed and reviewed in order. The detailed pass inspected 323 sequential frames at three-second intervals in addition to the initial 109-frame pass. Clip-spanning features and side-view camera excursions were reconciled against the accepted plan.

The source now authors 19 jump/rise profiles and 12 berms. It includes the large west-side tables, south return table, north fence jump, interior jump sequence, shaded hairpins, cone-marked eastern loop, shallow static worn lines, variable widths and reference scenery. Every numeric obstacle dimension is marked `authored_estimate` and retains the clip/time evidence behind its shape.

The accepted JSON route is unchanged. The derived riding line is smoothed by less than 0.54 m at any sample. Terrain is quantized once into the same RAW used by the preview, scenery and native converters. No GoPro GPS altitude or nonstandard gravity settings are used.

A source pass is not an installable game track. The dedicated workflow only emits the ride-test PKZ and publishes its prerelease after native graphics, terrain collision, scenery, closed centerline, race/reset files and package checks pass. The release's `BushnellMX_v001_Validation.json` is the authoritative build result for its commit and run.

Still requiring in-game verification: initial load, grip, jump spacing and landings, camera views, reset behavior, lap timing, object collisions and FPS. Real-world gate and paddock positions remain provisional.
