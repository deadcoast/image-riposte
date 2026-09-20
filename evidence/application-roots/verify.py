"""Verify retained PAC-030 evidence identity; no tests or CSV writes are hidden here."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(name):
    suites = ET.parse(HERE / name).getroot().findall("testsuite")
    values = {key: sum(int(s.attrib[key]) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    values["passed"] = values["tests"] - sum(values[k] for k in ("failures", "errors", "skipped"))
    return values


def capture():
    spec = importlib.util.spec_from_file_location("manifest_basis", ROOT / "evidence/milestone-reconciliation-2026-09-18/verify.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    assert read(ROOT / "RELEASE-MANIFEST.json") == baseline.manifest()
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in baseline.source_files()}
    previous = read(ROOT / "typing/evidence/source-reviewed-workspace-lease.json")
    assert set(sources) == set(previous)
    changed = sorted(p for p in sources if sources[p] != previous[p])
    assert changed == ["src/riposte/store.py", "src/riposte/terminal/output.py", "src/riposte/terminal/paths.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-application-roots.json")
    historical = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")
    frozen = historical["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    assert digest(ROOT / "history/v0.4.0/RELEASE-MANIFEST.json") == historical["historical_manifest"]["sha256"]
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    assert "Found 1102 errors in 37 files (checked 50 source files)" in (HERE / "raw-source.txt").read_text()
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (57, 395, 47)
    assert read(ROOT / "typing/evidence/source-after.json") == sources
    before = counts("before-corrected.xml")
    assert before == dict(tests=29, failures=25, errors=0, skipped=0, passed=4)
    full = counts("full-native-final.xml")
    assert full == dict(tests=1130, failures=0, errors=0, skipped=9, passed=1121)
    compatibility = counts("compatibility.xml")
    assert compatibility == dict(tests=37, failures=0, errors=0, skipped=1, passed=36)
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["version"] == baseline.version() == "0.5.0"
    assert package["application_files"] == len(sources) == 57
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/application-roots/dist" / name) == value
    entries = read(HERE / "entries.json")
    assert entries["wrapper_version"] == "RIPOSTE 0.5.0"
    assert entries["start_linear"] == dict(exit_code=0, main_menu=True, explicit_q_exit=True, stderr_empty=True)
    pacer = read(HERE / "pacer-validation.json")
    assert pacer["valid"] and pacer["revision"] == "09463d2ffc947c0d5c06aa0bc797a42ba097678846d6f4d1f40abb3ed93d7fd5"
    excluded = {"acceptance.json", "deferred-inventory.json", "deferred-operations.json", "inventory-output.txt"}
    evidence = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(HERE.rglob("*"))
                if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts}
    for name in ("tests/test_application_roots.py", "tests/test_menu_startup.py", "tests/test_v04_product_terminal.py",
                 "tests/test_workflows.py", "typing/check.py", "typing/pacer_inventory.py", "typing/runtime_contracts.py",
                 "typing/stubs/riposte/store.pyi", "typing/stubs/riposte/terminal/paths.pyi", "typing/README.md",
                 "typing/evidence/verification.json", "typing/evidence/source-current-command.json", "RELEASE-MANIFEST.json"):
        evidence[name] = digest(ROOT / name)
    return {"task": "PAC-030", "result": "BOUNDED_REPAIR_ACCEPTED_MARKDOWN_ONLY", "audit": "OPEN", "milestone": "PENDING",
            "version": baseline.version(), "application_sources": sources, "changed_application_files": changed,
            "frozen_registers": frozen, "before": before, "full_suite": full, "compatibility": compatibility,
            "contracts": contracts, "raw_source": "1102 diagnostics in 37 files, 50 checked; remains FAIL",
            "package": package, "entries": entries, "stale_evidence": pacer["stale_evidence"], "evidence_sha256": evidence,
            "limits": ["Full suite predates addition of the nested-library compatibility test, which passed separately on unchanged application source.",
                       "Windows native runtime; five symlink privilege and four POSIX terminal skips. Junctions tested.",
                       "Wheel root is its package directory; other environment assets are not claimed protected.",
                       "No clean bootstrap, native Linux/macOS, real-model or efficacy qualification.",
                       "Frozen CSV source/symbol/requirement reconciliation remains deferred."]}


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
        assert current == read(HERE / "acceptance.json"), "Evidence/source identity changed"
        inventory = read(HERE / "deferred-inventory.json")
        assert inventory["result"] == "FAIL" and inventory["source_unchanged"] and inventory["contracts_recorded_pass"]
        assert all(inventory["sources"].get(path) == value for path, value in current["application_sources"].items())
        assert all(digest(ROOT / path) == value for path, value in inventory["sources"].items())
    print(json.dumps({"identity": "PASS", "task": "PAC-030", "scope": current["result"], "frozen_registers_unchanged": True,
                      "audit": "OPEN", "milestone": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
