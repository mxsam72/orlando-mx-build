# Orlando MX v033 — final sign update

Native build source: `7a3d37662dd8464efa56b6710ef1d42f72b186fd`, branch `rebuild-v033`.
Verified parent: private v032 source checkpoint from release 407076842, SHA256 `c1395b88a4191a5dd6ab55c2af1c610d323c69ac11513be07eed1c36c62a227b`.

Only the three memorial support columns change within retained v032 scenery: 24 vertices, depth 0.24 → 0.12 metres. Their X/Y coordinates, ground anchors, frame, footings, image planes, UVs, material connections and approved memorial bitmap remain unchanged. The supports now lie 44 mm inside both artwork planes. All other old FBX object records and connection records are byte-exact.

The supplied, uncropped 1448 × 1086 Qwikchute logo is imported as a 2048 × 2048 native TGA on a 6 × 4.5 metre double-sided billboard. The mesh preserves the original 4:3 artwork aspect ratio. Its ground anchor is game X/Z `[281.5,164.6]`, approximately 6 metres behind the spectator fence and 13.13 metres outside the main riding corridor. It lies inside the original screenshot mark. The board was shifted 4.5 metres along that marked strip to clear the existing light pole from frontal sightlines. No other object moved.

Both memorial faces were rendered from the same cameras before and after the fix, using actual serialized FBX meshes, connected textures and retained native terrain. The image comparison verifies changed pixels in all three former support bands on each face. The render verification report also confirms the unchanged memorial texture and projects the billboard anchor inside the user's yellow mark. Frontal Qwikchute views from the pits and track side were inspected for readable UVs and pole occlusion.

These are external source renders, not MX Bikes game screenshots. Native compilation additionally checks changed support and billboard coordinates and decoded bitmap payload signatures inside the MAP; the compiled TRH, reset bounds, menu textures and marshals file must match v032 exactly. MX Bikes load/riding/performance testing remains separate.

Reproduce source with `python TOOLS/build_v033.py --source-only` after restoring the verified checkpoint using `TOOLS/v033_release_transfer.py source` in the authorized Windows workflow. Compile with `TOOLS/build_windows_v033.py`. On Linux, use VTK 9.5.2 with a working OSMesa window to run `TOOLS/render_v033_sign_checks.py`; set `SIGN_SOURCE_FOLDER=V032_OUTPUT` and `--only 01,02` for the baseline views, then render `V033_OUTPUT` and run `TOOLS/verify_v033_renders.py`.
