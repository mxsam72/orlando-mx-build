# v056 correction

v055 was rejected in game. It removed part of T03 and T12 with an overbroad landing repair and obscured track boundaries with the shoulder blend. This revision starts from checksum-pinned delivered v054.

Every corner, all 18 boundary/material masks, full-resolution racing maps and the A/B/C layout are restored. Only a small right-side R03 crown patch and RGB -6/-4/-4 base-soil tint differ. No new layers or decoded texture allocations versus v054.

Native validation must decode and compare all 4,198,401 MAP/TRH heights, in addition to corner, texture, scenery, race and archive checks. Source previews are not game footage. In-game appearance/riding remain pending.

Run `.github/workflows/build-v056.yml` on `rebuild-v056`. Final download and checksums are published only after native gates pass.
