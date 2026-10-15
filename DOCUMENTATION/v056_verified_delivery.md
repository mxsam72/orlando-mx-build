# v056 verified native release

[Download OrlandoMX_2026_v056.pkz](https://github.com/mxsam72/orlando-mx-build/releases/download/v056-restored-corners-38665837940/OrlandoMX_2026_v056.pkz) · [Release](https://github.com/mxsam72/orlando-mx-build/releases/tag/v056-restored-corners-38665837940) · [Successful native build](https://github.com/mxsam72/orlando-mx-build/actions/runs/38665837940)

v055 was rejected in game. Its broad landing patch removed up to 1.843 m from T03 and 0.167 m from T12 across the audited widths. Its expanded photographic mask and nearly uniform soil colours obscured the boundary. v056 uses checksum-pinned delivered v054, including the accepted A/B/C layout and start.

All 14 corner grids are exact v054 across a 28 m cross width with RAW bilinear support protected. All 18 visual/physical surface masks, the full-resolution 4K racing photographs/normals, both 8K atlases, original wear blend and normal strength are restored. Only the base soil dry/wet images receive a mild RGB -6/-4/-4 tint, retaining approximately 75% of their original colour separation.

The right-side R03 crown correction changes 840 RAW samples and stops at station 272.0, before the T03 arc at 272.518. Maximum local reduction is 0.484 m. The single centre profile, all corner grids, unrelated jumps, native routes, race files and scenery remain exact v054. The original banked turn entry is preserved; this does not promise a flat runout through the bank.

The official native build passed complete comparisons of all 4,198,401 MAP heights and all 4,198,401 TRH heights against the emitted RAW, then rechecked every corner against v054. Native texture/scenery probes, retained race-file checks, centreline merge and the 13-entry archive CRC gate passed. The published asset digest independently matches the successful native-build log.

Same 14 layers and 48 unique active image payloads as v054. The estimated RGBA8 base-level texture allocation is unchanged at 1,380,188,160 bytes. A separate source-pixel check confirmed the soil tint broke no existing bitmap aliases. These are asset allocation checks, not measured game RAM/VRAM or FPS.

PKZ: **920,759,900 bytes**  
SHA256: `8f491a00c274ba60c82225782983033c8b16df1a094761d9678a4cfc3ed63c25`  
Source/native commit: `c02a8cac8a7ef142969d246fee17fe08340257be`  
Native run: `38665837940`  
Published validation report SHA256: `e0a0e9f63e743e090c6226e784c3a50535f657d6cb1549faf1c4d68f8ef3ba25`

An extra local full-download check could not complete because the local command runner stopped responding. No separate local archive/ground-grid pass is claimed. The official Windows native and archive checks passed, and the release asset's recorded digest matches that validated build.

In-game load, appearance, timing, R03 riding and FPS still require a game test. Source previews are labelled and are not game captures. The menu entry is **Orlando MX 2026 v056**; select it and reset the track.
