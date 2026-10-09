# Orlando MX v041

Baseline: actual privately delivered v040, source commit e3c4230687315bd6a4a65470f9115cfe77258c73. Its complete checkpoint and native validation are authenticated before authoring.

Changes: additive native TRKASPH infill between the unmodified road and concrete wall; 63-m-long stadium grandstands, ten rows and three seating sections facing native -X toward the course opposite the entrance; three generic red pickups replaced in source order by blue, purple and green Cybertrucks; twelve-metre photorealistic crocodile in drainage_water_0.

Every retained v040 geometry/model/material/texture record is exact. Terrain, masks, racing, freestyle jump and corrected sign orientation remain exact. No v039 UV fix is repeated. Crocodile artwork is generated wildlife-photo style, not an actual wildlife photograph. The original transparent PNG is retained here. Native opaque RGB is mapped to a silhouette outline with 45 cm front/back separation and exterior-face culling, avoiding transparent-card sorting. Stadium geometry uses solid opaque materials without duplicated faces.

Crocodile tool: built-in image-generation skill. Prompt: Photorealistic full side-profile adult crocodile, snout facing left, detailed natural olive-brown scales and teeth, entire animal visible, soft daylight, transparent background; oversized twelve-metre pond Easter egg, no text, logos or cartoon styling.

Run TOOLS/build_v041.py, then TOOLS/verify_v041_source.py. Use the official Windows workflow in .github/workflows/build-v041.yml for native MAP/TRH compilation and private draft delivery. Do not publish the release. Internal validation does not claim in-game visual or riding testing.

Inherited historical reports retain their named version. The authoritative v041 checks are v041_independent_validation.json and the final official native validation. Only current native probe sets are used; obsolete historical v037 oval vehicle probes are not presented as v041 evidence.
