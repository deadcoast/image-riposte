"""Fresh wheel checks using the existing environment and an isolated install target."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "sort_package_probe", ROOT / "evidence/sort-recovery/check_package.py"
)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.HERE = HERE
probe.INSTALLED = ROOT / "typing/.cache/title-discovery/installed"
probe.WHEEL = ROOT / ".tmp/title-discovery/dist/riposte_studio-0.5.0-py3-none-any.whl"
probe.SDIST = ROOT / ".tmp/title-discovery/dist/riposte_studio-0.5.0.tar.gz"
probe.main()

env = {**os.environ, "PYTHONPATH": str(probe.INSTALLED)}
with tempfile.TemporaryDirectory(prefix="installed-categories-", dir=ROOT / ".tmp/title-discovery") as directory:
    root = Path(directory)
    for name in ("hockey.png", "winter-goalie-practice.mp4", "other.jpg"):
        (root / name).write_bytes(b"Synthetic filename only; no media decode claim.")
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    command = [sys.executable, "-m", "riposte", "--json", "categories", str(root),
               "--category", "Sport=hockey;goalie"]
    result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                            text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["review"]["categories"][0]["count"] == 2
    assert report["counts"]["unmatched_files"] == 1
    assert report["writes"] is False and report["rules_saved"] is False
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    (HERE / "installed-categories.json").write_text(json.dumps({
        "result": "PASS", "scope": "Installed wheel read-only filename command on three synthetic files",
        "report": report, "media_and_state_unchanged": True,
    }, indent=2) + "\n", encoding="utf-8")
print("PASS installed filename category discovery and explicit aliases")
