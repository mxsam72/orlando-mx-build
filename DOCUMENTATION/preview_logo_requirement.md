# Orlando MX Park preview artwork requirement

The user-facing Orlando MX package must use the Orlando MX Park logo artwork for the track-selection preview.

## Source artwork
- Library/source filename: `orlando_mx_park_logo_reference.png`
- Source PNG SHA-256: `8527e10dabbf3000b2eac706662fa5f58212a6ff317bb2718bdeba13e8936383`
- This is the same artwork presentation used for the corrected v015 preview.
- Do not regenerate or reinterpret the logo. Use the source artwork directly.

## MX Bikes target
For version NNN, replace only:
`orlandomx_2026_vNNN/orlandomx_2026_vNNN.tga`

Do not replace:
`orlandomx_2026_vNNN/orlandomx_2026_vNNN_map.tga`

The `_map.tga` remains the course map.

## Presentation used for corrected v017
- TGA canvas: 1024 x 1024 RGB
- Background: white
- Logo scaled proportionally to 944 x 481
- Logo offset: x=40, y=271
- No cropping or logo recreation
- Corrected v017 preview TGA SHA-256: `7902dd97dc15a0384f12c68e63f832ffa23dea6b1a97301ea1b2275e7401bf01`

## Distribution rule
The preview patch is cosmetic only. MAP, TRH, RDF, race files, scenery, physics, and the course-map TGA must remain byte-identical to the native build.

Corrected distributed v017 PKZ SHA-256:
`aee4461812a663f8f7950b9332e716e7dbd7d099e1196dd945c35bb38cf0ced1`

Carry this preview requirement forward to subsequent Orlando MX versions.
