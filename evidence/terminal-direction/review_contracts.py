"""Review the isolated native-key repair without admitting unrelated drift."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("typing_check", ROOT / "typing/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
previous = json.loads((ROOT / "typing/evidence/source-reviewed-sorter-menu.json").read_text())
current = check.source_hashes()
changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
assert changed == {"src/riposte/terminal/keyboard.py"}, changed
issues, signatures, modules = check.check_parity()
assert not issues, issues
check.REVIEWED_SOURCE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed_files": sorted(changed), "signatures": signatures,
                  "leaf_modules": len(modules), "application_files": len(current)}, indent=2))
