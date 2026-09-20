"""PCUC retained proof/evidence identity; does not execute tests or write CSVs."""
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
    result["generator"] = "evidence/pcuc-shared-views/verify.py --manifest"
    return result


def counts(name):
    suites = ET.parse(HERE / name).getroot().findall("testsuite")
    result = {key: sum(int(s.attrib[key]) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    result["passed"] = result["tests"] - sum(result[k] for k in ("failures", "errors", "skipped"))
    return result


def capture():
    current_manifest = manifest()
    assert read(ROOT / "RELEASE-MANIFEST.json") == current_manifest
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "src/riposte").rglob("*")
               if p.is_file() and "__pycache__" not in p.parts}
    assert len(sources) == 61
    previous = read(HERE / "source-before.json")
    assert previous == read(ROOT / "typing/evidence/source-reviewed-source-typing.json")
    with ZipFile(HERE / "source-before.zip") as archive:
        assert {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()} == previous
    changed = sorted(p for p in sources.keys() | previous.keys() if sources.get(p) != previous.get(p))
    assert changed == ["src/riposte/context_graph.py", "src/riposte/coupled.py", "src/riposte/optimizer.py", "src/riposte/release_guard.py"]
    assert sources == read(ROOT / "typing/evidence/source-reviewed-shared-views.json")
    frozen = read(ROOT / "evidence/milestone-reconciliation-2026-09-18/review.json")["frozen_registers"]
    assert all(digest(ROOT / path) == value for path, value in frozen.items())
    old_inputs = read(ROOT / "evidence/source-typing/deferred-inventory.json")["sources"]
    for name in ("pyproject.toml", "uv.lock", "mypy.ini", "typing/pyproject.toml", "typing/uv.lock",
                 "typing/mypy-source.ini", "typing/mypy-contracts.ini", "typing/stubtest-allowlist.txt"):
        assert digest(ROOT / name) == old_inputs[name]
    raw = read(ROOT / "typing/evidence/source-current-command.json")
    assert raw["sources"] == sources and raw["exit_code"] == 1
    assert "Found 871 errors in 36 files (checked 54 source files)" in (HERE / "raw-source.txt").read_text()
    assert (HERE / "raw-source.txt").read_text().splitlines()[1:] == (ROOT / "typing/evidence/source-current.txt").read_text().splitlines()
    assert read(ROOT / "typing/evidence/source-after.json") == sources
    contracts = read(ROOT / "typing/evidence/verification.json")
    assert len(contracts["results"]) == 7 and all(contracts["results"].values())
    assert (contracts["source_files"], contracts["source_signatures"], contracts["stubtest_leaf_modules"]) == (61, 406, 51)
    full = counts("full-native.xml")
    assert full == dict(tests=1207, failures=0, errors=0, skipped=9, passed=1198)
    command = read(HERE / "full-command.json")
    assert command["exit_code"] == 0 and command["source_unchanged"] and command["sources"] == sources
    assert counts("before.xml") == dict(tests=12, failures=12, errors=0, skipped=0, passed=0)
    proof = read(HERE / "proof.json")
    assert proof["result"] == "PASS" and proof["sources"] == sources and len(proof["comparisons"]) == 8
    assert max(row["max_absolute_error"] for row in proof["comparisons"]) < 2e-9
    assert all(row["peak_saved_tensor_bytes"] == 66564 and row["remaining_bytes"] == 0 for row in proof["saved_tensors"])
    measurements = read(HERE / "measurements.json")
    assert measurements["result"] == "PASS" and measurements["sources"] == sources and len(measurements["cases"]) == 5
    measured = []
    for case in measurements["cases"]:
        assert case["same_pixels"] and case["same_selection"] and case["same_context_scores"]
        before = case["before"]["samples"][0]["calls"]
        after = case["after"]["samples"][0]["calls"]
        assert all(after["view:" + view] == 8 for view in ("identity", "jpeg85", "resize75"))
        assert all(after[key] == before[key] for key in before if not key.startswith("view:"))
        measured.append({"encoders": case["encoders"], "optional": case["optional_branches"],
                         "heavy": case["synthetic_convolutional_model"], "speedup": case["speedup"]})
    package = read(HERE / "package.json")
    assert package["result"] == "PASS" and package["application_files"] == 61 and package["version"] == "0.5.0"
    assert all(value == "PASS" for checks in package["checks"].values() for value in checks.values())
    for name, value in package["artifact_sha256"].items():
        assert digest(ROOT / ".tmp/pcuc-shared-views/dist" / name) == value
    pacer = read(HERE / "pacer-validation.json")
    assert pacer["valid"] and pacer["revision"] == "09463d2ffc947c0d5c06aa0bc797a42ba097678846d6f4d1f40abb3ed93d7fd5"
    excluded = {"acceptance.json", "deferred-inventory.json", "deferred-operations.json", "inventory-output.txt", "verification.txt"}
    paths = [p for p in HERE.rglob("*") if p.is_file() and p.name not in excluded and "__pycache__" not in p.parts]
    paths += [p for base in (ROOT / "tests", ROOT / "typing/stubs") for p in base.rglob("*")
              if p.is_file() and p.suffix in {".py", ".pyi", ".js", ".cjs"}]
    paths += [ROOT / name for name in ("typing/check.py", "typing/pacer_inventory.py", "typing/runtime_contracts.py",
              "typing/evidence/verification.json", "typing/evidence/source-current-command.json", "RELEASE-MANIFEST.json")]
    return {"study": "PCUC-001", "result": "SHARED_VIEW_COMPUTATION_VERIFIED", "milestone": "OPEN", "PAC-034": "SHELVED",
            "sources": sources, "changed": changed, "frozen_registers": frozen, "full_suite": full, "contracts": contracts,
            "raw_source": "871 errors, 36 files, 54 checked; FAIL retained", "measurements": measured,
            "package": package, "stale_evidence": pacer["stale_evidence"],
            "evidence_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(paths))},
            "limits": ["Deterministic non-mutating context functions and fixed detached weights; surrogate derivative only.",
                       "Floating-point sum reordering can change near-zero signs and search trajectories beyond these samples.",
                       "Synthetic CPU timings and saved-tensor counts; no pretrained/GPU/whole-memory or efficacy claim.",
                       "Existing dependency packaging only; clean installation qualification stays shelved.",
                       "Four-register reconciliation deferred; validation does not make stale evidence current."]}


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
    print(json.dumps({"identity": "PASS", "study": "PCUC-001", "result": current["result"], "PAC-034": "SHELVED",
                      "milestone": "OPEN", "frozen_registers_unchanged": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
