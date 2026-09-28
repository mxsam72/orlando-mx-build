# v011 — tabletop and facility rebuild

Baseline: `rebuild-v010-irl-corrections` at `a44ca6c60410cb30f8c9425a3392bf566d61023a`.
Work branch: `rebuild-v011-jumps-facilities`. v010 remains intact.

Checkpoint 01: branch and scope established.
Checkpoint 02: jump primitives and encoded-terrain QA committed as `f7e239aa2c40d27e7282802d02b0af3cc82a8d01`.
Checkpoint 03: facility meshes, roads and Windows pipeline prepared and compiled successfully by GitHub Actions.

Geometry: four tabletops (R01/R05/R10/R14), two provisional doubles (R07/R16), one jump out of turn (R09), one modest step-down shelf (R18), six rollers and four natural crests. R01 has a 10 m deck and 2.8 m authored rise. Actual encoded decks and valleys pass structural QA. Start gate is flat, 24 stalls reconstruct correctly, and T05 merge centerline grade remains below 0.18.

Reproduce on Windows: `BUILD_V011_LOCAL.bat`, or `python TOOLS/build_v011.py` after installing `requirements-v009.txt`. `--source-only` stops before native compilation. The v011 GitHub workflow stores the generated source checkpoint before attempting MAP/TRH compilation.

Native compilation is verified. Not yet claimed: in-game riding, first-lap/reset behavior, multiplayer behavior, or precise survey accuracy.

Available references: current v010 test; original real GoPro; IMG_3591, IMG_3592, IMG_3594, IMG_3595, IMG_3597; v011 handover dated 2026-09-28. All five facility/spectator clips have now been reviewed; IMG_3591/3592 mainly reinforce pit-road, office/check-in, bleacher and parking/camping context.

Priorities: true R01 front tabletop; separate jump primitives; timber/mesh frontage, covered stand and bleachers; pit access roads, office, restroom, concession and informal parking. Preserve the v010 start grid and T05 merge. The gate is to the right in the established design orientation; this is not a claim of geographic east.

Dimensions and unsurveyed object positions are authoring estimates. New source and native compilation will be validated separately from the user's next ride test.


## Verified native build

GitHub Actions workflow `Build v011 IRL corrections` completed successfully.

- Workflow run: `36446464053`
- Build source commit: `ea330f6b64bbdfcbf72d02f3e58919cec1edbb53`
- Game artifact: `OrlandoMX-v011-game-candidate`
- Game artifact ID: `10982205006`
- Evidence artifact ID: `10980839995`
- Source-checkpoint artifact ID: `10981575049`
- PKZ: `OrlandoMX_2026_v011.pkz`
- PKZ bytes: `139735618`
- PKZ SHA-256: `548062110f43b0677dd27f9d31f6be0cdd53821f857ab453f4502360709d270a`

Official PiBoSo native stages returned success for EDF, MAP, TRH and centerline merge. Source validation also passed.

The remaining release gate is an actual MX Bikes ride test: 24-rider start/T05 merge, first finish crossing, reset behavior, full timed lap, and P01-P14 comparison.
