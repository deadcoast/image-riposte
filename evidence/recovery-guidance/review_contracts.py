"""Record a reviewed recovery presentation delta, with unchanged engine authority."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('typing_check', ROOT / 'typing/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
before = json.loads((HERE / 'source-before.json').read_text())
after = check.source_hashes()
changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
expected = {'src/riposte/' + p for p in (
    'errors.py', 'recovery.py', 'server.py', 'static/app.js', 'static/category-sort.js',
    'static/duplicates.js', 'static/index.html', 'static/publish.js', 'static/recovery-catalog.json',
    'static/recovery.js', 'static/style.css', 'terminal/controller.py', 'terminal/interaction.py',
    'terminal/jobs.py', 'terminal/output.py', 'terminal/render.py', 'terminal/reports.py')}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
for name in ('focused-final.xml', 'native.xml'):
    for suite in ET.parse(HERE / name).getroot().findall('testsuite'):
        assert int(suite.attrib['failures']) == int(suite.attrib['errors']) == 0
assert json.loads((HERE / 'browser-live.json').read_text())['result'] == 'PASS'
check.REVIEWED_SOURCE.write_text(json.dumps(after, indent=2) + '\n')
review = {'owners': sorted(changed), 'signatures': signatures, 'leaf_modules': len(modules),
          'application_files': len(after), 'review': [
              'RiposteError sanitizes its code using the existing terminal grammar; machine error envelopes remain code-only.',
              'The typed recovery module and browser loader read the same packaged JSON; unavailable data has bounded safe fallback.',
              'Jobs expose only an allowlisted operation family, never request arguments, paths or exception messages.',
              'Presentation consumers use shared titles/actions and preserve machine codes; informational category states do not affect readiness.',
              'Terminal scrolling and browser persistent notices never retry operations, grant consent or discard category drafts.',
              'Source replacement, history integrity, lease ownership, model computation and category matching implementations are unchanged.',
              'External declarations review new signatures and the recovery record; raw implementation typing remains a separate failing audit.',
          ]}
(HERE / 'contract-review.json').write_text(json.dumps(review, indent=2) + '\n')
print(json.dumps(review, indent=2))
