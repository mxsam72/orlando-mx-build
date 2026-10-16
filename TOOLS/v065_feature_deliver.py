"""Check and package the v065 feature photos without changing game assets."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'DOCUMENTATION/v065_feature_cinematics'
OUT = ROOT.parent / 'OrlandoMX-v065-Feature-Photos'
EXPECTED = {
    'terrain.raw': '860350c4c733e5d26939e9e2f40204679ecef302d6e07889f78a849afc8a8fa2',
    'scenery.fbx': '40d8e6ddeacfa0d0c3c9fad454abd2f83acee633fb367e31c8530d8dbafa6e99',
}
SHOTS = [
    ('01_four_vehicles_and_candy', 'The four-vehicle lineup'),
    ('02_chevy_express_and_candy', 'Express and candy sign'),
    ('03_sam_king_ranch', "Sam's Ford King Ranch"),
    ('04_premier_chevy', 'Premier service Chevrolet'),
    ('05_silver_cybertruck', 'Stainless Cybertruck'),
    ('06_pup_memorial_close', 'Pup Whatley memorial'),
    ('07_pup_memorial_pits', 'Remembering Pup in the pits'),
    ('08_crocodile_close', 'The pond resident'),
    ('09_crocodile_pond', 'Crocodile pond'),
    ('10_speedway_golden_hour', 'Speedway in golden light'),
    ('11_tabletop_three_quarter', 'Loam on the tabletop'),
    ('12_berm_golden_hour', 'Golden-hour berm'),
]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/' + name, size)


def main():
    for filename, expected in EXPECTED.items():
        assert sha(ROOT / 'V065_OUTPUT' / filename) == expected, filename
    report = json.loads((SOURCE / 'renders.json').read_text())
    assert report['version'] == 'v065' and not report['in_game_capture']
    assert report['terrain_sha256'] == EXPECTED['terrain.raw']
    assert report['scenery_sha256'] == EXPECTED['scenery.fbx']
    rendered = {row['name']: row for row in report['renders']}
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1800, 1606), (24, 28, 29))
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 18), 'ORLANDO MX  /  v065', font=font(32, True), fill=(247, 242, 232))
    draw.text((25, 62), 'Feature photos  ·  12 originals at 2560 × 1440', font=font(20), fill=(186, 191, 186))
    rows = []
    for index, (name, title) in enumerate(SHOTS):
        record = rendered[name]
        source = SOURCE / record['file']
        assert source.name == name + '.png'
        assert sha(source) == record['sha256'], name
        with Image.open(source) as image:
            image.load()
            assert image.size == (2560, 1440) and image.mode == 'RGB', name
            assert max(hi - lo for lo, hi in image.getextrema()) > 120, name
            thumbnail = image.resize((580, 326), Image.Resampling.LANCZOS)
        target = OUT / ('OrlandoMX_v065_' + name + '.png')
        shutil.copy2(source, target)
        x = 10 + index % 3 * 600
        y = 106 + index // 3 * 366
        sheet.paste(thumbnail, (x, y))
        draw.text((x + 7, y + 335), title, font=font(18), fill=(232, 230, 220))
        rows.append(dict(file=target.name, title=title, size=[2560, 1440], sha256=sha(target), camera=record))
    draw.text((24, 1577), 'Actual v065 assets with cinematic lighting. Source renders; not in-game captures.', font=font(17), fill=(178, 184, 179))
    preview = OUT / 'OrlandoMX_v065_Feature_Preview.jpg'
    sheet.save(preview, quality=95, subsampling=0)
    readme = OUT / 'Readme.txt'
    readme.write_text(
        'Orlando MX v065 - cinematic feature photos\n\n'
        'Twelve clean 2560 x 1440 PNG images, ready to post.\n\n'
        'The four-vehicle lineup, Express and candy board, Ford King Ranch, Premier Chevrolet, '
        'stainless Cybertruck, Pup Whatley memorial, crocodile pond, speedway, tabletop and berm.\n\n'
        'Rendered in Blender Cycles from the released v065 track assets. Lighting, reflections '
        'and depth of field are cinematic presentation settings; these are not MX Bikes game captures. '
        'The cardboard lettering is oriented for these camera views. '
        'The native terrain and scenery files are unchanged.\n', encoding='utf-8')
    proof = OUT / 'Render_Provenance.json'
    proof.write_text(json.dumps(dict(
        version='v065', in_game_capture=False, renderer='Blender Cycles 4.5.3 CPU, AgX',
        presentation_lighting=True, native_assets_unchanged=True,
        terrain_sha256=EXPECTED['terrain.raw'], scenery_sha256=EXPECTED['scenery.fbx'],
        material_validation_sha256=report['material_validation_sha256'], images=rows,
    ), indent=2) + '\n')
    archive = OUT / 'OrlandoMX_v065_Feature_Photos.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=4) as bundle:
        for row in rows:
            bundle.write(OUT / row['file'], row['file'])
        for path in [readme, proof, preview]:
            bundle.write(path, path.name)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None and len(bundle.infolist()) == 15
    result = dict(checks_pass=True, images=rows, preview=str(preview), archive=str(archive),
                  archive_bytes=archive.stat().st_size)
    (ROOT / 'BUILD/v065_feature_delivery.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'images'}, indent=2))


if __name__ == '__main__':
    main()
