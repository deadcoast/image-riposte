"""Reconcile the PACER source/typing file index without importing the application.

--plan writes proposed guarded operations; it never writes the canonical CSVs.
Exports records statically declared names (including class methods), not Python's
dynamic public API. Imports includes conditional and function-local statements.
Requires resolves local static modules and source/stub ownership, not dynamic
imports, optional-provider availability, or execution order.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path

from check import is_application_source

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "typing/evidence/pacer-inventory.json"
TAG = "#typing-index"
INPUTS = (
    "README.md", "AGENTS.md", "pyproject.toml", "uv.lock", "mypy.ini",
    "typing/README.md", "typing/pyproject.toml", "typing/uv.lock",
    "typing/check.py", "typing/runtime_contracts.py",
    "typing/probe_windows_stat.py", "typing/pacer_inventory.py",
    "typing/mypy-source.ini", "typing/mypy-contracts.ini", "typing/stubtest-allowlist.txt",
    "typing/test_tooling.py",
    "typing/evidence/mypy-tooling.txt", "typing/evidence/tooling-regressions.txt",
    "typing/evidence/source-after.json",
    "typing/checks/consumers.py", "typing/checks/rejected.py.txt",
    "typing/evidence/source-before.json", "typing/evidence/verification.json",
    "typing/evidence/source-current.txt",
    "typing/evidence/source-current-command.txt",
    "typing/evidence/dynamic-boundaries.json",
    "typing/evidence/windows-stat-probe.txt",
    "typing/evidence/windows-stat-probe-app-py314.txt",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scoped_paths() -> list[str]:
    paths = set(INPUTS)
    for base, pattern in ((ROOT / "src", "*"), (ROOT / "typing/stubs", "*.pyi")):
        paths.update(
            path.relative_to(ROOT).as_posix()
            for path in base.rglob(pattern)
            if path.is_file() and "__pycache__" not in path.parts
        )
    return sorted(paths)


def module_key(path: str) -> tuple[str, str] | None:
    for prefix, layer in (("src/", "source"), ("typing/stubs/", "stub")):
        if path.startswith(prefix) and Path(path).suffix in {".py", ".pyi"}:
            parts = list(Path(path[len(prefix):]).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            return layer, ".".join(parts)
    return None


def definitions(tree: ast.Module) -> list[str]:
    result: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            result.add(node.name)
            if isinstance(node, ast.ClassDef):
                result.update(
                    f"{node.name}.{child.name}" for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            result.update(
                child.id for target in targets for child in ast.walk(target)
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store)
            )
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            result.add(node.name.id)
    return sorted(result)


def describe(path: str, modules: dict[tuple[str, str], str]) -> dict[str, str]:
    row = {"AssetType": "FILE", "Path": path, "Symbol": "",
           "Exports": "", "Imports": "", "Requires": ""}
    key = module_key(path)
    if any(part.endswith(".egg-info") for part in Path(path).parts):
        row["Purpose"] = "Generated installation metadata included in the reviewed source snapshot"
    elif path.startswith("src/"):
        row["Purpose"] = "Existing application " + (f"module {key[1]}" if key else "asset")
    elif path.startswith("typing/stubs/"):
        row["Purpose"] = "External source-derived typing declarations"
    else:
        row["Purpose"] = "Typing validation input, evidence or development authority"
    dependencies: set[str] = set()
    if Path(path).suffix in {".py", ".pyi"} or path.endswith(".py.txt"):
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        row["Exports"] = ";".join(definitions(tree))
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        row["Imports"] = "\n".join(sorted({ast.unparse(node) for node in imports}))
        # The consumer fixtures are checked through mypy_path, whereas the
        # runtime probes import the implementation through PYTHONPATH.
        layer = key[0] if key else ("stub" if path.startswith("typing/checks/") else "source")
        package = key[1].split(".") if key else []
        if not Path(path).stem == "__init__":
            package = package[:-1]
        for node in imports:
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif node.level:
                base = package[:len(package) - node.level + 1]
                if node.module:
                    base += node.module.split(".")
                name = ".".join(base)
                names = [name, *(f"{name}.{alias.name}" for alias in node.names)]
            elif node.module:
                names = [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
            for name in names:
                dependency = modules.get((layer, name))
                if dependency is not None and dependency != path:
                    dependencies.add(dependency)
    if key and key[0] == "stub":
        source = modules.get(("source", key[1]))
        if source:
            dependencies.add(source)
    row["Requires"] = ";".join(sorted(dependencies))
    return row


def inventory() -> tuple[list[dict[str, str]], dict[str, str]]:
    paths = scoped_paths()
    modules = {key: path for path in paths if (key := module_key(path)) is not None}
    modules.update({("source", Path(path).stem): path for path in paths
                    if Path(path).parent.as_posix() == "typing" and path.endswith(".py")})
    return [describe(path, modules) for path in paths], {path: digest(ROOT / path) for path in paths}


def reconcile(plan: Path | None) -> bool:
    desired, hashes = inventory()
    with (ROOT / "overlord.PACER.csv").open(encoding="utf-8-sig", newline="") as handle:
        registered = list(csv.DictReader(handle))
    files = {row["Path"]: row for row in registered if row["AssetType"] == "FILE"}
    next_id = max(int(row["ID"].split("-")[1]) for row in registered if row["ID"].split("-")[1].isdigit()) + 1
    ids = {path: row["ID"] for path, row in files.items()}
    for row in desired:
        if row["Path"] not in ids:
            ids[row["Path"]] = f"OVR-{next_id:03}"
            next_id += 1
    issues: list[str] = []
    operations: list[dict[str, object]] = []
    paths = {row["Path"] for row in desired}
    for row in desired:
        path = row["Path"]
        row["ID"] = ids[path]
        row["Requires"] = ";".join(sorted(ids[part] for part in row["Requires"].split(";") if part))
        existing = files.get(path)
        row["Tags"] = " ".join(sorted(set((existing or {}).get("Tags", "").split()) | {TAG}))
        if not existing:
            issues.append(f"Unregistered file: {path}")
            operations.append({"op": "add", "register": "overlord", "row": row})
        else:
            changes = {key: value for key, value in row.items() if key != "ID" and value != existing.get(key, "")}
            # Preserve meaningful descriptions authored by other maintainers.
            changes.pop("Purpose", None)
            if changes:
                issues.append(f"Stale index: {path}: {', '.join(sorted(changes))}")
                operations.append({"op": "set", "id": ids[path], "fields": changes})
    for row in registered:
        if TAG in row.get("Tags", "").split() and row["AssetType"] == "FILE" and row["Path"] not in paths:
            issues.append(f"Retired indexed path needs review: {row['Path']}")
    # The new tool's callable symbols receive individual OVR rows. Existing
    # application/stub definitions remain in their FILE Exports and this report.
    tool_path = "typing/pacer_inventory.py"
    tool_tree = ast.parse((ROOT / tool_path).read_text(encoding="utf-8"))
    tool_functions = {node.name for node in tool_tree.body if isinstance(node, ast.FunctionDef)}
    for name in sorted(tool_functions):
        matches = [row for row in registered if row["Path"] == tool_path and row["Symbol"] == name]
        fields = {"AssetType": "FUNCTION", "Path": tool_path, "Symbol": name,
                  "Requires": ids[tool_path], "Tags": "#typing-tool"}
        if not matches:
            issues.append(f"Unregistered tool function: {name}")
            operations.append({"op": "add", "register": "overlord", "row": {
                "ID": f"OVR-{next_id:03}", "Purpose": "PACER inventory tool function", **fields}})
            next_id += 1
        elif len(matches) != 1 or any(matches[0].get(key, "") != value for key, value in fields.items()):
            issues.append(f"Tool function metadata needs review: {name}")
    for row in registered:
        if "#typing-tool" in row.get("Tags", "").split() and row["Symbol"] not in tool_functions:
            issues.append(f"Retired tool function needs review: {row['Symbol']}")
    source = {path: value for path, value in hashes.items()
              if path.startswith("src/") and is_application_source(Path(path))}
    baseline = json.loads((ROOT / "typing/evidence/source-before.json").read_text(encoding="utf-8"))
    baseline = {path: value for path, value in baseline.items() if is_application_source(Path(path))}
    if source != baseline:
        issues.append("Application source differs from the reviewed source-before snapshot")
    source_modules = {key[1] for path in paths if (key := module_key(path)) and key[0] == "source"}
    stub_modules = {key[1] for path in paths if (key := module_key(path)) and key[0] == "stub" and key[1] != "_riposte_types"}
    if source_modules != stub_modules:
        issues.append("Source/stub module coverage differs")
    verification = json.loads((ROOT / "typing/evidence/verification.json").read_text(encoding="utf-8"))
    expected_stages = {"mypy-contracts", "mypy-tooling", "stubtest", "runtime-contracts", "tooling-regressions", "negative-consumers", "source-stable"}
    results = verification.get("results", {})
    if set(results) != expected_stages or any(value is not True for value in results.values()):
        issues.append("External contract verification is incomplete or failed; run typing/check.py")
    if len([row for row in registered if row["AssetType"] == "FILE"]) != len(files):
        issues.append("Duplicate FILE paths in overlord")
    report = {
        "scope": __doc__, "result": "FAIL" if issues else "PASS", "issues": issues,
        "counts": {"source_files": len(source), "source_modules": len(source_modules),
                   "paired_stubs": len(stub_modules), "indexed_files": len(desired),
                   "tool_functions": len(tool_functions),
                   "static_definitions": sum(len(row["Exports"].split(";")) for row in desired if row["Exports"]),
                   "local_dependency_edges": sum(len(row["Requires"].split(";")) for row in desired if row["Requires"])},
        "sources": hashes, "source_unchanged": source == baseline,
        "contracts_recorded_pass": not any(value is not True for value in results.values()) and set(results) == expected_stages,
        "files": [{"id": ids[row["Path"]], "path": row["Path"], "definitions": row["Exports"].split(";") if row["Exports"] else []} for row in desired],
        "limits": ["Run typing/check.py immediately before acceptance; reading its old report is not a fresh test.",
                   "Static imports do not establish optional providers or dynamic dependency completeness.",
                   "Definition names are syntactic declarations; annotations and bodies require separate review.",
                   "Raw-source mypy errors and Windows stat finding are unresolved; no source repair is claimed."]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if plan is not None:
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text(json.dumps(operations, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("result", "counts", "source_unchanged", "issues")}, indent=2))
    return not issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, help="Write proposed PACER operations for review; do not apply them")
    args = parser.parse_args()
    return 0 if reconcile(args.plan) else 1


if __name__ == "__main__":
    raise SystemExit(main())
