"""PAC-031 retained evidence identity, with read-only CSV reconciliation planning."""
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
    previous = read(ROOT / "typing/evidence/source-reviewed-application-roots.json")
    changed = sorted(p for p in sources.keys() | previous.keys() if sources.get(p) != previous.get(p))
    assert changed == ["src/riposte/cli.py", "src/riposte/organizer.py", "src/riposte/sort_plan.py",
                       "src/riposte/static/category-sort.js", "src/riposte/terminal/controller.py",
                       "src/riposte/terminal/output.py", "src/riposte/terminal/service.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-sort-preview.json")
    full_basis = read(HERE / "raw-source-first-command.json")["sources"]
    assert set(full_basis) == set(sources)
    assert [p for p in sources if sources[p] != full_basis[p]] == ["src/riposte/sort_plan.py"]
    frozen = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    assert "Found 1100 errors in 37 files (checked 51 source files)" in (HERE / "raw-source.txt").read_text()
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (58, 398, 48)
    assert read(ROOT / "typing/evidence/source-after.json") == sources
    before, full, final = (counts(name) for name in ("before.xml", "full-native.xml", "final-sort.xml"))
    assert before == dict(tests=20, failures=20, errors=0, skipped=0, passed=0)
    assert full == dict(tests=1164, failures=0, errors=0, skipped=9, passed=1155)
    assert final == dict(tests=169, failures=0, errors=0, skipped=1, passed=168)
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["version"] == baseline.version() == "0.5.0"
    assert package["application_files"] == len(sources) == 58
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/sort-preview/dist" / name) == value
    entries = read(HERE / "entries.json")
    assert entries["wrapper_version"] == "RIPOSTE 0.5.0"
    assert entries["start_linear"] == dict(exit_code=0, main_menu=True, explicit_q_exit=True, stderr_empty=True)
    assert (HERE / "browser.txt").read_text().strip() == "PASS category_sort_browser"
    assert read(HERE / "ui-audit.json")["findings"] == read(ROOT / "evidence/category-sort/ui-audit-final.json")["findings"]
    pacer = read(HERE / "pacer-validation.json")
    assert pacer["valid"] and pacer["revision"] == "09463d2ffc947c0d5c06aa0bc797a42ba097678846d6f4d1f40abb3ed93d7fd5"
    excluded = {"acceptance.json", "deferred-inventory.json", "deferred-operations.json", "inventory-output.txt", "verification.txt"}
    evidence = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(HERE.rglob("*"))
                if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts}
    paths = [p for base in (ROOT / "tests", ROOT / "typing/stubs") for p in base.rglob("*")
             if p.is_file() and p.suffix in {".py", ".pyi", ".js", ".cjs"}]
    paths += [ROOT / name for name in ("typing/check.py", "typing/pacer_inventory.py", "typing/runtime_contracts.py",
              "typing/evidence/verification.json", "typing/evidence/source-current-command.json", "RELEASE-MANIFEST.json")]
    evidence.update({p.relative_to(ROOT).as_posix(): digest(p) for p in paths})
    return {"task": "PAC-031", "result": "BOUNDED_REPAIR_ACCEPTED_MARKDOWN_ONLY", "audit": "OPEN", "milestone": "PENDING",
            "version": baseline.version(), "application_sources": sources, "changed_application_files": changed,
            "frozen_registers": frozen, "before": before, "full_suite": full, "final_sorting": final,
            "contracts": contracts, "raw_source": "1100 diagnostics in 37 files, 51 checked; remains FAIL",
            "package": package, "entries": entries, "stale_evidence": pacer["stale_evidence"], "evidence_sha256": evidence,
            "limits": ["Full suite precedes final planner codec imports and callback annotation; affected sorting suite passes after that correction.",
                       "Windows native runtime; five symlink-privilege and four POSIX terminal skips.",
                       "Browser runs shipping UI against controlled network fixtures; API/filesystem are tested separately.",
                       "Static UI scanner retains 66 unchanged findings and prior documented limitations.",
                       "Stale consent rejection is before workspace acquisition; later races can leave recoverable partial work.",
                       "Combined receipt binds configured model paths and recipe, not model weight bytes; model preflight still applies.",
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
    print(json.dumps({"identity": "PASS", "task": "PAC-031", "scope": current["result"], "frozen_registers_unchanged": True,
                      "audit": "OPEN", "milestone": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
