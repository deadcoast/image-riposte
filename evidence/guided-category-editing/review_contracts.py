"""Review the bounded guided-editor source delta before admitting its snapshot."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('typing_check', ROOT / 'typing/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
before = json.loads((HERE / 'source-before.json').read_text())
after = check.source_hashes()
changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
expected = {'src/riposte/static/' + p for p in ('category-sort.js', 'index.html', 'style.css')}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
assert json.loads((HERE / 'browser-live.json').read_text())['result'] == 'PASS'
assert 'PASS category_sort_browser' in (HERE / 'browser-final.txt').read_text(encoding='utf-8-sig')
check.REVIEWED_SOURCE.write_text(json.dumps(after, indent=2) + '\n')
review = {'owners': sorted(changed), 'signatures': signatures, 'leaf_modules': len(modules),
          'application_files': len(after), 'python_runtime_unchanged': True,
          'review': ['Structured browser fields serialize the existing categories/exclusions/priorities/slugs request arrays.',
                     'The shared Python parser remains authoritative; client errors provide immediate correction hints.',
                     'Assignment maps serialize existing path=slug requests and cannot grant exact-preview consent.',
                     'Explicit save uses the reviewed options and revision, preserving the current conflict boundary.',
                     'Runtime Python signatures, stubs, sorting engine, CLI and terminal source remain unchanged.']}
(HERE / 'contract-review.json').write_text(json.dumps(review, indent=2) + '\n')
print(json.dumps(review, indent=2))
