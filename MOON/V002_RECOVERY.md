# Moon v002 native-build recovery

The original run 39070771277 completed sky conversion, approximately 29 minutes
of scenery conversion, collision compilation and centerline merging. Its MAP
graphics compilation then reached the script's 180-minute process timeout.
The terrain compiler log contained no output, so the underlying reason for the
delay is still unproven.

This recovery uses the exact saved authored inputs from that run. It does not
regenerate or replace the measured terrain, loop, pits, textures or scenery.

- Authored commit: `58a4fe9992c9b78c53d6520f063c260e1d00e9e6`.
- Source artifact: `Moon-v002-native-input-checkpoint`, original run 39070771277.
- Inner input ZIP SHA-256:
  `8c03f41723ea2511a31201f60ad35e94c182d8380d2bec6c2b59716158d0984c`.

Sky, scenery and collision/route now compile in separate jobs. Each successful
job immediately uploads its native output plus a manifest containing file
hashes, source hash, compiler commit and run ID. Restoring a checkpoint checks
its provenance, CRC, exact asset list and every file digest before extraction.
Re-running only failed jobs can reuse successful dependencies from that run.
The recovery workflow is on the separate v002 recovery branch; the original
v002 source workflow is left intact. This workflow intentionally uses the
pinned inputs, so new authoring changes require a new authored checkpoint.

Graphics first compile with baked shadows disabled, with a 20-minute process
limit. Every original height-grid, material-signature, native coordinate,
reset-file, package-layout and size validation gate still applies. A successful
diagnostic package is saved as an artifact and is explicitly labelled
`Diagnostic_No_Baked_Shadows`. It is not the final lighting result and should
not be installed alongside the ordinary v002 package: both use the same
internal track ID.

Only after that diagnostic succeeds does a shadowed build run. It uses
`shadowmaps_scale=0.2` and supersampling 1, with terrain self-shadowing retained,
instead of the original 0.5 / supersampling 2. Shadow volumes remain disabled,
and the sun direction is unchanged. These are a lower-cost first-test bake;
neither its appearance nor compilation speed has been established yet.
The shadowed graphics process has a 90-minute limit, and its job reserves extra
time for cleanup and log upload. This isolates shadow-related cost rather than
simply allowing the same opaque three-hour run again.

The official [MXB Track Creation Guide](https://docs.piboso.com/wiki/index.php/MXB_Track_Creation_Guide)
documents disabling shadow generation for faster test exports, a normal shadow
map scale of 0.2, and reducing supersampling for faster exports.

Compiler output is streamed as available. Every 45 seconds the build also
records cumulative CPU time, memory, I/O counters, free disk space and native
output-file sizes. Those measurements are diagnostic evidence, not a percent
complete or a remaining-time estimate. A quiet compiler may still be busy.

The completed shadowed package gets its own checkpoint. Publication is a
separate job, so a release-upload failure does not force recompilation.
The publisher rejects diagnostic-only or unshadowed validation reports.
All checkpoint and log artifacts request 30-day retention.

Actual game loading, visuals, timing, reset behavior and riding remain pending.
Use the separately installed compatible Quiet Gravity plugin with `preset=half`
for the track baseline. The PKZ does not change gravity. No multiplayer support
for the track or gravity plugin is established by this build.
