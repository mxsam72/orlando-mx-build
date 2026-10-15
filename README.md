> **v056 is available:** [download the corrected PKZ](https://github.com/mxsam72/orlando-mx-build/releases/download/v056-restored-corners-38665837940/OrlandoMX_2026_v056.pkz). Restores all 14 v054 corner grids, original track boundaries and full-resolution dirt. Native compilation, complete MAP/TRH height checks, texture/scenery and archive gates passed. [Verification and limitations](DOCUMENTATION/v056_verified_delivery.md). v055 is rejected and superseded. In-game riding and appearance remain pending.

# Orlando MX 2026 v006

Native MX Bikes rebuild refined from the user's complete GoPro lap and ridden v005 test. Retains user-traced aerial lap connectivity. Dimensions are construction estimates. See DOCUMENTATION/v006_comparison.md for section-by-section changes.

Windows CI verifies input hashes, compiles original scenery and terrain with pinned official PiBoSo tools, checks compiled scenery coordinates, merges both centerlines, and validates the PKZ archive. In-game riding of v006 is not performed in CI.

TOOLS/pack_inputs.py creates the CI input archive. TOOLS/build_windows.py produces the installable PKZ.
