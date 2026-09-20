"""Record the reviewed research integration and source-derived corpus declarations."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("typing_check", ROOT / "typing/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
previous = json.loads((ROOT / "typing/evidence/source-reviewed-optional-categories.json").read_text())
current = check.source_hashes()
changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
expected = {"src/riposte/" + p for p in (
    "category_corpus.py", "category_sort.py", "category_rules.py", "policy.py", "video.py", "cli.py", "terminal/service.py", "static/app.js", "title_categories.py", "terminal/actions.py",
    "terminal/render.py", "terminal/reports.py", "static/category-sort.js", "static/index.html",
)}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
# Reviewed: typed bounded corpus model, normalized views, graph association and
# stable existing anchors; JSON-native evidence inside version-3 receipts;
# CamelCase rule compatibility; actual-year canonical paths and legacy videos;
# dynamic tree/year filtering and shared preview/discovery reports. Existing
# source identity, explicit consent, float exclusion and recovery remain owned
# by the established transaction engine. No report contract was broadened.
check.REVIEWED_SOURCE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed_files": sorted(changed), "signatures": signatures,
                  "leaf_modules": len(modules), "application_files": len(current)}, indent=2))
