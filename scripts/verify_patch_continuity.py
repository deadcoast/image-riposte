"""Verify selective-patch provenance after the separately authorized audit repairs.

Keep verify_v05_merge.py and its historical snapshots unchanged. This receipt
checks the chain from the original merge to the reviewed repairs and executes
the terminal regressions against the current application.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "evidence/patch-closure"
HISTORY = ROOT / "evidence/patch-v050"
REPAIRED_SOURCE = {
    "src/riposte/generation.py", "src/riposte/optimizer.py", "src/riposte/organizer.py",
    "src/riposte/publication.py", "src/riposte/runtime_probe.py", "src/riposte/sanitize.py",
    "src/riposte/server.py", "src/riposte/static/app.js", "src/riposte/static/publish.js",
    "src/riposte/terminal/app.py",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_continuity() -> dict:
    """Require exact archive, baseline, reviewed repair and dependency identities."""
    decisions = read(HISTORY / "merge-decisions.json")
    before = read(HISTORY / "checkout-before.json")
    merged = read(HISTORY / "merge-verification.json")
    reviewed = read(ROOT / "typing/evidence/source-reviewed-v050.json")
    repairs = read(ROOT / "evidence/development-repairs/report.json")
    assert merged["source_sha256"] == reviewed, "Original merge snapshot differs"
    assert repairs["authorization"] == "Implement the listed repairs, including source and test changes"
    source = {p.relative_to(ROOT).as_posix(): digest(p)
              for p in (ROOT / "src/riposte").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    assert source == repairs["application"], "Current application differs from reviewed repairs"
    assert source.keys() == reviewed.keys() and len(source) == 47
    changed = {p for p in source if source[p] != reviewed[p]}
    assert changed == REPAIRED_SOURCE, "Unexpected change since selective merge"
    for path, sha256 in repairs["tests_at_report_time"].items():
        assert digest(ROOT / path) == sha256, f"Reviewed test changed: {path}"
    for path, sha256 in repairs["lockfiles"].items():
        assert digest(ROOT / path) == sha256, f"Dependency configuration changed: {path}"

    archive = ROOT / "packages/RIPOSTE_v0.5.0.zip"
    assert digest(archive) == decisions["incoming_archive_sha256"] == merged["archive_sha256"]
    assert digest(ROOT / decisions["base_archive"]) == decisions["base_archive_sha256"]
    assert not (ROOT / "patch-TODO/RIPOSTE_v0.5.0.zip").exists()
    applied = []
    with zipfile.ZipFile(archive) as incoming, zipfile.ZipFile(ROOT / decisions["base_archive"]) as base:
        assert incoming.testzip() is None and base.testzip() is None
        assert {i.filename.removeprefix("RIPOSTE/") for i in incoming.infolist() if not i.is_dir()} == {
            entry["path"] for entry in decisions["decisions"]}
        for entry in decisions["decisions"]:
            path = entry["path"]
            raw = incoming.read("RIPOSTE/" + path)
            assert hashlib.sha256(raw).hexdigest() == entry["incoming_sha256"], path
            assert entry["before_sha256"] == before.get(path), path
            if entry["decision"] != "apply-reviewed-patch-only-delta":
                continue
            applied.append(path)
            if path in reviewed:
                assert reviewed[path] == entry["incoming_sha256"], path
            if path not in REPAIRED_SOURCE:
                assert digest(ROOT / path) == entry["incoming_sha256"], path
            name = "RIPOSTE/" + path
            if entry["before_sha256"] is None:
                assert name not in base.namelist(), path
            else:
                original = base.read(name).replace(b"\r\n", b"\n")
                assert entry["before_sha256"] in {
                    hashlib.sha256(original).hexdigest(),
                    hashlib.sha256(original.replace(b"\n", b"\r\n")).hexdigest(),
                }, path
    for path, sha256 in reviewed.items():
        if path not in applied:
            assert sha256 == before[path], f"Unreviewed original source delta: {path}"
    assert digest(ROOT / "typing/evidence/source-before.json") == before["typing/evidence/source-before.json"]
    # Read the retained pre-merge index's immutable blobs, independent of today's index.
    index = {line.split("\t", 1)[1]: line.split()[1]
             for line in (HISTORY / "index-before.txt").read_text(encoding="utf-8").splitlines()}
    for path in ("pyproject.toml", "uv.lock"):
        old = tomllib.loads(subprocess.check_output(["git", "cat-file", "blob", index[path]], cwd=ROOT).decode())
        current = tomllib.loads((ROOT / path).read_text(encoding="utf-8"))
        if path == "pyproject.toml":
            old["project"]["version"] = "0.5.0"
        else:
            for package in old["package"]:
                if package["name"] == "riposte-studio":
                    package["version"] = "0.5.0"
        assert old == current, f"Unexpected dependency changes: {path}"
    historical = {p.relative_to(ROOT).as_posix(): digest(p)
                  for p in HISTORY.iterdir() if p.is_file()}
    return {"source": source, "authorized_repair_changes": sorted(changed),
            "applied_patch_files": applied, "archive_sha256": digest(archive),
            "dependencies_preserved": True, "historical_evidence": historical,
            "tests": repairs["tests_at_report_time"], "lockfiles": repairs["lockfiles"]}


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    (ROOT / "typing/.cache/patch-closure").mkdir(parents=True, exist_ok=True)
    report = check_continuity()
    baseline = dict(report)
    command = [sys.executable, "-m", "pytest", "tests/test_v05_revision.py",
               "tests/test_v04_terminal_core.py", "tests/test_v04_terminal_host.py",
               "tests/test_v04_product_terminal.py", "tests/test_linear_focus.py", "-q", "-ra",
               "--basetemp", "typing/.cache/patch-closure/pytest",
               "--junitxml=evidence/patch-closure/terminal.xml"]
    with (HERE / "terminal.txt").open("w", encoding="utf-8") as output:
        completed = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=False)
    report["command"] = command
    report["exit_code"] = completed.returncode
    assert completed.returncode == 0, "Terminal regressions failed; inspect terminal.txt"
    suite = ET.parse(HERE / "terminal.xml").getroot().find("testsuite")
    assert suite is not None
    report["terminal_counts"] = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    assert check_continuity() == baseline, "Inputs changed during verification"
    report["result"] = "PASS"
    report["scope"] = "Selective merge continuity, unchanged reviewed repairs and current terminal regressions. Original failed runs remain historical."
    report["verifier_sha256"] = digest(Path(__file__))
    (HERE / "continuity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("result", "terminal_counts", "archive_sha256", "dependencies_preserved")}, indent=2))


if __name__ == "__main__":
    main()
