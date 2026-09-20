"""Record the reviewed optional-category semantics without widening contracts."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("typing_check", ROOT / "typing/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
previous = json.loads((ROOT / "typing/evidence/source-reviewed-terminal-polish.json").read_text())
current = check.source_hashes()
changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
expected = {"src/riposte/" + p for p in (
    "category_sort.py", "category_rules.py", "title_categories.py", "terminal/actions.py",
    "terminal/render.py", "terminal/reports.py", "static/category-sort.js", "static/index.html",
)}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
# Existing category/report declarations explicitly expose dynamic dictionaries;
# None is already permitted. No callable signature, schema or required key changes.
# Review: no-match None, unavailable-title status, per-item category_source and
# category counts; preserved stored choices and receipt version 2. Source/rules
# integrity, consent, float pruning and recovery boundaries remain in place.
check.REVIEWED_SOURCE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed_files": sorted(changed), "signatures": signatures,
                  "leaf_modules": len(modules), "application_files": len(current)}, indent=2))
