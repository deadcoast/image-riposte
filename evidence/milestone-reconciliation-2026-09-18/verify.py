"""Check this review checkpoint without updating frozen PACER registers.

--manifest emits the explicitly scoped development manifest to stdout.
No path is written by this verifier. A successful check does not close the audit.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INPUTS = (
    "README.md", "AGENTS.md", "todo-audit.PACER.md", "LICENSE",
    "pyproject.toml", "uv.lock", "MANIFEST.in", "mypy.ini",
    "INSTALL.ps1", "INSTALL.sh", "START.ps1", "START.sh", "START.cmd", "riposte.cmd",
    "docs/PROJECT-STATUS.md", "docs/CLI.md", "docs/REBUILD.md", "docs/CHANGELOG.md",
    "docs/DESIGN.md", "docs/UX-CONTRACT.md", "docs/DEVELOPMENT-SPEC.md",
    "docs/WAVE-04.md", "docs/THREAT-MODEL.md", "docs/VALIDATION.md",
    "typing/README.md", "typing/pyproject.toml", "typing/uv.lock",
    "typing/mypy-contracts.ini", "typing/mypy-source.ini",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files() -> list[Path]:
    files = []
    for directory, children, names in os.walk(ROOT / "src/riposte"):
        children[:] = sorted(c for c in children if c != "__pycache__")
        files.extend(Path(directory) / name for name in sorted(names))
    return files


def version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def manifest() -> dict:
    paths = sorted({ROOT / name for name in INPUTS} | set(source_files()))
    files = {p.relative_to(ROOT).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p)}
             for p in paths}
    return {
        "release": f"RIPOSTE {version()}",
        "version": version(),
        "status": "DEVELOPMENT_AUDIT_OPEN",
        "milestone": "PENDING_MARKDOWN_AUDIT_COMPLETION",
        "scope": "Application source plus the explicit configuration, launcher and documentation inputs listed in files. Development snapshot only; not built wheel/sdist/install equality, complete repository inventory, model qualification or audit completion. Excludes itself, generated files, historical artifacts, tests, other evidence and model assets.",
        "historical_manifest": "history/v0.4.0/RELEASE-MANIFEST.json",
        "generator": "evidence/milestone-reconciliation-2026-09-18/verify.py --manifest",
        "manifest_entries": len(files),
        "files": files,
    }


def verify() -> dict:
    report = json.loads((HERE / "review.json").read_text())
    expected = json.loads((ROOT / "RELEASE-MANIFEST.json").read_text())
    assert expected == manifest(), "Development manifest differs from declared current scope"
    for name, value in report["frozen_registers"].items():
        assert digest(ROOT / name) == value, f"Frozen register changed: {name}"
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in source_files()}
    assert sources == report["application_sources"], "Application source changed during review"
    assert sources == json.loads((ROOT / "typing/evidence/source-reviewed-category-sort.json").read_text())
    raw = json.loads((ROOT / "typing/evidence/source-current-command.json").read_text())
    assert sources == raw["sources"] and raw["exit_code"] == 1
    assert digest(ROOT / expected["historical_manifest"]) == report["historical_manifest"]["sha256"]
    tree = ast.parse((ROOT / "src/riposte/__init__.py").read_text())
    source_version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets))
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    lock_version = next(p["version"] for p in lock["package"] if p["name"] == "riposte-studio")
    assert source_version == lock_version == version() == report["versions"]["installed"]
    suites = ET.parse(HERE / "launcher-menu.xml").getroot().findall("testsuite")
    assert sum(int(s.attrib["tests"]) for s in suites) == 29
    assert all(int(s.attrib[key]) == 0 for s in suites for key in ("failures", "errors", "skipped"))
    probes = json.loads((HERE / "probes.json").read_text())
    assert probes["probe_status"] == "OBSERVATIONS_REPRODUCED"
    assert probes["application_acceptance"] == "NOT_A_PASS_CLAIM"
    assert len(probes["findings"]) == 5 and probes["sources"] == sources
    assert {row["id"] for row in report["audit_items"]} == {
        "PAC-015", *(f"PAC-{number:03}" for number in range(29, 44))}
    assert not any(row["status"] == "DONE" for row in report["audit_items"])
    return {"checkpoint": "PASS", "application_audit": "OPEN", "release_milestone": "PENDING",
            "frozen_registers_unchanged": True, "application_source_unchanged": True,
            "manifest_files": len(expected["files"]), "version": version(),
            "launcher_menu_tests": 29, "reproduced_open_findings": 5,
            "raw_source_typing": "FAIL_RETAINED_SOURCE_MATCHES",
            "historical_manifest_preserved": True}


if __name__ == "__main__":
    print(json.dumps(manifest() if sys.argv[1:] == ["--manifest"] else verify(), indent=2))
