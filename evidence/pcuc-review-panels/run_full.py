"""Source-bound native suite; test workspaces must be outside application roots."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sources():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}


before = sources()
parent = Path(tempfile.mkdtemp(prefix="riposte-pcuc-native-"))
command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(parent / "pytest"),
           "--junitxml", str(HERE / "full-native.xml")]
with (HERE / "full-native.txt").open("w", encoding="utf-8") as output:
    result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
after = sources()
(HERE / "full-command.json").write_text(json.dumps({"command": command, "exit_code": result.returncode,
    "sources": before, "source_unchanged": before == after, "temporary_parent": str(parent)}, indent=2) + "\n", encoding="utf-8")
assert before == after
raise SystemExit(result.returncode)
