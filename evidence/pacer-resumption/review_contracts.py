"""Admit the reviewed browser-job contracts; reject unrelated source drift."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('typing_check', ROOT / 'typing/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
before = json.loads((ROOT / 'typing/evidence/source-reviewed-duplicates.json').read_text())
after = check.source_hashes()
changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
expected = {'src/riposte/server.py', 'src/riposte/sort_history.py',
            *('src/riposte/static/' + p for p in ('app.js', 'category-sort.js', 'index.html', 'style.css'))}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
check.REVIEWED_SOURCE.write_text(json.dumps(after, indent=2) + '\n')
review = {'owners': sorted(changed), 'signatures': signatures, 'leaf_modules': len(modules),
          'application_files': len(after),
          'review': ['Jobs.start adds explicit read_only metadata; start/close/completion share locks.',
                     'Cancellation drops read-only completion results and progress uses only bounded fields.',
                     'Sort and rule-save commits remain non-cancellable.',
                     'undo_sort adds keyword-only Progress; commit never invokes it.',
                     'Both affected external declarations reflect the runtime signature and instance field.',
                     'Browser uses job receipts, settings revisions and existing authenticated transport.']}
(Path(__file__).parent / 'contract-review.json').write_text(json.dumps(review, indent=2) + '\n')
print(json.dumps(review, indent=2))
