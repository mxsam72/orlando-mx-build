# Orlando MX v054 A/B/C update — published and verified

Download: https://github.com/mxsam72/orlando-mx-build/releases/download/v054-start-corners-38605191325/OrlandoMX_2026_v054.pkz

Release: https://github.com/mxsam72/orlando-mx-build/releases/tag/v054-start-corners-38605191325

v052 is the accepted baseline (commit 109bf8469e09d9653898f975c906729e1ca53530). The cancelled v053 palette changes are excluded. v054 implements the user's annotated A/B/C drawing:

- A extends the approach/return and moves the outside corner east by roughly 25 m, making room for the revised start.
- B preserves the origin and all 24 gate positions, runs through the new gap, and merges farther along the existing main corner at old authored station 500 m. The bank opening has a smooth elevation transition. Sector one follows this merge; the bypassed T05 checkpoint is normal-lap-only.
- C broadens the entry sweep into R17. Eight roller profiles, original heights and 10 m authored spacing remain. The underlying transported floor is smoothed locally to remove historical impressions; independent height checks detect eight crests.

Static v052 soil photographs, colour/wet tiles, tiled normals and shaders remain exact. Only affected corridor masks and directional atlas pixels move. There are still 14 terrain layers. All road/asphalt/concrete geometry and practice barriers remain exact; 139,879 protected RAW samples are unchanged. Necessary nearby scenery moves without changing vegetation counts. Disconnected grass blades remain individually ground-bound. Gate and pit world positions, unrelated jump riding lines, lighting, cameras and logo are checked exact. Race, reset, marshal references and track-info map follow the updated route.

Reviewed source: commit 03b21cb68c34366ddc0f8a8a63995f9b31abc528, successful source run 38605191325. Source checkpoint is preserved in release 412990475, tag v054-start-corners-38605191325. Matched A/B/C previews were checksum checked and visually reviewed: https://github.com/mxsam72/orlando-mx-build/blob/rebuild-v054/PREVIEWS/v054/README.md . These are source renders, not game screenshots.

Official native exports completed in run 38607699127 from compiler commit 76696afc917cbb8ade40e391c69ad2b2248cc7fc. FBX2EDF: 252.45 s; TerrainEd TRH: 5.73 s; TrackEd merge: 38.70 s; TerrainEd MAP: 2428.02 s. All four returned zero. Its final general texture checker incorrectly treated the alpha-only specular map as a colour bitmap. The binaries were saved before that check. The corrected validator uses the established v052 bounded alpha-stream decoder for this bitmap in both EDF and MAP and verifies the retained terrain tiles directly in MAP.

Successful final validation/publication: run 38617424749, commit ac9e41f4d71c6e10052b61c8a63ae50a262d228a. TOOLS/resume_v054_native.py recovered checksum-pinned native outputs without changing them, verified the diagnostic archive, all 11 non-native package members against reviewed source, and the 13-entry package root/CRC. It then ran the complete corrected native checks and published the reviewed source release.

Final verification:

- 3,501 native scenery probes (3,309 retained, 192 changed), max error 0.000043987234 m; EDF preflight and MAP checks passed.
- 92 object colour/normal/specular texture checks, including decoded zero-alpha foliage records in EDF and MAP.
- 29 retained v052 terrain bitmap signatures plus the two revised route atlases verified in MAP.
- New collision differs from both delivered v052 and the unmerged TRH; official main/start merge completed.
- All source, road, scenery, gate/pit, jump/roller, race-reference, archive and size-budget checks passed.
- PKZ: 920,767,498 bytes (+0.181829% from v052), SHA256 3d3324a29d488ddb49ae53454cc948cfb7a673ca308dbd8518410a03cb773e21.
- Final report: OrlandoMX_v054_Validation.json, 142,952 bytes, SHA256 9c485385b2fdfb373b5e9d2a2e2ced9ab1ec48154a2c8f3023f49b7b4ec16fd7.
- Published asset sizes and SHA256 digests match the final report. Final validation artifact 11920378370 (166,198 bytes, SHA256 04f9401a5632aee2ac0dc62a120cd425b8cbf5e71aae8fdb7972223c611f8980) was downloaded and checksum checked.

Actual MX Bikes load, gate-drop/first-lap timing, resets, riding and FPS still require the user's in-game test. No in-game visual/riding/performance pass is claimed. Install_v054.txt, the PKZ checksum, source checkpoint, saved native scenery, previews and final validation report are available in the published release.
