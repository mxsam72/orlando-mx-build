> **v055 was rejected in game.** Its landing patch cut part of T03/T12 and the shoulder blend hid track boundaries. The `rebuild-v056` correction restores the accepted v054 banks, masks and full-resolution dirt, with a narrowly scoped landing crown correction. Native validation/publication status: see the [v056 workflow](https://github.com/mxsam72/orlando-mx-build/actions/workflows/build-v056.yml).

# Orlando MX 2026 v006

Native MX Bikes rebuild refined from the user's complete GoPro lap and ridden v005 test. Retains user-traced aerial lap connectivity. Dimensions are construction estimates. See DOCUMENTATION/v006_comparison.md for section-by-section changes.

Windows CI verifies input hashes, compiles original scenery and terrain with pinned official PiBoSo tools, checks compiled scenery coordinates, merges both centerlines, and validates the PKZ archive. In-game riding of v006 is not performed in CI.

TOOLS/pack_inputs.py creates the CI input archive. TOOLS/build_windows.py produces the installable PKZ.
