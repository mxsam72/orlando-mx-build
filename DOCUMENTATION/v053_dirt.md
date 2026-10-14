# v053 cancelled; v052 remains the approved baseline

On 2026-10-14, after viewing the matched source comparisons, the user cancelled v053 and chose v052's existing dirt colour and appearance.

Future track updates must start from the delivered v052 package and source checkpoint. Do not carry forward v053's warmer palette, grain balance, grooming or local wear changes unless the user requests them again. The earlier proposal below is historical and is not an approved build specification.

The v053 build workflow has been replaced with a cancellation-only workflow in the existing `orlando-v053` concurrency group. It performs no compilation, packaging or publication. The experimental source and previews are preserved for reference.

[Approved v052 download](https://github.com/mxsam72/orlando-mx-build/releases/download/v052-natural-dirt-grass-38537630164/OrlandoMX_2026_v052.pkz)

## Historical experiment (cancelled)

The latest rider video (20261014-1337-19.4778337.mp4) shows soft route-scale dirt detail, olive mottling, weak distinction between compacted and loose soil, regular edges and little local tyre wear. v052's high atlas blend suppresses the fine 4K photographic soil underneath. The source photographs already contain grains and small clods.

v053 keeps those photographic normal maps and their matte alpha 2. The photographs receive a small warm RGB adjustment (+3,-2,-1) and restrained fine-grain contrast. The route atlas has less blend weight so fine soil survives near the rider. Narrower, slightly varied grooves follow the route and jump faces. Curved tyre fragments activate only in corners; interrupted compaction covers landing and short run-out areas. Irregular edge mixing can reduce the dirt mask inside its previous footprint but cannot expand it.

All changes are visual. The exact v052 HMF, its 14 layers, texture dimensions, physical terrain, collision, roads, race/reset files and lighting remain. Exact delivered v052 grass, scene, matte foliage and three isolated legacy-layer trial masks are restored from pinned assets. The native EDF is reused only after its hash matches the successful v052 delivery validation.

Matched rider-height previews showed that the recovered grain looked clearer, while flat-straight furrows needed more definition. Fine virtual grooming gets a further 28% strength on flat straights, with a smaller gain on faces and landings, retaining the same photographic blend and matte finish.

Source checks compare every changed atlas/mask pixel against the previous corridor, verify no expansion of the dirt mask, check photographic grain contrast and matte alpha, and verify longitudinal grooming gradients and local wear activation. Matched CPU previews sample the actual HMF and textures at each pixel's approximate ground footprint. They are source previews, not screenshots from MX Bikes. Native TerrainEd compilation, texture signatures, decoded foliage specular alpha, geometry probes, collision hashes and archive CRC gate publication. Final in-game appearance and FPS still need the user's ride test.
