"""Admit only the eight reviewed terminal files; preserve the prior snapshot."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("typing_check", ROOT / "typing/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
previous = json.loads((ROOT / "typing/evidence/source-reviewed-kontext.json").read_text())
current = check.source_hashes()
changed = {path for path in previous.keys() | current.keys() if previous.get(path) != current.get(path)}
expected = {f"src/riposte/terminal/{name}.py" for name in
            ("actions", "app", "controller", "interaction", "keyboard", "paths", "render", "state")}
assert changed == expected, changed ^ expected
issues, signatures, modules = check.check_parity()
assert not issues, issues
check.REVIEWED_SOURCE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed_files": sorted(changed), "signatures": signatures,
                  "leaf_modules": len(modules), "application_files": len(current)}, indent=2))
