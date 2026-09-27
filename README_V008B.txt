ORLANDO MX v008b - LOCAL COLOR + TREE FIX

PURPOSE
Creates a separate v008b build from the same known-good v007/v008 geometry.
It does NOT change terrain.raw, track.tht, centerline, race data, or jump geometry.

VISUAL CHANGES
- Dirt hue shifted ~6 degrees away from orange.
- Dirt saturation reduced roughly 53-60% depending on material.
- Dirt brightness reduced roughly 16-24% depending on material.
- Worked dirt made darker/more contrasted than prepared dirt.
- Grass slightly dulled.
- Scenery analysis found 580 individual dense tree meshes. The script removes a deterministic ~30% and varies/scales the survivors to break the continuous oversized canopy wall.

INSTALL
Extract this ZIP directly into the same repository root where BUILD_V008_LOCAL.bat lives.
Allow it to add new files. It should not replace your existing v008 scripts.
Then run BUILD_V008B_LOCAL.bat from Command Prompt.

OUTPUT
12_RELEASE\OrlandoMX_2026_v008b.pkz

SAFETY
The batch first restores exact v007 inputs, re-applies the verified v008 overlay, then performs the v008b visual-only corrections. v007 and v008 PKZs are not overwritten.
