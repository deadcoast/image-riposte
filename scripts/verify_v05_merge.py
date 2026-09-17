"""Recheck this selective merge against retained pre-merge hashes and archive bytes.

This is a merge receipt, not a replacement for pytest or the external type suite.
It deliberately fails when a later development change invalidates its snapshots.
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
HERE = ROOT / "evidence/patch-v050"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_report(name: str) -> dict:
    tree = ET.parse(HERE / f"{name}.xml")
    suite = tree.getroot().find("testsuite")
    assert suite is not None
    cases = list(tree.getroot().iter("testcase"))
    failures = []
    for case in cases:
        issue = case.find("failure")
        if issue is None:
            issue = case.find("error")
        if issue is not None:
            failures.append({"test": case.attrib["classname"] + "::" + case.attrib["name"],
                             "kind": issue.tag, "message": issue.attrib.get("message", "")})
    revision = [case for case in cases if case.attrib["classname"] == "tests.test_v05_revision"]
    return {"counts": {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")},
            "revision_cases": len(revision),
            "revision_passed": sum(len(case) == 0 for case in revision),
            "failures": failures,
            "case_ids": sorted(case.attrib["classname"] + "::" + case.attrib["name"] for case in cases)}


def main() -> None:
    decisions = json.loads((HERE / "merge-decisions.json").read_text(encoding="utf-8"))
    before = json.loads((HERE / "checkout-before.json").read_text(encoding="utf-8"))
    archive = ROOT / "packages/RIPOSTE_v0.5.0.zip"
    assert digest(archive) == decisions["incoming_archive_sha256"]
    assert digest(ROOT / decisions["base_archive"]) == decisions["base_archive_sha256"]
    assert not (ROOT / "patch-TODO/RIPOSTE_v0.5.0.zip").exists()
    with zipfile.ZipFile(archive) as incoming, zipfile.ZipFile(ROOT / decisions["base_archive"]) as base:
        assert incoming.testzip() is None
        assert {entry.filename.removeprefix("RIPOSTE/") for entry in incoming.infolist() if not entry.is_dir()} == {entry["path"] for entry in decisions["decisions"]}
        for entry in decisions["decisions"]:
            raw = incoming.read("RIPOSTE/" + entry["path"])
            assert hashlib.sha256(raw).hexdigest() == entry["incoming_sha256"]
            if entry["decision"] == "apply-reviewed-patch-only-delta":
                assert (ROOT / entry["path"]).read_bytes() == raw, entry["path"]
                name = "RIPOSTE/" + entry["path"]
                if entry["before_sha256"] is None:
                    assert name not in base.namelist(), entry["path"]
                else:
                    original = base.read(name).replace(b"\r\n", b"\n")
                    assert entry["before_sha256"] in {
                        hashlib.sha256(original).hexdigest(),
                        hashlib.sha256(original.replace(b"\n", b"\r\n")).hexdigest(),
                    }, f"Patch-only decision did not match the base: {entry['path']}"

    changed = sorted(path for path, value in before.items()
                     if path.startswith(("src/riposte/", "tests/")) and digest(ROOT / path) != value)
    allowed = {entry["path"] for entry in decisions["decisions"]
               if entry["decision"] == "apply-reviewed-patch-only-delta"}
    assert set(changed) <= allowed
    preserved = [path for path in before if path.startswith(("src/riposte/", "tests/")) and path not in changed]
    assert all(digest(ROOT / path) == before[path] for path in preserved)
    assert digest(ROOT / "typing/evidence/source-before.json") == before["typing/evidence/source-before.json"]
    assert (HERE / "index-before.txt").read_bytes() == subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT)

    for path in ("pyproject.toml", "uv.lock"):
        old = tomllib.loads(subprocess.check_output(["git", "show", ":" + path], cwd=ROOT).decode())
        new = tomllib.loads((ROOT / path).read_text(encoding="utf-8"))
        if path == "pyproject.toml":
            assert new["project"]["version"] == "0.5.0"
            old["project"]["version"] = "0.5.0"
        else:
            for package in old["package"]:
                if package["name"] == "riposte-studio":
                    package["version"] = "0.5.0"
        assert old == new, f"Unexpected dependency changes: {path}"

    reviewed = json.loads((ROOT / "typing/evidence/source-reviewed-v050.json").read_text(encoding="utf-8"))
    source = {path.relative_to(ROOT).as_posix(): digest(path)
              for path in (ROOT / "src/riposte").rglob("*") if path.is_file() and "__pycache__" not in path.parts}
    assert source == reviewed and len(source) == 47
    contracts = json.loads((ROOT / "typing/evidence/verification.json").read_text(encoding="utf-8"))
    assert contracts["results"] and all(value is True for value in contracts["results"].values())
    assert contracts["source_files"] == 47 and contracts["source_signatures"] == 313
    baseline = test_report("baseline-full")
    merged = test_report("merged-full")
    assert set(baseline["case_ids"]) <= set(merged["case_ids"])
    baseline.pop("case_ids")
    merged.pop("case_ids")
    assert merged["revision_cases"] == merged["revision_passed"] == 49
    root_audit = json.loads((HERE / "root-mypy.json").read_text(encoding="utf-8"))
    assert root_audit["same_output"]
    assert all(row["exit_code"] == 1 and not row["duplicate_module"] for row in root_audit["results"])
    for row in root_audit["results"]:
        output = (HERE / f"root-mypy-{row['entrypoint']}.txt").read_text(encoding="utf-8")
        assert hashlib.sha256(output.encode("utf-8")).hexdigest() == row["output_sha256"]
    report = {"result": "PASS", "scope": "Selective merge continuity, archive identity and retained execution reports; the full application suite and raw-source typing remain failing.",
              "command": [sys.executable, "scripts/verify_v05_merge.py"],
              "archive": archive.relative_to(ROOT).as_posix(), "archive_sha256": digest(archive),
              "existing_source_files_changed": changed, "source_and_test_files_preserved": len(preserved),
              "git_index_unchanged": True, "dependency_versions_preserved": True,
              "baseline": baseline, "merged": merged, "contracts": contracts,
              "raw_source_audit": root_audit,
              "source_sha256": source,
              "limits": ["Windows organization identity failures are intermittent; before/after failing test IDs differ.",
                         "Preserved backend source and matching failure causes support continuity; test counts alone do not establish it.",
                         "No native POSIX console, optional ML stack, historical wheel or visual acceptance was verified."]}
    (HERE / "merge-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("result", "archive", "archive_sha256", "source_and_test_files_preserved", "git_index_unchanged", "dependency_versions_preserved")}, indent=2))


if __name__ == "__main__":
    main()
