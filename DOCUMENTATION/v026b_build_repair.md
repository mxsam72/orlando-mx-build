# v026b build repair

Baseline: completed v026, source commit 2275efa8e92a4958ea130acd71bc6ea74ed49591.
Failed attempt: rebuild-v026b, commit ee5c10db1cec65eefef6eb9a9e9ef5930b88f8cc.

The first failed build (run 37364931854) completed the protected v026 source,
then stopped before scenery removal. Applying both the full-name replacement
and a second version replacement produced v026bb filenames. The required
v026b release inputs therefore did not exist. The repair performs one version
substitution, preserves original text bytes/newlines, and checks the exact
race/reset/marshal hashes and required release names before compilation.

The later run 37367286425 never received a runner: runner_id was zero and its
job had no steps. Its job was cancelled after about 15 minutes. There are no
compiler logs or PKZ artifacts from that attempt. The underlying reason for
that allocation failure is not established.

A Windows 2022 diagnostic run (37374759783) received a runner but the protected
baseline scenery hash check rejected its regeneration before the v026b edit.
The same Python/package versions produced a different scenery binding hash;
the input FBX hash was identical. The repair therefore retains windows-latest,
which supplied Windows Server 2025 / windows-2025-vs2026 for the successful v026
build. The accepted hash check remains mandatory. The precise cause of that
cross-image byte difference is not established by these logs.

The attached obstruction clip was sampled at 0, 5, 10, 15, 20, 25, 30 and 35
seconds, with additional one-second samples from 18 through 32 seconds. The
trees intersect the relocated corner around 19-25 seconds; the pale marker is
directly in the riding line around 28-29 seconds. Mesh positions identify three
overlapping tree objects (tree_215, tree_222, tree_525) and two intruding marker
objects (SOFTCPLAS_marker_53, SOFTCPLAS_marker_55) in that local section.

The earlier broad 8 m tree / 3 m marker edge-clearance rule is replaced with
local corridor intersection and an exact, coordinate-checked removal list.
Low tree vertices must enter the 7.8 m T09 riding width plus a 0.5 m margin on
each side and fall below 2.4 m rider headroom above v026 terrain. Markers must
lie inside the authored track edge between the R10 landing and R11 runout.
Unexpected selections stop the build. Retained FBX objects, material/texture
records, unaffected connections, and global axes are checked byte for byte.
FBX definition counts retain the separate GlobalSettings entry.

Terrain, route, masks, dirt materials, starting grid, pits and unrelated scenery
remain as v026. Native validation reports geometry and physics preservation
relative to v026. Compilation and source checks do not establish in-game riding,
visual quality or FPS; those checks require MX Bikes.
