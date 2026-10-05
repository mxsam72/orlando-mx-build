# v027 implementation

Reference: the supplied recent correct-layout GoPro and v026 test ride, reviewed
at five-second intervals with extra entrance detail. Independent findings were
recorded before the second ChatGPT's notes were read. The version incorporates
the intended v026b obstruction correction directly; there is no separate v026b
release in this branch.

The new behind-gate staging bay connects to the accepted pit road. Broad oak
canopies shade a pale, worn sand apron with a pickup, trailer, table and bikes
on stands. A separate 6.5 m practice lane runs outside the wide race-start lane,
with timber rails to the rider's left, woodland to the right and short metal
barrier banks before it blends onto the accepted start route. Its centre joins
that route at start station 122 m and uses the accepted remaining start route
to reach the active track. These coordinates/dimensions are fitted authoring
estimates, not a survey of the footage.

The surface pass uses warmer prepared brown dirt, paler sand/compacted pit soil,
four blended longitudinal grooming directions and multiple interrupted traffic
lines. Existing curved corner rut trajectories drive packed floors, loose
deposits and modest additional physical relief together. The active riding
strip suppresses the pale visual sand overlay while physical material types
and thicknesses remain the accepted declarations. Grass edge masks vary with
the same local surface fields. Sparse default damp-looking patches stay matte;
the previously removed water geometry is not restored.

The accepted macro centreline, start, turn and jump-profile files remain exact.
The new relief is limited to approximately 2–3 cm in corners and small local
pit/access smoothing. New low props/fences/trunks are checked against main,
race-start, practice and pit-connector corridors; oak overhangs must clear
2.4 m rider headroom. Existing custom vehicles, bikes, sign artwork, corrected
facilities, race/reset data and menu logo are preserved.

The isolated scenery edit removes tree_215, tree_222, SOFTCPLAS_marker_53 and
SOFTCPLAS_marker_55 using coordinate-checked corridor tests. Retained FBX object
records and connections are checked byte-for-byte before the new pit objects
are appended. New mesh coordinates and bike UVs are serialized and read back;
FBX definition totals include the separate GlobalSettings type.

The baseline regeneration has produced a differing serialized scenery hash on
some Windows runners despite matching terrain/start and layout checks. This
branch accepts that source only if the complete official-tool compiled EDF
matches v026's recorded 173,137,253-byte scenery SHA-256 exactly. That proof is
saved, and future v027 builds restore the immutable verified checkpoint rather
than depending on a fresh legacy scenery regeneration. A mismatch in the
native EDF still stops the build. The checkpoint actually selected for v027
matched v026's terrain, scenery and start source files byte-for-byte; no native
equivalence exception was needed for that checkpoint.

The Windows compiler builds fresh MAP/TRH files, merges the accepted native
centreline/start, verifies compiled object coordinates and exact terrain/prop
bitmap payloads, then checks the 13-file PKZ root and CRCs. Source previews are
not game screenshots. Native/source checks do not establish MX Bikes loading,
riding, resets, deformation or FPS; the package is a game test candidate until
those checks are completed.
