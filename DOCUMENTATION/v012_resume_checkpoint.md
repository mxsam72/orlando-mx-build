# v012 resume checkpoint — native build in progress

Source/native input commit: `60b028fdc38f1c3e6470d4d7ae2ff61fee13e877`.
Branch: `rebuild-v012-final-obstacles-layout` in `mxsam72/orlando-mx-build`.
Actions run: `36660342389`.
Job: `109713480360`.

All requested R01–R18 geometry is authored; bathroom/office and outside-T05 start loop are implemented. All 18 encoded profiles, 24 gate positions, checkpoint modes, loop topology and 91 facility mesh clearances pass locally. A fresh Windows source build/native compile is running. Do not restart from v011 or overwrite older versions.

Source checkpoints:
- corrected v011 base: 56b7fed68c210c6090458d046a6ddc7490be9267
- v012 branch/instructions: 763d67017d0bb9c03ce3229638e272dafae422e8
- R01–R05: ae14e82df0345003e995bcff2a46f831d861f861
- R06–R10: 17ac301d5e14ed671c963a62b9441585db91e0c2
- R11–R14: f3cb8ffff700c1b33ab31ff80fe43b1448a7ad52
- R15–R18: 677d5a2bd5e305b4e40bda0d2e23cd83002c3c32
- facilities: 620a4914595fb6c5fcc945a6adac205f935b3181
- start: ea886465d9736bf5bdbd11a07bf7ff0211a2295d
- QA/pipeline: d84637a5d3afdc20c8a08893f3ce941872925c36
- native workflow activated: 60b028fdc38f1c3e6470d4d7ae2ff61fee13e877

Local workspace was a partial materialization. Full packed source/native inputs are retained in the repository and restored by CI. Local v012 tree: /workspace/scratch/56a10393eb91/orlando_v012. Do not mistake absence of binary source locally for missing repository inputs.

The final terrain after start grading has SHA-256 `51fdde42715d5494c6e33cd20740fde442ae51f55e4d99fd4567b21f6c4782ad`. Main-course terrain before start grading: `d6bc0695eeecd0ea7d2a74a8d8c86529dd8d748e478a94a393a167e0864ddc5f`.

Next: inspect the run, fix any concrete source/native failure, download the game-candidate and build-evidence artifacts, verify ZIP/PKZ contents and hashes, write v012_build_record.json, and deliver the separate PKZ plus QA/checklist. Native success must never be described as an in-game ride test. Gate/first-lap/reset and material appearance need the user's test.

Office assumption: left of frontage pickup_03 when viewed +Z from pit road toward fence. Start assumption: right turn is T06; merge s493, 4.694 m before it. Both are explicitly shown in facility_start_corrections.png.

