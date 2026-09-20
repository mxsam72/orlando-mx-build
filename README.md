# Orlando MX 2026 v006

Native MX Bikes rebuild refined from the user's complete GoPro lap and ridden v005 test. Retains user-traced aerial lap connectivity. Dimensions are construction estimates. See DOCUMENTATION/v006_comparison.md for section-by-section changes.

Windows CI verifies input hashes, compiles original scenery and terrain with pinned official PiBoSo tools, checks compiled scenery coordinates, merges both centerlines, and validates the PKZ archive. In-game riding of v006 is not performed in CI.

TOOLS/pack_inputs.py creates the CI input archive. TOOLS/build_windows.py produces the installable PKZ.
