# Orlando MX v009 geometry candidate

The complete lap is rebuilt as continuous terrain sectors over the verified v008b
baseline. Eighteen independently parameterized crests/ramps replace the legacy
jump envelope. Fourteen turn sectors carry physical asymmetric banks and shallow
grooves. Long and short terrain waves, entry braking chop, exit roughness and
shoulder blends connect them. The preferred lane is approximately 7.8–8.7 m wide;
the cleared dirt and reset limits remain wider.

## Reference interpretation

The real GoPro video is the geometry authority; the v008 test video identifies
mismatches. Landmarks and feature order override approximate timestamp anchors.
The real clip repeats the opening physical area after roughly 124 seconds.
S12–S14 therefore reference earlier physical sectors rather than extending the lap.
The station map records uncertainty and the alias relationships. Estimated physical
boundaries can be uncertain by roughly 15–25 m. No surveyed dimensions are claimed.

The native horizontal centerline and race topology are retained. Their sequence
agrees with the available landmark evidence; preferred turning radius and width
change through the lower grooves and raised outside terrain. A stronger geometric
alignment claim needs surveyed/aerial registration or additional rider feedback.

## Sector changes

| Sections | Implemented terrain changes |
|---|---|
| S09 | Signature ramp at station 989 m; 16 m progressive face, rounded rollover, short crest and 24 m landing; reduced setup mound; raised preceding berm. |
| S07–S08 | Major tree-side ramp at 759 m; 16.5 m face and 22 m landing; deep banked T09 with compact linked exit crests. |
| S04–S06 | Long bowl turns, lower preferred grooves, removal of oversized legacy platforms, progressive turn-exit jump at 536 m and rough landing/runout. |
| S01–S03 / S12–S13 | Pole-side ramp at 40 m with 17 m face and 22.5 m landing; first carved sweeper, linked crests, rolling west-edge setup and reduced neutral space. |
| S10–S11 | Wooded settling waves/jump and physical banks through the final approach turns, maintaining relief toward the pole-side sequence. |
| S14 | Same physical S03/S04 terrain seen again: coherent worked relief and supported sweeper. Native route closure is checked separately at station zero. |

Dimensions above are recipe estimates before lateral blending and grade relaxation.
The QA figures sample the actual quantized heightmap, not the ideal recipe.
Signature R14 local design relief is 3.55 m; this is not an absolute map elevation.

## Source evidence

Final heightmap SHA-256:
`bf6c6d335ff1f555555e4d66c9db5d5ed6d7f07cede21bc39167ad31d20a0f64`.

- Height range: 1.63754–6.53202 m within the 18 m native scale.
- Maximum terrain raise/lower versus v008b: +1.53262 / −2.16791 m.
- Maximum changed-terrain grade: 0.77953; shaped racing-corridor grade: 0.56436.
- Zero new excessive-grade nodes; zero terrain delta outside the protected corridor.
- Native loop height difference: zero; horizontal endpoint separation about 8e−12 m.
- The raw and 16-bit PNG heights are identical. Sector boundary finite differences pass.

The final surface includes local smoothing of steep inherited shoulders. Maximum
target relaxation is 0.69331 m at a shoulder; it is documented rather than hidden
as an unchanged ideal profile. Checkpoints retain intermediate validation separately.

## Integration and limits

The exact seven v008b corrected textures and the 417-tree treatment are retained.
Scenery is rebound vertically with X/Z, topology and materials preserved. Fence
rails conform by vertex and their normals are recomputed. Visual racing/worked
masks follow the narrower shaped corridor; changes are bounded to that corridor.
Physics masks and race RDF stay unchanged because route alignment is unchanged.
Cameras and marshals follow local ground changes. Source QA checks pit and start
support before native compilation.

Authoring evidence includes the section plan, before/after elevation and terrain
plots, major jump profiles, representative berm cross-sections and 14 section
views. These are source visualizations, not in-game screenshots. Native compilation
has its own validation report. Ride feel, cockpit recognizability, deformation,
multiplayer and game rendering remain subject to the ride-test checklist.
