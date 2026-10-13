# v048 finish tabletop dirt benchmark

R01 only: takeoff furrows, compacted deck/lip, wheel-worn and churned landing,
lighter disturbed soil on the existing banks. This is a visual material sample;
the accepted 51.47 m tabletop geometry and all collision/riding profiles remain
unchanged. Do not extend the treatment to the triple or table-single until the
user has compared this sample in-game.

The baseline is the verified published v047 (252 A trees, 45 B trees) with exact
v046 whole-track dirt. Restore SHA-pinned release assets, never regenerate the
accepted scenery or physical terrain for this build. Patch existing 8K macro
colour/normal atlases and three 4K masks only inside R01. Add one 2K clod
colour/normal tile with two new, fully scoped masks. Retain every existing HMF
layer and depth; both appended visual layers also have 4 m cosmetic thickness.
This is independent of the unchanged finite physical surface budget of 0.31 m.

The code measures centerline surface distance from the accepted height field,
and converts virtual-relief gradients into the surface tangent frame. These
normal-map grooves/clods do not alter wheel collision or the jump silhouette.
Source comparisons use identical cameras and daylight. They omit scenery in
both versions and are explicitly labelled as source previews, not game footage.

Before publishing: verify every changed atlas/mask pixel stays in scope; all
unchanged sources and depth settings; the exact v047 EDF/TRH/race/lighting;
actual new/retained native bitmap digests; all 2266 accepted scenery probes;
and the final 13-entry PKZ CRC. Preserve validated source before compilation and
the compiled PKZ before extended verification. A validator failure must reuse
those saved native bytes where possible instead of repeating compilation.

In-game appearance, deformation over repeated laps and FPS require the user's
test. Install beside v047, reset the track, compare the tabletop in matching dry
weather and camera, then ride with the usual deformation setting enabled.
