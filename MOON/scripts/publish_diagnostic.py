"""Publish the preserved no-shadow package separately from the shadowed candidate."""
import hashlib, json, os, urllib.error, urllib.parse, zipfile
from native_lighting import BASE_RUN, BASE_COMMIT, DIAGNOSTIC_SHA, restore_base
from publish_test import R, api, upload_files


def main():
    restore_base('map-test')
    report = json.loads((R/'Moon_v002_Diagnostic_Validation.json').read_text())
    pkz = R/'Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz'
    assert hashlib.sha256(pkz.read_bytes()).hexdigest() == report['pkz_sha256'] == DIAGNOSTIC_SHA
    assert pkz.stat().st_size == report['pkz_bytes'] == 75371649
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None
        assert all(name.startswith('taurus_littrow_mx_v002/') for name in z.namelist())
        assert {'taurus_littrow_mx_v002/taurus_littrow_mx_v002'+ext for ext in ['.map','.trh','.rdf','.amb','.ini']} <= set(z.namelist())
    tag = 'moon-v002-diagnostic-'+BASE_RUN
    try:
        release = api('/releases/tags/'+urllib.parse.quote(tag, safe=''))
    except urllib.error.HTTPError as exc:
        if exc.code != 404: raise
        release = api('/releases', dict(tag_name=tag, target_commitish=BASE_COMMIT,
            name='Taurus-Littrow MX v002 — diagnostic, no baked shadows',
            prerelease=True, draft=False, make_latest='false', body=(
                'First native test package for the Moon track around mapped Shorty crater in Taurus-Littrow. '
                'This explicitly labelled diagnostic has BAKED SHADOWS DISABLED. It lets us test loading, the '
                'mapped terrain, pits, route, grip, timing, resets and half-gravity riding while the shadow bake is repaired. '
                'Native geometry placement, all 4,198,401 terrain height samples, material signatures and package '
                'checks passed. Actual game loading and riding have not yet been tested. '
                'Download the PKZ and installation text below. Keep the PKZ intact and use single-player Testing, '
                'Clear weather, with your separately installed compatible Quiet Gravity plugin set to preset=half. '
                'The PKZ does not change gravity or contain the plugin. Do not install alongside another v002 '
                'package: both use internal track ID taurus_littrow_mx_v002. '
                'This is a lighting diagnostic, not the final visual release. No multiplayer validation is claimed. '
                'Compiled assets are preserved from run '+BASE_RUN+'.')))
    assert release['tag_name'] == tag and release['target_commitish'] == BASE_COMMIT
    assert release['prerelease'] and not release['draft']
    upload_files(release, [pkz, pkz.with_suffix('.pkz.sha256'),
                          R/'Moon_v002_Diagnostic_Validation.json', R/'Install_Moon_v002_Diagnostic.txt'])
    delivery = dict(release_url=release['html_url'], pkz_sha256=DIAGNOSTIC_SHA,
                    original_compile_run=BASE_RUN, original_compile_commit=BASE_COMMIT,
                    publication_run=os.environ['GITHUB_RUN_ID'], diagnostic_only=True)
    (R/'v002_diagnostic_delivery.json').write_text(json.dumps(delivery, indent=2)+'\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write('[Download the no-shadow Moon diagnostic]('+release['html_url']+')\n')
    print('MOON_V002_DIAGNOSTIC_RELEASE', release['html_url'], flush=True)


if __name__ == '__main__': main()
