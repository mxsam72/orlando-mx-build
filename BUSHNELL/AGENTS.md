# Bushnell project instructions

- Bushnell work belongs on `bushnell-v001`, under `BUSHNELL/`; its workflow is `.github/workflows/bushnell-v001-source.yml`.
- Preserve the approved layout in `source/approved_layout.json`. Changes to the accepted route must be explicit and versioned.
- Use `references/videos.json` for the eight original clips, in order. Camera excursions alongside jumps are reference viewpoints, not mandatory track bends.
- Keep measured, visually inferred, user-confirmed, and provisional dimensions distinguishable. Unknown jump metrics remain null until authored with their evidence or estimate status.
- Use standard game physics. Do not copy Moon gravity hooks, presets, lunar terrain or Orlando track geometry into this project.
- All generated source, previews, validation and future release files must stay within `BUSHNELL/`, with `BushnellMX` names. Raw original videos stay outside Git.
- Run `python -m unittest discover -s BUSHNELL/tests -v` and `python BUSHNELL/scripts/build_source.py` after changing the authoring pipeline.
- Source generation is separate from native compilation. Never label a package installable until its own native MAP/TRH, race data and staging have been built and validated.
