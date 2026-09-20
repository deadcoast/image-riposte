"""PAC-033 retained evidence identity and read-only reconciliation planning."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
import tomllib
import xml.etree.ElementTree as ET

import analyze

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
    previous = read(ROOT / "typing/evidence/source-reviewed-catalog-scaling.json")
    changed = sorted(p for p in sources.keys() | previous.keys() if sources.get(p) != previous.get(p))
    assert changed == ["src/riposte/category_sort.py", "src/riposte/cli.py", "src/riposte/organizer.py",
                       "src/riposte/publication.py", "src/riposte/records.py", "src/riposte/sanitize.py",
                       "src/riposte/sort_history.py", "src/riposte/sort_plan.py", "src/riposte/store.py",
                       "src/riposte/terminal/actions.py", "src/riposte/terminal/controller.py",
                       "src/riposte/terminal/jobs.py", "src/riposte/terminal/service.py", "src/riposte/video.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-source-typing.json")
    frozen = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    prior_inventory = read(ROOT / "evidence/catalog-scaling/deferred-inventory.json")["sources"]
    unchanged = ("pyproject.toml", "uv.lock", "mypy.ini", "typing/pyproject.toml", "typing/uv.lock",
                 "typing/mypy-source.ini", "typing/mypy-contracts.ini", "typing/stubtest-allowlist.txt",
                 "INSTALL.ps1", "INSTALL.sh", "START.ps1", "START.sh", "START.cmd", "riposte.cmd")
    assert all(digest(ROOT / name) == prior_inventory[name] for name in unchanged)
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw == read(HERE / "source-third-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    raw_lines = (HERE / "source-third.txt").read_text().splitlines()
    assert raw_lines[0].startswith("warning: `VIRTUAL_ENV=.venv` does not match the project environment path")
    assert raw_lines[1:] == (ROOT / "typing/evidence/source-current.txt").read_text().splitlines()
    assert "Found 876 errors in 36 files (checked 53 source files)" in (HERE / "source-third.txt").read_text()
    assert read(HERE / "baseline-command.json")["sources"] == previous
    analysis = analyze.capture()
    assert analysis == read(HERE / "analysis.json")
    records = (ROOT / "src/riposte/records.py").read_text()
    assert "type: ignore" not in records and not any(isinstance(n, ast.Name) and n.id == "Any" for n in ast.walk(ast.parse(records)))
    consumers = read(HERE / "consumers.json")
    assert consumers["result"] == "PASS" and consumers["sources"] == sources
    assert consumers["positive_errors"] == 0 and consumers["expected_negative_errors"] == 9 and consumers["exact_lines_and_codes"]
    assert Path(consumers["command"][-1]) == ROOT / "src/riposte"
    assert "Found 885 errors in 37 files (checked 55 source files)" in (HERE / "consumers.txt").read_text()
    assert {key: n for key, n in analyze.diagnostics(HERE / "consumers.txt").items() if key[0].startswith("src/")} == dict(analyze.diagnostics(HERE / "source-third.txt"))
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (60, 402, 50)
    assert read(ROOT / "typing/evidence/source-after.json") == sources
    focused, full = (counts(name) for name in ("focused-first.xml", "full-native.xml"))
    assert focused == dict(tests=255, failures=0, errors=0, skipped=1, passed=254)
    assert full == dict(tests=1189, failures=0, errors=0, skipped=9, passed=1180)
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["version"] == baseline.version() == "0.5.0"
    assert package["application_files"] == len(sources) == 60
    assert all(value == "PASS" for checks in package["checks"].values() for value in checks.values())
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/source-typing/dist" / name) == value
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
    return {"task": "PAC-033", "result": "BOUNDED_REDUCTION_ACCEPTED_MARKDOWN_ONLY", "audit": "OPEN", "milestone": "PENDING",
            "version": version, "application_sources": sources, "changed_application_files": changed,
            "frozen_registers": frozen, "unchanged_configuration_and_launchers": list(unchanged),
            "analysis": analysis, "focused_initial": focused, "full_suite": full, "contracts": contracts,
            "source_consumers": consumers, "raw_source": "876 diagnostics in 36 files, 53 checked; remains FAIL",
            "package": package, "entries": entries, "stale_evidence": pacer["stale_evidence"], "evidence_sha256": evidence,
            "limits": ["224 fewer checker diagnostics, not a claim of runtime defect fixes or source-wide cleanliness.",
                       "Source consumer compatibility is separate from the retained 876 source-body diagnostics.",
                       "AST erasure and localized casts require behavior review; annotations add no runtime validation.",
                       "Initial focused tests precede final annotations; full suite covers final application source.",
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
    print(json.dumps({"identity": "PASS", "task": "PAC-033", "scope": current["result"], "frozen_registers_unchanged": True,
                      "audit": "OPEN", "milestone": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
