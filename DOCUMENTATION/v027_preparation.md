# v027 preparation

The user requested on 5 October 2026 that the v026b obstruction correction be
included in v027. The new v027 prompt will define the remainder of its scope.
This branch begins with accepted v026 commit
2275efa8e92a4958ea130acd71bc6ea74ed49591 and preserves its original source files.
No separate v026b release is being pursued.

The latest failed run 37375662360 regenerated and passed the accepted v026
baseline, including scenery SHA256
98dc23a52fc9868a155d47368e10ff5645727033fc98b649cfb9d264cf9cdd90
and terrain SHA256
334f8042e4f2c3f2507e2ace1dea52e1dffa80f2900f89a3c701bdc39296d27f.
It stopped before scenery removal and native compilation because the expected
selection included tree_525 from an older v006 placement fixture. That tree is
not in the canonical v026 corridor candidate set. The older fixture was an
incorrect basis for that extra expected removal.

The corrected list comes from the canonical diagnostics saved alongside this
document: tree_215, tree_222, SOFTCPLAS_marker_53, SOFTCPLAS_marker_55.
The first tree's low canopy and the second tree's trunk/canopy enter the moved
corner. Both markers lie inside the authored track edge at the corner exit and
R11 runout. Selection checks exact names and coordinates. Removing the four
objects deletes eight Geometry/Model records and their incident connections;
retained object properties, topology, texture/material records and axes remain
protected by complete raw-record fingerprints.

The original release-copy failure was a second version substitution that
produced v026bb names. The v027 release builder must perform one substitution
from v026 to v027 and preserve original text bytes/newlines. Check all required
names and exact race/reset/marshal hashes before native compilation. Use the
accepted Windows build environment; a Windows 2022 diagnostic regeneration
failed the protected scenery hash while windows-latest passed it.

TOOLS/v027_release.py now provides that single-substitution support-file copy
with exact race/reset/marshal checks. Its regression uses the actual accepted
v026 PKZ support files; only the menu INI text changes for the v027 identity.

Apply TOOLS/v027_scenery.py to a V027_OUTPUT copy of the accepted V026_OUTPUT
before unrelated v027 changes alter its route/terrain. Then incorporate the new
user prompt and compile with official PiBoSo tools. The new branch has no
automatic v027 build workflow yet. A compiled v027 package and in-game checks
remain pending.

Review footage is sampled every five seconds, with closer samples around
obstructions and suspect transitions.
