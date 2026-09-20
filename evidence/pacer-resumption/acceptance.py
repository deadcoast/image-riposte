"""Recheck execution/history evidence and prepare reviewed manual PACER reports.

The decisions file is an explicit human-readable engineering review, not a test
oracle. This script checks its supporting executions and binds it to current
requirements; actual acceptance still uses PACER verify with a fresh task receipt.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from verify import ROOT, HERE, read, digest, verify


def history():
    patch = ROOT/'evidence/patch-v050'
    decisions = read(patch/'merge-decisions.json')
    before = read(patch/'checkout-before.json')
    merged = read(patch/'merge-verification.json')
    source = read(ROOT/'typing/evidence/source-reviewed-v050.json')
    closure = read(ROOT/'evidence/patch-closure/continuity.json')
    assert merged['source_sha256'] == source and len(source) == 47
    assert all(digest(ROOT/p) == sha for p,sha in closure['historical_evidence'].items())
    assert digest(ROOT/'packages/RIPOSTE_v0.5.0.zip') == decisions['incoming_archive_sha256'] == merged['archive_sha256']
    assert digest(ROOT/decisions['base_archive']) == decisions['base_archive_sha256']
    applied = set()
    with zipfile.ZipFile(ROOT/'packages/RIPOSTE_v0.5.0.zip') as incoming, zipfile.ZipFile(ROOT/decisions['base_archive']) as base:
        assert incoming.testzip() is None and base.testzip() is None
        assert {i.filename.removeprefix('RIPOSTE/') for i in incoming.infolist() if not i.is_dir()} == {e['path'] for e in decisions['decisions']}
        for item in decisions['decisions']:
            name = item['path']
            assert hashlib.sha256(incoming.read('RIPOSTE/'+name)).hexdigest() == item['incoming_sha256']
            assert item['before_sha256'] == before.get(name)
            if item['decision'] != 'apply-reviewed-patch-only-delta': continue
            applied.add(name)
            if name in source: assert source[name] == item['incoming_sha256']
            if item['before_sha256'] is None: assert 'RIPOSTE/'+name not in base.namelist()
            else:
                raw = base.read('RIPOSTE/'+name).replace(b'\r\n',b'\n')
                assert item['before_sha256'] in {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()}
    assert all(sha == before[p] for p,sha in source.items() if p not in applied)
    assert digest(ROOT/'typing/evidence/source-before.json') == before['typing/evidence/source-before.json']
    assert all(digest(ROOT/p) == sha for p,sha in closure['lockfiles'].items() if p != 'pyproject.toml')
    # The later menu terminology repair changed the package description. Compare
    # dependency declarations to the retained pre-merge Git blob, not prose bytes.
    index = {line.split('\t',1)[1]:line.split()[1] for line in (patch/'index-before.txt').read_text().splitlines()}
    old_project = tomllib.loads(subprocess.check_output(['git','cat-file','blob',index['pyproject.toml']],cwd=ROOT).decode())
    current_project = tomllib.loads((ROOT/'pyproject.toml').read_text())
    for key in ('dependencies','optional-dependencies','requires-python','scripts'):
        assert old_project['project'][key] == current_project['project'][key], key
    assert old_project['build-system'] == current_project['build-system']
    review = read(ROOT/'evidence/development-review-2026-09-18/review.json')
    assert set(review['groups']) == {'1','2','3','4'} and len(review['findings']) == 16
    assert review['sources'] == read(ROOT/'typing/evidence/source-reviewed-category-sort.json')
    return {'selective_patch':'PASS: retained archives, decisions, source snapshot and dependency inputs',
            'identification':'PASS: four lists and 16 findings with original source identity',
            'limits':'Historical events are not reapplied over later authorized development.'}


def prepare(pacer_source):
    sys.path.insert(0, str(pacer_source))
    from pacer_mcp.service import Service
    result = verify(packages=True)
    historical = history()
    inventory = read(ROOT/'typing/evidence/pacer-inventory.json')
    assert inventory['result'] == 'PASS', inventory['issues']
    assert read(HERE/'entries.json')['start_linear']['exit_code'] == 0
    cases = list(ET.parse(HERE/'suite.xml').getroot().iter('testcase'))
    decisions = read(HERE/'decisions.json')
    # Evidence bindings legitimately exceed the standard csv reader's 128 KiB
    # field default. Bound parsing by the actual local register sizes.
    csv.field_size_limit(max(csv.field_size_limit(), *(p.stat().st_size for p in
        (ROOT/'organism.PACER.csv', ROOT/'overlord.PACER.csv'))))
    with (ROOT/'organism.PACER.csv').open(encoding='utf-8-sig',newline='') as f: requirements = list(csv.DictReader(f))
    with (ROOT/'overlord.PACER.csv').open(encoding='utf-8-sig',newline='') as f: assets = list(csv.DictReader(f))
    assert set(decisions) == {r['ID'] for r in requirements}
    ids = {r['Path']:r['ID'] for r in assets if r['AssetType']=='FILE'}
    next_id = max(int(r['ID'].split('-')[1]) for r in assets)+1
    operations = []
    service = Service(ROOT)
    for row in requirements:
        decision = decisions[row['ID']]
        coverage = {}
        for module in decision['tests']:
            selected = [c for c in cases if c.get('classname') == 'tests.'+module]
            assert selected, module
            assert not any(c.find('failure') is not None or c.find('error') is not None for c in selected), module
            coverage[module] = {'passed':sum(c.find('skipped') is None for c in selected), 'skipped':sum(c.find('skipped') is not None for c in selected)}
        observed = service.evaluate(row['ID'])
        assert all(v is not None for v in observed['sources'].values())
        report = {'requirement':row['ID'], 'meaning':observed['meaning'], 'sources':observed['sources'],
                  'result':'PASS', 'command':['.venv/Scripts/python.exe evidence/pacer-resumption/verify.py --packages',
                    '.venv/Scripts/python.exe evidence/pacer-resumption/acceptance.py --pacer-source <installed PACER src>',
                    '.venv/Scripts/python.exe -m pytest -q -k "not browser_native and not native_browser and not browser_review_in_real_chromium"',
                    '.venv/Scripts/python.exe -m pytest -q -k "browser_native or native_browser or browser_review_in_real_chromium"',
                    'uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py'],
                  'review':decision['review'], 'test_modules':coverage, 'historical':historical,
                  'limits':result['limits'], 'raw_source_typing':result['source_typing']}
        path = f'evidence/pacer-resumption/{row["ID"]}.json'
        (ROOT/path).write_text(json.dumps(report,indent=2)+'\n')
        artifact = ids.get(path)
        if artifact is None:
            artifact = f'OVR-{next_id}'; next_id += 1
            operations.append({'op':'add','register':'overlord','row':{'ID':artifact,'AssetType':'FILE','Path':path,
                'Purpose':'Reviewed exact-requirement evidence for '+row['ID']+'; historical acceptance retained', 'Tags':'#acceptance #pacer-resumption'}})
        operations.append({'op':'verify','id':row['ID'],'artifact':artifact,
                           'evidence':'2026-09-20 reviewed current source and exact scope: '+decision['review']+' Evidence: '+path})
    (HERE/'acceptance-operations.json').write_text(json.dumps(operations,indent=2)+'\n')
    (HERE/'history.json').write_text(json.dumps(historical,indent=2)+'\n')
    print(json.dumps({'reports':len(decisions),'operations':len(operations),'history':historical}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pacer-source',type=Path,required=True)
    args = parser.parse_args()
    prepare(args.pacer_source)
