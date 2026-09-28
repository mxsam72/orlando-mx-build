# v010 implemented changes and remaining work

This is a video-guided construction candidate. Dimensions are authoring estimates, not surveyed Orlando measurements. P01–P14 refers to the supplied real/test-video sync in V010_SOURCE/review_section_sync.json. Native compilation and riding status are recorded separately in v010_status.md.

## Facilities and first lap

- Grid/native shared gate moves to (416,184), facing +Z, to the right of the spectator frontage in the user’s design orientation. The 24-stall count and 1.5 m spacing retain the existing capacity.
- Independent 115.9 m start centerline curves outside T01 into T05 at main station 455 with matching tangent. Apron is level across all stalls.
- A local opening through the outer T05 entry bank avoids a hump across the start route. The main centerline and inside entry remain at the main-terrain elevations; the outside line changes locally to form the junction.
- Start/off/grass/racing masks retire the old race-start connector and define the new lane. Normal-lap reset boundaries remain station-compatible.
- Two start-only checkpoints cover the connector; T05–T14 are configured Both; T01–T04 remain normal-lap checkpoints. Existing finish, split lines, pits and pit boards are preserved. Grid and 30-second board move together. Native runtime behavior needs a real start/reset test.
- Fence meshes move outside the T14–R01–T01 frontage. A former fence opening remains a pedestrian gap. Start-lane tree/stake obstructions are removed; fixed-building conflicts fail the build.

## Jump profiles

Dimensions below are metres. Face/landing are profile lengths along the route; height is the added recipe crest height, not total ground elevation. Actual grades are measured from the encoded terrain centerline; 0.40 means 40% grade.

| ID | Height old → new | Face old → new | Rollover old → new | Landing old → new | Actual face grade old → new |
|---|---:|---:|---:|---:|---:|
| R01 | 2.65 → 2.65 | 17.00 → 15.50 | 3.80 → 2.30 | 22.50 → 21.00 | 0.232 → 0.273 |
| R02 | 1.15 → 1.40 | 10.50 → 10.20 | 4.00 → 1.80 | 16.00 → 13.00 | 0.140 → 0.207 |
| R03 | 0.85 → 1.50 | 10.00 → 9.00 | 4.60 → 1.60 | 13.50 → 12.50 | 0.162 → 0.255 |
| R04 | 0.90 → 0.90 | 11.50 → 11.50 | 4.20 → 3.70 | 15.00 → 14.50 | 0.161 → 0.159 |
| R05 | 1.70 → 1.85 | 14.00 → 12.70 | 4.00 → 2.00 | 19.50 → 17.50 | 0.173 → 0.231 |
| R06 | 0.48 → 0.48 | 7.50 → 7.50 | 3.40 → 3.40 | 10.50 → 10.50 | 0.160 → 0.126 |
| R07 | 2.45 → 2.70 | 13.50 → 11.20 | 3.00 → 1.65 | 18.50 → 18.00 | 0.289 → 0.364 |
| R08 | 0.70 → 0.70 | 9.50 → 9.50 | 4.50 → 4.00 | 12.00 → 12.00 | 0.123 → 0.103 |
| R09 | 1.05 → 1.40 | 12.00 → 10.80 | 4.00 → 1.90 | 16.00 → 13.00 | 0.113 → 0.198 |
| R10 | 3.05 → 3.20 | 16.50 → 13.40 | 3.30 → 1.80 | 22.00 → 21.00 | 0.273 → 0.351 |
| R11 | 0.65 → 0.65 | 8.00 → 8.00 | 3.60 → 3.30 | 10.50 → 10.50 | 0.111 → 0.132 |
| R12 | 1.45 → 1.60 | 11.50 → 10.50 | 3.50 → 1.90 | 15.00 → 14.00 | 0.183 → 0.236 |
| R13 | 0.70 → 0.70 | 10.00 → 10.00 | 4.20 → 4.20 | 12.50 → 12.50 | 0.079 → 0.088 |
| R14 | 3.55 → 3.65 | 16.00 → 13.00 | 3.40 → 1.60 | 24.00 → 22.00 | 0.325 → 0.417 |
| R15 | 0.80 → 0.80 | 10.50 → 10.50 | 4.30 → 3.50 | 12.50 → 12.50 | 0.119 → 0.120 |
| R16 | 2.55 → 2.65 | 15.00 → 13.00 | 3.70 → 1.90 | 22.00 → 20.00 | 0.241 → 0.319 |
| R17 | 0.85 → 0.85 | 12.50 → 12.50 | 4.80 → 4.20 | 15.50 → 14.00 | 0.124 → 0.114 |
| R18 | 2.15 → 2.25 | 16.50 → 14.20 | 4.00 → 2.30 | 22.00 → 20.00 | 0.201 → 0.258 |

R13 dimensions are retained pending clarification of the pre-signature disturbance. EX1 before T02 and EX2 after R14 are disabled provisional records, not added obstacles. R07/R10/R14 use a different face progression from the low transitions.

## Corners and surface

All 14 turns now have independently parameterized entry load, apex offset, exit load, pocket depth and two drifting rut paths. Larger carved pockets and supported banks are concentrated at T01, T03, T05, T09 and T10. The v009 full-lap repeating waves and straight twin grooves are removed from the new layer. The legacy v006 corner-rut recipe is compensated before adding the authored paths. Local braking/drive relief remains near turn entries/exits.

Main-loop X/Z alignment and native station IDs are unchanged. This pass improves section cross-sections and longitudinal profiles; it does not claim that the plan-view radii now match measured IRL corners. The old satellite was not used to redraw current jumps.

## Physical section implementation ledger

| Section | Implemented in this candidate | Remaining |
|---|---|---|
| P01 | R01 face/crest/runout; correct spectator frontage | Ride silhouette/landing check; pole/shelter detailing |
| P02 | T01 pocket, support and separate rut paths | Assess local turn radius/exit heading in game |
| P03 | Distinct R02 and R03 built faces; T02 shaping | Resolve EX1 and sequence spacing |
| P04 | Carved T03, modest R04, differentiated T04 | Confirm continuous climbing transition |
| P05 | R05 profile, T05 lines and start-lane junction | Test normal entry and 24-rider start convergence |
| P06 | Small R06 retained; T06 exit support; stronger R07 face | Landing/braking setup into T07 |
| P07 | Separate T07/T08 load envelopes; subordinate R08 | Verify right-left spacing and reveal of R09 |
| P08 | Stronger distinct R09/R10 faces and trough | Test unload/settle rhythm and landing approach |
| P09 | T09 pocket, supported wall and drifting lines | In-game rut depth/support check |
| P10 | R11/R12 differentiation and T10 right wall | Validate crest phases and signature setup |
| P11 | R14 progressive face/crest/landing; R13 held | EX2 form/station and full signature-complex spacing |
| P12 | T11 line support; small R15 and larger R16 | Close vegetation edge and ride comparison |
| P13 | Different T12/T13 banks, pockets and release | Local plan-view corrections if comparison supports them |
| P14 | R17/R18 profile distinction; T14 release; correct fence frontage | Landing-to-turn setup and seam ride check |

## Required ride evidence

1. Race start: outermost and central stalls, gate drop, entire start lane, T05 convergence, first finish crossing.
2. One complete timed normal lap: checkpoints and splits must work without false penalties.
3. Short/long resets on the start straight, merge, T05 and normal-lap approaches.
4. Full comparison lap using the P01–P14 anchors. Judge approach, lip, landing, corner entry/apex/exit; retimed review footage is not a speed or jump-distance measurement.
5. Confirm whether real 0:23–0:24 is a separate mound or raised T02 entry, and define the smaller rise at 1:38–1:40 after the signature landing.
