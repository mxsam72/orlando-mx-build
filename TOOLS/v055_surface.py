"""Match shoulders, reveal photographic soil, retain directional grooming, reduce allocations."""
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageStat
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

from v055_inputs import R, BASE, PREV, O, M, sha, save
from v054_geometry import read, smooth
from v054_surfaces import source as old_source

LEGACY = ['soil', 'prepared', 'worked', 'packed', 'face']


def source(name):
    if (M / name).is_file():
        return M / name
    if (PREV / 'materials' / name).is_file():
        return PREV / 'materials' / name
    return old_source(name)


def baseline(name):
    if (PREV / 'materials' / name).is_file():
        return PREV / 'materials' / name
    return old_source(name)


def tga(a, path):
    Image.fromarray(a).save(path, format='TGA')


def mean_color(path):
    return np.asarray(ImageStat.Stat(Image.open(path).convert('RGB')).mean)


def masks():
    scope_name = 'mask_v046_section.tga'
    im = Image.open(baseline(scope_name))
    a = np.array(im)
    old = a[:, :, 3].astype(float) / 255
    n = len(old)
    dist = distance_transform_edt(old < .98) * 600 / n
    # Same photographic soil on the bare shoulders, with a 3 m soft boundary.
    expanded = smooth((5.0 - dist) / 3.0)
    for name, limit in [('mask_visual_grass.tga', .15), ('mask_v024_pit_roads.tga', .08), ('mask_pits.tga', .08)]:
        guard = np.asarray(Image.open(baseline(name)).getchannel('A').resize((n, n), Image.Resampling.BILINEAR), float) / 255
        expanded *= 1 - smooth(guard / limit)
    new = np.maximum(old, expanded)
    a[:, :, 3] = np.uint8(np.rint(new * 255))
    tga(a, M / scope_name)
    p = np.array(Image.open(baseline('mask_v046_packed.tga')))
    packed = p[:, :, 3].astype(float) / 255
    # No dark continuous lanes: preserve original full-width compaction patches.
    p[:, :, 3] = np.uint8(np.rint(np.clip(packed + np.maximum(new - old, 0) * .28, 0, 1) * 255))
    tga(p, M / 'mask_v046_packed.tga')
    wear = np.array(Image.open(baseline('mask_v046_wear.tga')))
    wear[:, :, 3] = np.uint8(np.rint(wear[:, :, 3].astype(float) * .50))
    tga(wear, M / 'mask_v046_wear.tga')
    assert np.array_equal(a[:, :, :3], np.asarray(im)[:, :, :3])
    return dict(shoulder_added_area_m2=float(np.sum(new - old) * (600 / n)**2),
                maximum_macro_blend=float(wear[:, :, 3].max() / 255),
                original_macro_blend_max=float(Image.open(baseline('mask_v046_wear.tga')).getchannel('A').getextrema()[1] / 255),
                grass_roads_pits_excluded_from_extension=True)


def main():
    M.mkdir(parents=True, exist_ok=True)
    reports = []
    photo_means = {}
    for family in ['loose', 'packed']:
        name = f'v045_{family}.tga'
        im = Image.open(baseline(name)).convert('RGB').resize((2048, 2048), Image.Resampling.LANCZOS)
        a = np.asarray(im, float)
        mean = a.mean((0, 1))
        # Bring grain and clod boundaries back without moving the accepted hue.
        low = np.asarray(im.filter(ImageFilter.GaussianBlur(1.6)), float)
        a = mean + (a - mean) * 1.10 + (a - low) * .16
        tga(np.uint8(np.rint(np.clip(a, 0, 255))), M / name)
        photo_means[family] = mean_color(M / name)
        assert np.max(abs(photo_means[family] - mean)) < .10
        nn = f'v045_{family}_n.tga'
        normal = Image.open(baseline(nn))
        # Alpha is specular data; never premultiply it into RGB during resize.
        rgb = np.asarray(normal.convert('RGB').resize((2048, 2048), Image.Resampling.BOX), float) / 127.5 - 1
        rgb[:, :, :2] *= .40
        rgb /= np.maximum(np.linalg.norm(rgb, axis=2, keepdims=True), 1e-8)
        out = np.empty((2048, 2048, 4), np.uint8)
        out[:, :, :3] = np.uint8(np.rint(np.clip(rgb * 127.5 + 127.5, 0, 255)))
        out[:, :, 3] = 2
        tga(out, M / nn)
    target = photo_means['loose'] * .70 + photo_means['packed'] * .30
    # Correct the older pale/ruddy soil below and beside the photographic skin.
    # Dry means match the racing blend; each wet/dry brightness ratio is retained.
    palette = []
    for family in LEGACY:
        dry_name = f'v032_{family}.tga'
        dry_mean = mean_color(baseline(dry_name))
        for wet in [False, True]:
            name = f'v032_{family}' + ('_wet' if wet else '') + '.tga'
            im = Image.open(baseline(name)).convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)
            a = np.asarray(im, float)
            old_mean = a.mean((0, 1))
            goal = target * np.clip(old_mean / dry_mean, .55, 1.10) if wet else target
            # Neutralise orange/white grain extremes while keeping soil detail.
            delta = a - old_mean
            luma = delta @ np.array([.2126, .7152, .0722])
            result = goal + .72 * luma[:, :, None] + .16 * (delta - luma[:, :, None])
            tga(np.uint8(np.rint(np.clip(result, 0, 255))), M / name)
            if not wet:
                new_mean = mean_color(M / name)
                assert np.max(abs(new_mean - target)) < .25
                palette.append(dict(file=name, mean_rgb_before=dry_mean.tolist(), mean_rgb_after=new_mean.tolist()))
        name = f'v032_{family}_n.tga'
        normal = Image.open(baseline(name))
        if normal.width > 1024:
            rgb = np.asarray(normal.convert('RGB').resize((1024, 1024), Image.Resampling.BOX), float) / 127.5 - 1
            rgb /= np.maximum(np.linalg.norm(rgb, axis=2, keepdims=True), 1e-8)
            out = np.empty((1024, 1024, 4), np.uint8)
            out[:, :, :3] = np.uint8(np.rint(np.clip(rgb * 127.5 + 127.5, 0, 255)))
            out[:, :, 3] = 2
            tga(out, M / name)
    # Low-frequency colour needs 4K; keep the route-oriented normal atlas at 8K.
    name = 'v044_route_detail.tga'
    Image.open(baseline(name)).convert('RGB').resize((4096, 4096), Image.Resampling.BOX).save(M / name, format='TGA')
    name = 'v044_route_detail_n.tga'
    im = Image.open(baseline(name))
    out = np.array(im)
    for row in range(0, im.height, 128):
        v = out[row:row+128, :, :3].astype(float) / 127.5 - 1
        v[:, :, :2] *= 1.65
        v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-8)
        out[row:row+128, :, :3] = np.uint8(np.rint(np.clip(v * 127.5 + 127.5, 0, 255)))
    assert np.all(out[:, :, 3] == 2)
    tga(out, M / name)
    del out
    mask_report = masks()
    (O / 'compiled_track.hmf').write_text((PREV / 'compiled_track.hmf').read_text())
    assert sha(O / 'compiled_track.hmf') == sha(PREV / 'compiled_track.hmf')
    # Inventory every unique active terrain colour/normal/mask, including frames.
    hmf = (O / 'compiled_track.hmf').read_text()
    names = set(re.findall(r'(?m)^\s*(?:map|mask)\s*=\s*(\S+)', hmf))
    for name in list(names):
        shader = baseline(name).with_suffix('.shd')
        if shader.exists():
            names.update(re.findall(r'(?m)^\s*map\s*=\s*(\S+)', shader.read_text()))
    before_rgba, after_rgba = 0, 0
    texture_rows = []
    for name in sorted(names):
        a = Image.open(baseline(name))
        b = Image.open(source(name))
        before_rgba += a.width * a.height * 4
        after_rgba += b.width * b.height * 4
        texture_rows.append(dict(file=name, size_before=list(a.size), size_after=list(b.size),
                         sha256=sha(source(name)), changed=sha(source(name)) != sha(baseline(name))))
    assert after_rgba < before_rgba
    assert {x['file'] for x in texture_rows} == names
    for p in sorted(M.iterdir()):
        reports.append(dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p), size=list(Image.open(p).size)))
    photo_delta = float(np.linalg.norm(target - mean_color(baseline('v032_soil.tga'))))
    new_delta = float(np.linalg.norm(target - mean_color(M / 'v032_soil.tga')))
    assert new_delta < photo_delta * .05
    save(O / 'surface_validation.json', dict(checks_pass=True, baseline='v054',
         accepted_racing_photo_mean_hue_preserved=True, racing_target_mean_rgb=target.tolist(),
         shoulder_base_rgb_distance_before=photo_delta, shoulder_base_rgb_distance_after=new_delta,
         shoulder_palette=palette, blend=mask_report, layer_count=14, added_layers=0,
         added_texture_allocations=0, main_photographs_retained_with_detail_contrast=True,
         macro_colour_atlas_size=[4096, 4096], macro_normal_atlas_size=[8192, 8192],
         route_oriented_grooming_retained=True, normal_specular_alpha=2,
         legacy_colour_texture_size=[1024, 1024], photographic_tile_size=[2048, 2048],
         active_terrain_inventory=texture_rows, changed_images=reports,
         rgba8_base_level_bytes_before=before_rgba, rgba8_base_level_bytes_after=after_rgba,
         rgba8_base_level_bytes_saved=before_rgba-after_rgba,
         estimated_rgba8_full_mip_bytes_saved=(before_rgba-after_rgba)*4//3,
         allocation_estimate_note='Unique active texture dimensions at RGBA8, with optional full mip pyramid. Not measured process RAM or VRAM.',
         physical_material_declarations_unchanged=True, in_game_visual_check=False, performance_test=False))
    print('V055_SURFACE_PASSED', 'base RGBA8 bytes saved:', before_rgba-after_rgba, 'shoulder colour distance:', photo_delta, '->', new_delta, flush=True)


if __name__ == '__main__':
    main()
