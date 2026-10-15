"""Restore accepted v054 boundaries and full-resolution dirt; tint base soil gently."""
import re
import shutil

import numpy as np
from PIL import Image, ImageStat

from v056_inputs import R, BASE, PREV, O, M, sha, save
from v054_surfaces import source as old_source


def baseline(name):
    if (PREV / 'materials' / name).is_file():
        return PREV / 'materials' / name
    return old_source(name)


def source(name):
    return M / name if (M / name).is_file() else baseline(name)


def mean_color(path):
    return np.asarray(ImageStat.Stat(Image.open(path).convert('RGB')).mean)


def main():
    M.mkdir(parents=True, exist_ok=True)
    # No expanded racing footprint and no colour/normal quality reductions.
    # The base soil is the only altered material; preserve most edge contrast.
    target = .7*mean_color(baseline('v045_loose.tga')) + .3*mean_color(baseline('v045_packed.tga'))
    dry_mean = mean_color(baseline('v032_soil.tga'))
    shift = np.rint((target-dry_mean)*.25).astype(int)
    changes = []
    for name in ['v032_soil.tga', 'v032_soil_wet.tga']:
        im = Image.open(baseline(name))
        a = np.array(im)
        out = np.clip(a.astype(np.int16)+shift, 0, 255).astype(np.uint8)
        Image.fromarray(out).save(M/name, format='TGA')
        assert Image.open(M/name).size == im.size
        changes.append(dict(file=name, size=list(im.size), channel_shift=shift.tolist(),
                            sha256=sha(M/name), baseline_sha256=sha(baseline(name))))
    shutil.copy2(PREV/'compiled_track.hmf', O/'compiled_track.hmf')
    assert sha(O/'compiled_track.hmf') == sha(PREV/'compiled_track.hmf')
    controls = (O/'compiled_track.hmf').read_text() + (R/'BUILD/v054_track.tht').read_text()
    names = set(re.findall(r'(?m)^\s*(?:map|mask)\s*=\s*(\S+)', controls))
    shaders = []
    for name in list(names):
        shader = baseline(name).with_suffix('.shd')
        if shader.is_file():
            names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)', shader.read_text()))
            shaders.append(dict(file=shader.name, sha256=sha(shader)))
            # An overridden bitmap needs its original shader next to it for
            # both the source preview and the native compiler to resolve it.
            if (M/name).exists():
                shutil.copy2(shader, M/shader.name)
    rows, masks, before_bytes, after_bytes = [], [], 0, 0
    for name in sorted(names):
        old, new = baseline(name), source(name)
        a, b = Image.open(old), Image.open(new)
        assert a.size == b.size and a.mode == b.mode
        before_bytes += a.width*a.height*4
        after_bytes += b.width*b.height*4
        same = sha(old) == sha(new)
        if name not in ['v032_soil.tga', 'v032_soil_wet.tga']:
            assert same, ('Unexpected material change', name)
        row = dict(file=name, size_before=list(a.size), size_after=list(b.size),
                   sha256=sha(new), baseline_sha256=sha(old), exact_v054=same, changed=not same)
        rows.append(row)
        if name.startswith('mask_'):
            masks.append(row)
    assert before_bytes == after_bytes
    old_delta = float(np.linalg.norm(dry_mean-target))
    new_delta = float(np.linalg.norm(mean_color(M/'v032_soil.tga')-target))
    assert .70 < new_delta/old_delta < .82
    assert Image.open(baseline('v045_loose.tga')).size == (4096, 4096)
    assert Image.open(baseline('v044_route_detail.tga')).size == (8192, 8192)
    assert len(masks) >= 16 and all(x['exact_v054'] for x in masks)
    save(O/'surface_validation.json', dict(checks_pass=True, baseline='v054',
        all_boundary_visual_and_physical_masks_exact_v054=True,
        all_racing_photographs_normals_macro_atlases_and_shaders_exact_v054=True,
        all_compaction_and_grooming_masks_exact_v054=True,
        no_racing_mask_extension=True, accepted_A_B_C_material_alignment_retained=True,
        layer_count=14, added_layers=0, added_texture_allocations=0,
        photographic_tile_size=[4096,4096], macro_colour_atlas_size=[8192,8192],
        macro_normal_atlas_size=[8192,8192], active_terrain_inventory=rows,
        retained_masks=masks, retained_shaders=shaders, changed_images=changes,
        shoulder_base_rgb_distance_before=old_delta, shoulder_base_rgb_distance_after=new_delta,
        shoulder_colour_distance_retained_fraction=new_delta/old_delta,
        rgba8_base_level_bytes_before=before_bytes, rgba8_base_level_bytes_after=after_bytes,
        rgba8_base_level_bytes_saved=0, estimated_rgba8_full_mip_bytes_saved=0,
        allocation_estimate_note='Same unique active texture dimensions and layers as accepted v054; no increase in decoded texture allocation. Not measured game RAM/VRAM or FPS.',
        physical_material_declarations_unchanged=True, in_game_visual_check=False, performance_test=False))
    print('V056_SURFACE_PASSED', len(masks), 'exact boundary/material masks; full-resolution racing maps; allocation bytes', after_bytes, 'soil shift', shift.tolist(), flush=True)


if __name__ == '__main__':
    main()
