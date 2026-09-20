"""Check consumers against actual source, retaining imported-module diagnostics."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / ".tmp/source-typing/consumers"


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    for name in ("consumers", "rejected"):
        (WORK / f"{name}.py").write_bytes((HERE / f"{name}.py.txt").read_bytes())
    command = [sys.executable, "-m", "mypy", "--config-file", "typing/mypy-source.ini",
               "--python-version", "3.13", str(WORK / "consumers.py"), str(WORK / "rejected.py"), str(ROOT / "src/riposte")]
    result = subprocess.run(command, cwd=ROOT, env={**os.environ, "MYPYPATH": str(ROOT / "src")},
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    (HERE / "consumers.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    expected = {(number, match[1]) for number, line in enumerate((WORK / "rejected.py").read_text().splitlines(), 1)
                if (match := re.search(r"# error: ([a-z-]+)", line))}
    errors = []
    for line in result.stdout.splitlines():
        match = re.match(r"(.+?):(\d+):\d+: error: .*?  \[([^]]+)\]$", line)
        if match and Path(match[1]).name in {"consumers.py", "rejected.py"}:
            errors.append((Path(match[1]).name, int(match[2]), match[3]))
    assert result.returncode == 1, result.stderr
    assert not any(row[0] == "consumers.py" for row in errors), errors
    assert {(n, code) for name, n, code in errors if name == "rejected.py"} == expected, errors
    assert len(errors) == len(expected) == 9, errors
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    return {"result": "PASS", "command": command, "exit_code": result.returncode, "positive_errors": 0,
            "expected_negative_errors": len(expected), "exact_lines_and_codes": True, "sources": sources,
            "scope": "Real source consumers with normal import following and unchanged strict configuration; imported source debt is retained in consumers.txt and remains separately failing."}


if __name__ == "__main__":
    (HERE / "consumers.json").write_text(json.dumps(main(), indent=2) + "\n", encoding="utf-8")
