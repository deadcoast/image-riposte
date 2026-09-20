"""Check retained PAC-029 evidence; --record captures, --inventory only proposes.

This verifier does not execute runtime tests or write the frozen PACER registers.
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_counts(name: str):
    suites = ET.parse(HERE / name).getroot().findall("testsuite")
    counts = {key: sum(int(s.attrib[key]) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - sum(counts[k] for k in ("failures", "errors", "skipped"))
    return counts


def capture():
    spec = importlib.util.spec_from_file_location("review_baseline", ROOT / "evidence/milestone-reconciliation-2026-09-18/verify.py")
    assert spec and spec.loader
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    manifest = baseline.manifest()
    assert manifest == read(ROOT / "RELEASE-MANIFEST.json")
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in baseline.source_files()}
    previous = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")
    frozen = previous["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    assert digest(ROOT / manifest["historical_manifest"]) == previous["historical_manifest"]["sha256"]
    changed = sorted(p for p in sources if sources[p] != previous["application_sources"].get(p))
    assert changed == ["src/riposte/locking.py", "src/riposte/organizer.py", "src/riposte/store.py"]
    assert set(previous["application_sources"]) <= set(sources)
    assert sources == read(ROOT / "typing/evidence/source-reviewed-workspace-lease.json")
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert sources == raw["sources"] and raw["exit_code"] == 1
    assert "Found 1102 errors in 37 files (checked 50 source files)" in (HERE / "raw-source.txt").read_text()
    raw_lines = (HERE / "raw-source.txt").read_text().splitlines()
    assert raw_lines[0].startswith("warning: `VIRTUAL_ENV=.venv` does not match the project environment path")
    assert raw_lines[1:] == (ROOT / "typing/evidence/source-current.txt").read_text().splitlines()
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (57, 393, 47)
    full, final = test_counts("full-native.xml"), test_counts("final.xml")
    assert full == dict(tests=1094, failures=0, errors=0, skipped=8, passed=1086)
    assert final == dict(tests=53, failures=0, errors=0, skipped=0, passed=53)
    first_sources = read(HERE / "raw-source-first-command.json")["sources"]
    assert sorted(p for p in sources if sources[p] != first_sources[p]) == ["src/riposte/locking.py"]
    package, posix = read(HERE / "package.json"), read(HERE / "posix.json")
    assert package["result"] == posix["result"] == "PASS"
    assert package["version"] == baseline.version() == "0.5.0" and package["application_files"] == 57
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/workspace-lease/dist" / name) == value
    pacer = read(HERE / "pacer-validation.json")
    assert pacer["valid"] and pacer["revision"] == "09463d2ffc947c0d5c06aa0bc797a42ba097678846d6f4d1f40abb3ed93d7fd5"
    excluded = {"acceptance.json", "deferred-inventory.json", "deferred-operations.json", "inventory-output.txt"}
    evidence = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(HERE.rglob("*"))
                if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts}
    for path in ("tests/test_workspace_lease.py", "tests/test_category_rules.py", "typing/check.py",
                 "typing/pacer_inventory.py", "typing/evidence/verification.json",
                 "typing/evidence/source-current-command.json", "typing/stubs/riposte/locking.pyi",
                 "typing/stubs/riposte/store.pyi", "typing/stubs/riposte/organizer.pyi", "RELEASE-MANIFEST.json"):
        evidence[path] = digest(ROOT / path)
    return {"task": "PAC-029", "result": "BOUNDED_REPAIR_ACCEPTED_MARKDOWN_ONLY",
            "version": baseline.version(), "audit": "OPEN", "milestone": "PENDING",
            "frozen_registers": frozen, "application_sources": sources, "changed_application_files": changed,
            "full_suite_before_platform_typing_adjustment": full, "final_source_focused_suite": final,
            "full_suite_source_snapshot": first_sources,
            "contracts": contracts, "raw_source": "1102 errors in 37 files, 50 checked; remains FAIL",
            "package": package, "posix": posix, "stale_evidence": pacer["stale_evidence"],
            "evidence_sha256": evidence,
            "limits": ["Unknown legacy lock markers remain blocked; no PID/age inference.",
                       "Full suite precedes final platform dispatch guards; focused, contract, POSIX and installed checks use final source.",
                       "Existing Windows runtime/dependencies; no clean bootstrap, full Linux/macOS or real-model qualification.",
                       "Deferred source/symbol registration and requirement reconciliation remain unapplied."]}


def main():
    if sys.argv[1:] == ["--inventory"]:
        sys.path.insert(0, str(ROOT / "typing"))
        import pacer_inventory
        pacer_inventory.REPORT = HERE / "deferred-inventory.json"
        return 0 if pacer_inventory.reconcile(HERE / "deferred-operations.json") else 1
    current = capture()
    if sys.argv[1:] == ["--record"]:
        (HERE / "acceptance.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    else:
        assert not sys.argv[1:]
        assert current == read(HERE / "acceptance.json"), "Recorded evidence or current source changed"
        inventory = read(HERE / "deferred-inventory.json")
        assert inventory["result"] == "FAIL" and inventory["source_unchanged"] and inventory["contracts_recorded_pass"]
        assert all(digest(ROOT / path) == value for path, value in inventory["sources"].items())
    print(json.dumps({"record_identity": "PASS", "task": "PAC-029", "scope": current["result"],
                      "frozen_registers_unchanged": True, "audit": "OPEN", "milestone": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
