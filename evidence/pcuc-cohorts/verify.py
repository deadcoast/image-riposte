"""Verify retained PCUC-003 evidence identity; never mutate PACER registers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    spec = importlib.util.spec_from_file_location("manifest_basis", ROOT / "evidence/milestone-reconciliation-2026-09-18/verify.py")
    basis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(basis)
    basis.INPUTS += ("docs/PCUC.md",)
    result = basis.manifest()
    result["generator"] = "evidence/pcuc-cohorts/verify.py --manifest"
    return result


def counts(name):
    suites = ET.parse(HERE / name).getroot().findall("testsuite")
    result = {key: sum(int(s.attrib[key]) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[k] for k in ("failures", "errors", "skipped"))
    return result


def capture():
    assert read(ROOT / "RELEASE-MANIFEST.json") == manifest()
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "src/riposte").rglob("*")
               if p.is_file() and "__pycache__" not in p.parts}
    assert len(sources) == 63
    before = read(HERE / "source-before.json")
    assert before == read(ROOT / "typing/evidence/source-reviewed-experiments.json")
    with ZipFile(HERE / "source-before.zip") as archive:
        assert {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()} == before
    changed = sorted(p for p in sources.keys() | before.keys() if sources.get(p) != before.get(p))
    assert changed == ["src/riposte/cli.py", "src/riposte/cohort.py", "src/riposte/experiment.py", "src/riposte/generation.py",
                       "src/riposte/records.py", "src/riposte/terminal/service.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-cohorts.json")
    assert sources == read(ROOT / "typing/evidence/source-after.json")
    frozen = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    old_inputs = read(ROOT / "evidence/pcuc-experiments/deferred-inventory.json")["sources"]
    for name in ("pyproject.toml", "uv.lock", "mypy.ini", "typing/pyproject.toml", "typing/uv.lock",
                 "typing/mypy-source.ini", "typing/mypy-contracts.ini", "typing/stubtest-allowlist.txt"):
        assert digest(ROOT / name) == old_inputs[name]
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    assert "Found 772 errors in 36 files (checked 56 source files)" in (HERE / "raw-source.txt").read_text()
    assert (HERE / "raw-source.txt").read_text().splitlines()[1:] == (ROOT / "typing/evidence/source-current.txt").read_text().splitlines()
    assert not any("experiment.py:" in line and "error:" in line for line in (HERE / "raw-source.txt").read_text().splitlines())
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (63, 441, 53)
    full = counts("full-native.xml")
    assert full == dict(tests=1259, failures=0, errors=0, skipped=9, passed=1250)
    command = read(HERE / "full-command.json")
    assert command["exit_code"] == 0 and command["source_unchanged"] and command["sources"] == sources
    assert counts("before.xml") == dict(tests=15, failures=15, errors=0, skipped=0, passed=0)
    assert "Missing stub: cohort" in (HERE / "contracts-before-review.txt").read_text()
    proof = read(HERE / "proof.json")
    assert proof["sources"] == sources and proof["result"] == "PASS"
    assert (proof["states"], proof["extreme_completions"]) == (216, 343)
    assert counts("full-first-native.xml")["failures"] == 1
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["application_files"] == 63 and package["version"] == "0.5.0"
    assert all(value == "PASS" for checks in package["checks"].values() for value in checks.values())
    assert all(checks["cohort_commit_generation_review_bounds"] == "PASS" for checks in package["checks"].values())
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/pcuc-cohorts/dist" / name) == value
    pacer = read(HERE / "pacer-validation.json")
    assert pacer["valid"] and pacer["revision"] == "09463d2ffc947c0d5c06aa0bc797a42ba097678846d6f4d1f40abb3ed93d7fd5"
    excluded = {"acceptance.json", "deferred-inventory.json", "deferred-operations.json", "inventory-output.txt", "verification.txt"}
    paths = [p for p in HERE.rglob("*") if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts]
    paths += [p for base in (ROOT / "tests", ROOT / "typing/stubs") for p in base.rglob("*")
              if p.is_file() and p.suffix in {".py", ".pyi", ".js", ".cjs"}]
    paths += [ROOT / name for name in ("typing/check.py", "typing/pacer_inventory.py", "typing/runtime_contracts.py",
              "typing/evidence/verification.json", "typing/evidence/source-current-command.json", "RELEASE-MANIFEST.json")]
    return {"study": "PCUC-003", "result": "LOCAL_COHORT_WORKFLOW_AND_BOUNDS_VERIFIED", "milestone": "OPEN", "PAC-034": "SHELVED",
            "sources": sources, "changed": changed, "frozen_registers": frozen, "full_suite": full,
            "contracts": contracts, "raw_source": "772 errors in 36 files; 56 checked; FAIL retained",
            "package": package, "stale_evidence": pacer["stale_evidence"],
            "evidence_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(paths))},
            "limits": ["Local trusted-operator commitment, not independent preregistration or tamper-proof history.",
                       "Presentation blinding only; reviewer independence and actual viewing are not established.",
                       "Equal-artwork selected-sample missingness bounds; no confidence intervals, independence or efficacy inference.",
                       "Synthetic generation/loader fixtures; no CUDA or pretrained model task qualification.",
                       "Existing-dependency package checks; clean installation remains shelved.",
                       "Raw-source typing, platform qualification and coordinated CSV reconciliation remain open."]}


def main():
    if sys.argv[1:] == ["--manifest"]:
        print(json.dumps(manifest(), indent=2))
        return 0
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
        assert current == read(HERE / "acceptance.json"), "Source/evidence identity changed"
        inventory = read(HERE / "deferred-inventory.json")
        assert inventory["result"] == "FAIL" and inventory["source_unchanged"] and inventory["contracts_recorded_pass"]
        assert all(digest(ROOT / path) == value for path, value in inventory["sources"].items())
    print(json.dumps({"identity": "PASS", "study": "PCUC-003", "result": current["result"],
                      "milestone": "OPEN", "PAC-034": "SHELVED", "frozen_registers_unchanged": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
