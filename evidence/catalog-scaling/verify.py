"""PAC-032 retained evidence identity and read-only reconciliation planning."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(name):
    suites = ET.parse(HERE / name).getroot().findall("testsuite")
    result = {key: sum(int(s.attrib[key]) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[k] for k in ("failures", "errors", "skipped"))
    return result


def capture():
    spec = importlib.util.spec_from_file_location("manifest_basis", ROOT / "evidence/milestone-reconciliation-2026-09-18/verify.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    assert read(ROOT / "RELEASE-MANIFEST.json") == baseline.manifest()
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in baseline.source_files()}
    previous = read(ROOT / "typing/evidence/source-reviewed-sort-preview.json")
    changed = sorted(p for p in sources.keys() | previous.keys() if sources.get(p) != previous.get(p))
    assert changed == ["src/riposte/catalog_guard.py", "src/riposte/organizer.py", "src/riposte/sort_history.py",
                       "src/riposte/sort_titles.py", "src/riposte/store.py", "src/riposte/video.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-catalog-scaling.json")
    frozen = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    assert "Found 1100 errors in 37 files (checked 52 source files)" in (HERE / "raw-source.txt").read_text()
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (59, 402, 49)
    assert read(ROOT / "typing/evidence/source-after.json") == sources
    before, focused, full = (counts(name) for name in ("before.xml", "focused.xml", "full-native.xml"))
    assert before == dict(tests=18, failures=8, errors=0, skipped=0, passed=10)
    assert focused == dict(tests=180, failures=0, errors=0, skipped=1, passed=179)
    assert full == dict(tests=1189, failures=0, errors=0, skipped=9, passed=1180)
    measurements = {key: read(HERE / f"measure-{key}.json") for key in ("before", "after")}
    assert measurements["before"]["sources"] == previous
    assert measurements["after"]["sources"] == sources
    assert all(len(value["measurements"]) == 12 for value in measurements.values())
    rows = {}
    for old, new in zip(measurements["before"]["measurements"], measurements["after"]["measurements"]):
        n, operation = new["images_before"], new["operation"]
        assert (n, operation, new["added_images"]) == (old["images_before"], old["operation"], old["added_images"])
        assert n in (16, 32, 64)
        assert new["rows"] == n * {"audit": 2, "lookup": 1, "apply_keep": 8, "apply_new": 8}[operation]
        assert old["rows"] > new["rows"] and old["bytes"] > new["bytes"]
        assert all(value[key] > 0 for value in (old, new) for key in ("seconds", "python_peak_bytes", "selects"))
        rows[f"{operation}:{n}"] = {"before": old["rows"], "after": new["rows"]}
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["version"] == baseline.version() == "0.5.0"
    assert package["application_files"] == len(sources) == 59
    assert all(value == "PASS" for checks in package["checks"].values() for value in checks.values())
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/catalog-scaling/dist" / name) == value
    tree = ast.parse((ROOT / "src/riposte/__init__.py").read_text())
    version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets))
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    assert version == baseline.version() == next(p["version"] for p in lock["package"] if p["name"] == "riposte-studio")
    entries = read(HERE / "entries.json")
    assert entries["wrapper_version"] == "RIPOSTE 0.5.0"
    assert entries["start_linear"] == dict(exit_code=0, main_menu=True, explicit_q_exit=True, stderr_empty=True)
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
    return {"task": "PAC-032", "result": "BOUNDED_REPAIR_ACCEPTED_MARKDOWN_ONLY", "audit": "OPEN", "milestone": "PENDING",
            "version": version, "application_sources": sources, "changed_application_files": changed,
            "frozen_registers": frozen, "before": before, "focused": focused, "full_suite": full,
            "measured_rows": rows, "contracts": contracts, "raw_source": "1100 diagnostics in 37 files, 52 checked; remains FAIL",
            "package": package, "entries": entries, "stale_evidence": pacer["stale_evidence"], "evidence_sha256": evidence,
            "limits": ["Synthetic 32x24 PNGs, real SQLite, Windows runtime; returned logical rows/bytes, not disk IO.",
                       "Single timing samples and instrumented Python allocation peaks; no whole-sort linear-time guarantee.",
                       "Journal persistence and full browser state polling remain separate costs.",
                       "SQLite revision/path identity guards are not cryptographic raw database tamper monitoring.",
                       "Later external races can leave incomplete journal-backed work; undo remains conflict-checked.",
                       "Five Windows symlink-privilege and four POSIX terminal skips.",
                       "No clean bootstrap, native Linux/macOS application or real-model efficacy qualification.",
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
    print(json.dumps({"identity": "PASS", "task": "PAC-032", "scope": current["result"], "frozen_registers_unchanged": True,
                      "audit": "OPEN", "milestone": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
