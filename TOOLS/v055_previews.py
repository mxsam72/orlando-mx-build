"""Matched terrain/material source previews; not game captures."""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from v055_inputs import R, PREV, O, sha, save
from v055_geometry import cross_points
from v055_surface import baseline, source as current_source
from v054_geometry import read
from v054_previews import Terrain
import v049_previews as render

OUT = R / 'BUILD/v055_review'
CURRENT = 'v054'


def source(name, version):
    return current_source(name) if CURRENT == 'v055' else baseline(name)


def main():
    global CURRENT
    OUT.mkdir(parents=True, exist_ok=True)
    q = dict(np.load(O / 'route.npz'))['q']
    before, after = Terrain(PREV / 'terrain.raw'), Terrain(O / 'terrain.raw')
    render.OUT = OUT
    render.source = source
    rows = []
    shots = [('table_single_landing', (228., 241., 275., 308.), 254., 0., 2.0, 278., 0., .7),
             ('landing_cross_width', (228., 241., 275., 308.), 279., -13., 4.5, 269., 0., .5),
             ('racing_soil_and_shoulders', (281., 159., 366., 213.), 8., 0., 1.8, 38., 0., .5)]
    for label, box, es, el, eh, ts, tl, th in shots:
        eye2 = cross_points(q, np.array([es]), np.array([el]))[0]
        target2 = cross_points(q, np.array([ts]), np.array([tl]))[0]
        eye = [*eye2, float(before.ground(eye2[None, 0], eye2[None, 1])[0]) + eh]
        target = [*target2, float(after.ground(target2[None, 0], target2[None, 1])[0]) + th]
        frames = []
        for version, sample in [('v054', before), ('v055', after)]:
            CURRENT = version
            render.O = O if version == 'v055' else PREV
            render.BOX = box
            colors, normals = render.composite('v049', n=1500)
            path = render.render(version, label, colors, normals, sample, eye, target, width=1280, height=800)
            frames.append(Image.open(path).copy())
            rows.append(dict(file=path.name, sha256=sha(path), source_only=True, box_xz_m=list(box), eye_xyz=eye, target_xyz=target))
        sheet = Image.new('RGB', (2560, 800))
        sheet.paste(frames[0], (0, 0))
        sheet.paste(frames[1], (1280, 0))
        sheet.save(OUT / ('comparison_' + label + '.jpg'), quality=94)
    # A close footprint resolves the photographic detail that a large world
    # atlas preview would otherwise blur away before the camera samples it.
    point = cross_points(q, np.array([68.]), np.array([0.]))[0]
    render.BOX = (point[0]-4, point[1]-4, point[0]+4, point[1]+4)
    close_frames, energy = [], []
    for version in ['v054', 'v055']:
        CURRENT = version
        render.O = O if version == 'v055' else PREV
        colors, normals = render.composite('v049', n=1800)
        luminance = colors @ np.array([.2126, .7152, .0722])
        energy.append(float(np.std(luminance - gaussian_filter(luminance, 3))))
        im = Image.fromarray(colors)
        ddraw = ImageDraw.Draw(im)
        ddraw.rectangle((0, 0, 1800, 44), fill=(22, 25, 29))
        ddraw.text((15, 11), version + ' close photographic soil detail — source, not game footage', font=render.font(22), fill='white')
        close_frames.append(im)
    close = Image.new('RGB', (3600, 1800))
    close.paste(close_frames[0], (0, 0))
    close.paste(close_frames[1], (1800, 0))
    close.save(OUT / 'comparison_soil_close_detail.jpg', quality=96)
    assert energy[1] > energy[0] * 1.5, ('Fine photographic detail did not improve', energy)
    d = dict(np.load(O / 'landing_sections.npz'))
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, key, title in zip(axes, ['before', 'after'], ['v054: inherited right-side rise', 'v055: level landing and smooth runout']):
        for lat in [-5, 0, 5]:
            i = np.argmin(abs(d['lat'] - lat))
            ax.plot(d['s'], d[key][i], label=f'Lateral {lat:+g} m')
        ax.set_title(title)
        ax.set_xlabel('Authored route station (m)')
        ax.grid(alpha=.2)
        ax.legend()
    axes[0].set_ylabel('Ground elevation (m)')
    fig.suptitle('R03 table-single landing: independently sampled emitted RAW heights')
    fig.tight_layout()
    fig.savefig(OUT / 'landing_sections.png', dpi=150)
    plt.close(fig)
    save(OUT / 'manifest.json', dict(version='v055', source_only=True, in_game_captures=False,
        matched_cameras_and_light=True, scenery_omitted=True, renders=rows,
        photographic_fine_detail_RMS_before=energy[0], photographic_fine_detail_RMS_after=energy[1],
        photographic_fine_detail_RMS_gain=energy[1]/energy[0],
        source_terrain_sha256=sha(O / 'terrain.raw'), surface_validation_sha256=sha(O / 'surface_validation.json')))
    print('V055_MATCHED_SOURCE_PREVIEWS_READY', flush=True)


if __name__ == '__main__':
    main()
