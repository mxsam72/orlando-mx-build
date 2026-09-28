# v010 implementation checkpoint

Baseline: v009 commit 4bdb20c2c34ce91cdd15c63546d5f7b662d9c4a4.
Branch: rebuild-v010-irl-corrections.

## Checkpoint 00 — scope locked (2026-09-28)

The user authorized implementation. Gate moves to the right of spectator frontage, with a separate start lane into T05. Spectator fence belongs outside T14–R01–T01. Old aerial imagery defines these relationships only. Native map orientation is authoritative for “right.” Exact dimensions are authoring estimates.

No geometry changed in this checkpoint. v009 remains intact. Implementation and validation still pending; no v010 PKZ exists.

## Resume

1. Restore the branch and read V010_SOURCE/requirements.json plus V010_SOURCE/review_section_sync.json.
2. Implement a separately named v010 pipeline. Keep v009 scripts and release files unchanged.
3. Build gate/grid/start terrain/T05 merge/fence as one coherent change. Validate route direction and first-lap handling before claiming a playable release.
4. Apply approved jump and corner changes by physical section, saving source and QA checkpoints.
5. Commit progress after each working stage, and replace this status with exact outputs, commands, checks and remaining work.
