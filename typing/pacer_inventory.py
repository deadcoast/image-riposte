"""Reconcile the PACER source/typing file index without importing the application.

--plan writes proposed guarded operations; it never writes the canonical CSVs.
Exports records statically declared names (including class methods), not Python's
dynamic public API. Imports includes conditional and function-local statements.
Requires resolves local static modules and source/stub ownership, not dynamic
imports, optional-provider availability, or execution order.
Source symbols include module declarations and direct class methods. Nested
implementation closures and external declarations remain under their owner.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path

from check import REVIEWED_SOURCE, is_application_source

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "typing/evidence/pacer-inventory.json"
TAG = "#typing-index"
INPUTS: tuple[str, ...] = (
    "tests/test_category_sort.py", "tests/test_category_sort_interfaces.py",
    "tests/category_sort_browser.cjs", "tests/category_sort_probe.js",
    "typing/evidence/source-reviewed-category-sort.json",
    "evidence/category-sort/acceptance.json",
    "evidence/category-sort/browser-final.txt",
    "evidence/category-sort/browser-sandbox.txt",
    "evidence/category-sort/build-final.txt",
    "evidence/category-sort/build.txt",
    "evidence/category-sort/checks.json",
    "evidence/category-sort/contracts.txt",
    "evidence/category-sort/core-first.txt",
    "evidence/category-sort/core-second.txt",
    "evidence/category-sort/finish.txt",
    "evidence/category-sort/full-final.txt",
    "evidence/category-sort/install-final.txt",
    "evidence/category-sort/OGM-007.json",
    "evidence/category-sort/OGM-008.json",
    "evidence/category-sort/OGM-009.json",
    "evidence/category-sort/OGM-010.json",
    "evidence/category-sort/OGM-011.json",
    "evidence/category-sort/OGM-012.json",
    "evidence/category-sort/OGM-013.json",
    "evidence/category-sort/OGM-014.json",
    "evidence/category-sort/OGM-015.json",
    "evidence/category-sort/OGM-016.json",
    "evidence/category-sort/OGM-017.json",
    "evidence/category-sort/package-final.txt",
    "evidence/category-sort/package.json",
    "evidence/category-sort/presentation-final.txt",
    "evidence/category-sort/raw-source-first.txt.gz",
    "evidence/category-sort/README.md",
    "evidence/category-sort/typing-final.txt",
    "evidence/category-sort/typing-first.txt",
    "evidence/category-sort/ui-audit-config.json",
    "evidence/category-sort/ui-audit-final.json",
    "evidence/category-sort/verify_package.py",
    "tests/test_category_rules.py", "typing/evidence/source-reviewed-category-rules.json",
    "evidence/category-rules/README.md", "evidence/category-rules/acceptance.json",
    "tests/test_title_categories.py", "typing/evidence/source-reviewed-title-discovery.json",
    "evidence/title-discovery/README.md", "evidence/title-discovery/acceptance.json",
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
    "typing/evidence/source-reviewed-v050.json",
    "typing/evidence/source-reviewed-repairs.json",
    "typing/evidence/source-reviewed-workflows.json",
    # PAC-022 admits menu entry, installers, browsing and their bounded evidence.
    'INSTALL.ps1',
    'INSTALL.sh',
    'START.cmd',
    'riposte.cmd',
    'MANIFEST.in',
    'docs/DESIGN.md',
    'docs/UX-CONTRACT.md',
    'tests/test_menu_startup.py',
    'tests/test_launcher_refresh.py',
    'tests/test_v04_product_terminal.py',
    'typing/evidence/source-reviewed-menu.json',
    'evidence/menu-startup/before.txt',
    'evidence/menu-startup/before.xml',
    'evidence/menu-startup/browser.txt',
    'evidence/menu-startup/browser.xml',
    'evidence/menu-startup/build-final.txt',
    'evidence/menu-startup/build.txt',
    'evidence/menu-startup/check_package.py',
    'evidence/menu-startup/install.txt',
    'evidence/menu-startup/lock.txt',
    'evidence/menu-startup/native-console-cmd.json',
    'evidence/menu-startup/native-console-cmd.txt',
    'evidence/menu-startup/native-console-first.txt',
    'evidence/menu-startup/native-console-powershell.json',
    'evidence/menu-startup/native-console-powershell.txt',
    'evidence/menu-startup/native-console.json',
    'evidence/menu-startup/native-console.txt',
    'evidence/menu-startup/native-run.txt',
    'evidence/menu-startup/native_console.py',
    'evidence/menu-startup/package-before.json',
    'evidence/menu-startup/package.json',
    'evidence/menu-startup/pytest.txt',
    'evidence/menu-startup/pytest.xml',
    'evidence/menu-startup/README.md',
    'evidence/menu-startup/report.json',
    'evidence/menu-startup/source-mypy-final.txt',
    'evidence/menu-startup/source-mypy.txt',
    'evidence/menu-startup/targeted-first.txt',
    'evidence/menu-startup/targeted-first.xml',
    'evidence/menu-startup/targeted-second.txt',
    'evidence/menu-startup/targeted-second.xml',
    'evidence/menu-startup/typing.txt',
    'evidence/menu-startup/windows-launcher.txt',
    'evidence/menu-startup/browser-small.png',
    'evidence/menu-startup/browser-small.txt',
    'evidence/menu-startup/capture.py',
    'evidence/menu-startup/home-small.png',
    'evidence/menu-startup/home-small.txt',
    'evidence/menu-startup/home-wide.png',
    'evidence/menu-startup/home-wide.txt',
    'evidence/menu-startup/menu-final.txt',
    'evidence/menu-startup/menu-final.xml',
    'evidence/menu-startup/typing-final.txt',
    # PAC-020 admits independent workflows and their bounded regression evidence.
    "tests/test_workflows.py", "evidence/workflows/README.md",
    "evidence/workflows/report.json", "evidence/workflows/pytest.txt",
    "evidence/workflows/pytest.xml", "evidence/workflows/browser.txt",
    "evidence/workflows/browser.xml", "evidence/workflows/typing.txt",
    "typing/evidence/source-current.txt",
    "typing/evidence/source-current-command.txt",
    "typing/evidence/source-environment.json",
    "typing/evidence/source-current-command.json",
    "typing/evidence/dynamic-boundaries.json",
    "typing/evidence/windows-stat-probe.txt",
    "typing/evidence/windows-stat-probe-app-py314.txt",
    # PAC-004 explicitly admits terminal patch integration and its proof inputs.
    "START.ps1", "START.sh", "docs/CHANGELOG.md", "docs/CLI.md",
    "docs/REBUILD.md", "docs/REVISION-v05.md", "docs/PATCH-v05-MERGE.md",
    "docs/TERMINAL-DESIGN.spec.md", "docs/VALIDATION.md",
    "scripts/capture_revision.py", "scripts/capture_terminal.py", "scripts/record_terminal.py",
    "scripts/verify_v05_merge.py",
    "tests/test_v05_revision.py",
    "typing/evidence/mypy-contracts.txt", "typing/evidence/stubtest.txt",
)

# PAC-026 admits exclusive output commits and rejected-destination recovery.
INPUTS += (
    "tests/test_sort_collisions.py",
    "typing/evidence/source-reviewed-sort-collisions.json",
)

# PAC-025 admits per-file sorting failure recovery and destination allocation.
INPUTS += (
    "tests/test_sort_partial_failures.py",
    "typing/evidence/source-reviewed-sort-partial.json",
)

# PAC-024 admits journal-time source mutation checks and their proof inputs.
INPUTS += (
    "tests/test_sort_commit_safety.py",
    "typing/evidence/source-reviewed-sort-commit.json",
)

# PAC-023 admits reversible media sorting and its bounded evidence.
INPUTS += (
    'tests/test_sort_recovery.py',
    'tests/test_video_sort.py',
    'tests/test_organizer.py',
    'tests/test_v04_terminal_core.py',
    'typing/evidence/source-reviewed-sort-recovery.json',
    'evidence/sort-recovery/backend-first.txt',
    'evidence/sort-recovery/backend-first.xml',
    'evidence/sort-recovery/before.txt',
    'evidence/sort-recovery/before.xml',
    'evidence/sort-recovery/browser-report.json',
    'evidence/sort-recovery/browser-small.png',
    'evidence/sort-recovery/browser-small.txt',
    'evidence/sort-recovery/browser.txt',
    'evidence/sort-recovery/browser.xml',
    'evidence/sort-recovery/build-final.txt',
    'evidence/sort-recovery/build.txt',
    'evidence/sort-recovery/capture.py',
    'evidence/sort-recovery/check_package.py',
    'evidence/sort-recovery/contracts-final.txt',
    'evidence/sort-recovery/distribution-report.json',
    'evidence/sort-recovery/expanded-first.txt',
    'evidence/sort-recovery/expanded-first.xml',
    'evidence/sort-recovery/full-first.txt',
    'evidence/sort-recovery/full-first.xml',
    'evidence/sort-recovery/home-small.png',
    'evidence/sort-recovery/home-small.txt',
    'evidence/sort-recovery/home-wide.png',
    'evidence/sort-recovery/home-wide.txt',
    'evidence/sort-recovery/install-final.txt',
    'evidence/sort-recovery/install.txt',
    'evidence/sort-recovery/menu-report.json',
    'evidence/sort-recovery/native-cmd-run.txt',
    'evidence/sort-recovery/native-console-cmd.json',
    'evidence/sort-recovery/native-console-cmd.txt',
    'evidence/sort-recovery/native-console-powershell.json',
    'evidence/sort-recovery/native-console-powershell.txt',
    'evidence/sort-recovery/native-run.txt',
    'evidence/sort-recovery/native_console.py',
    'evidence/sort-recovery/package-final.txt',
    'evidence/sort-recovery/package-run.txt',
    'evidence/sort-recovery/package.json',
    'evidence/sort-recovery/publication-report.json',
    'evidence/sort-recovery/recovery-final.txt',
    'evidence/sort-recovery/recovery-final.xml',
    'evidence/sort-recovery/source-mypy-final.txt',
    'evidence/sort-recovery/source-mypy.txt',
    'evidence/sort-recovery/suite-final.txt',
    'evidence/sort-recovery/targeted-final.txt',
    'evidence/sort-recovery/targeted-final.xml',
    'evidence/sort-recovery/typing-final.txt',
    'evidence/sort-recovery/typing-first.txt',
    'evidence/sort-recovery/verification.json',
    'evidence/sort-recovery/windows-launcher.txt',
    'evidence/sort-recovery/workflows-report.json',
)

INPUTS += ('evidence/sort-recovery/README.md', 'evidence/sort-recovery/suite-final.xml', 'evidence/sort-recovery/source-mypy-current.txt', 'evidence/sort-recovery/inventory-first.txt')


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
                    if Path(path).parent.as_posix() in {"typing", "scripts"} and path.endswith(".py")})
    return [describe(path, modules) for path in paths], {path: digest(ROOT / path) for path in paths}


def symbol_inventory(paths: list[str]) -> list[dict[str, str]]:
    """Index declarations and statically named references without importing code."""
    modules = {module_info[1]: path for path in paths
               if (module_info := module_key(path)) is not None and module_info[0] == "source"}
    modules["pacer_inventory"] = "typing/pacer_inventory.py"
    owners: dict[str, tuple[str, ast.AST, str]] = {}
    trees: dict[str, ast.Module] = {}
    for path in sorted(set(modules.values())):
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        trees[path] = tree
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                owners[f"{path}:{node.name}"] = (path, node, "")
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            owners[f"{path}:{node.name}.{child.name}"] = (path, child, node.name)
            elif path.startswith("src/"):
                for name in definitions(ast.Module(body=[node], type_ignores=[])):
                    owners[f"{path}:{name}"] = (path, node, "")
    records = []
    for key, (path, declaration, class_name) in sorted(owners.items()):
        symbol = key.split(":", 1)[1]
        package_key = module_key(path)
        package = package_key[1].split(".") if package_key else []
        if Path(path).stem != "__init__":
            package = package[:-1]
        bindings: dict[str, str] = {}
        # Top-level bindings plus imports within this declaration. A sibling
        # function's local imports cannot leak into this symbol's dependencies.
        imports = [part for part in trees[path].body if isinstance(part, (ast.Import, ast.ImportFrom))]
        imports += [part for part in ast.walk(declaration) if isinstance(part, (ast.Import, ast.ImportFrom))]
        for imported in imports:
            if isinstance(imported, ast.Import):
                for alias in imported.names:
                    if alias.name in modules:
                        bindings[alias.asname or alias.name] = modules[alias.name]
            else:
                base = package[:len(package) - imported.level + 1] if imported.level else []
                if imported.module:
                    base += imported.module.split(".")
                module = ".".join(base)
                for alias in imported.names:
                    target = f"{modules[module]}:{alias.name}" if module in modules else ""
                    if target in owners:
                        bindings[alias.asname or alias.name] = target
                    elif f"{module}.{alias.name}" in modules:
                        bindings[alias.asname or alias.name] = modules[f"{module}.{alias.name}"]
        shadowed: set[str] = set()
        if isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)):
            shadowed.update(arg.arg for arg in (*declaration.args.posonlyargs, *declaration.args.args, *declaration.args.kwonlyargs))
            shadowed.update(arg.arg for arg in (declaration.args.vararg, declaration.args.kwarg) if arg)
            shadowed.update(part.id for part in ast.walk(declaration) if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Store))
        dependencies = {path}
        for part in ast.walk(declaration):
            reference = ""
            if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load) and part.id not in shadowed:
                reference = bindings.get(part.id, f"{path}:{part.id}")
            elif isinstance(part, ast.Attribute) and isinstance(part.value, ast.Name):
                if class_name and part.value.id in {"self", "cls"}:
                    reference = f"{path}:{class_name}.{part.attr}"
                elif part.value.id not in shadowed and part.value.id in bindings:
                    reference = f"{bindings[part.value.id]}:{part.attr}"
            if reference in owners and reference != key:
                dependencies.add(reference)
        # PACER represents module data declarations with its CONFIG asset type.
        kind = "CLASS" if isinstance(declaration, ast.ClassDef) else "FUNCTION" if isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)) else "CONFIG"
        records.append({"AssetType": kind, "Path": path, "Symbol": symbol,
                        "Purpose": "OBSERVED source declaration; static references, not a runtime call graph",
                        "Requires": ";".join(sorted(dependencies)), "Tags": "#source-symbol"})
    return records


def reconcile(plan: Path | None = None) -> bool:
    desired, hashes = inventory()
    with (ROOT / "overlord.PACER.csv").open(encoding="utf-8-sig", newline="") as handle:
        registered = list(csv.DictReader(handle))
    files = {row["Path"]: row for row in registered if row["AssetType"] == "FILE"}
    next_id = max((int(row["ID"].split("-")[1]) for row in registered if row["ID"].split("-")[1].isdigit()), default=0) + 1
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
    symbols = symbol_inventory(sorted(paths))
    symbol_ids = {f"{row['Path']}:{row['Symbol']}": row["ID"] for row in registered if row["Symbol"]}
    expected_keys = {f"{row['Path']}:{row['Symbol']}" for row in symbols}
    for key in sorted(expected_keys):
        if key not in symbol_ids:
            symbol_ids[key] = f"OVR-{next_id:03}"
            next_id += 1
    reference_ids = ids | symbol_ids
    for row in symbols:
        key = f"{row['Path']}:{row['Symbol']}"
        matches = [old for old in registered if old["Path"] == row["Path"] and old["Symbol"] == row["Symbol"]]
        row["ID"] = symbol_ids[key]
        required = {reference_ids[part] for part in row["Requires"].split(";")}
        row["Requires"] = ";".join(sorted(required))
        if not matches:
            issues.append(f"Unregistered symbol: {key}")
            operations.append({"op": "add", "register": "overlord", "row": row})
        elif len(matches) != 1:
            issues.append(f"Duplicate symbol: {key}")
        else:
            old = matches[0]
            fields = {}
            if old["AssetType"] != row["AssetType"]:
                fields["AssetType"] = row["AssetType"]
            # Keep additional reviewed edges; demand every derived dependency.
            existing_edges = set(filter(None, old["Requires"].split(";")))
            if not required <= existing_edges:
                fields["Requires"] = ";".join(sorted(existing_edges | required))
            if fields:
                issues.append(f"Stale symbol: {key}: {', '.join(sorted(fields))}")
                operations.append({"op": "set", "id": old["ID"], "fields": fields})
    for row in registered:
        key = f"{row['Path']}:{row['Symbol']}"
        if "#source-symbol" in row.get("Tags", "").split() and key not in expected_keys:
            issues.append(f"Retired symbol needs review: {key}")
    source = {path: value for path, value in hashes.items()
              if path.startswith("src/") and is_application_source(Path(path))}
    baseline = json.loads(REVIEWED_SOURCE.read_text(encoding="utf-8"))
    baseline = {path: value for path, value in baseline.items() if is_application_source(Path(path))}
    if source != baseline:
        issues.append("Application source differs from the reviewed source snapshot")
    source_modules = {module[1] for path in paths if (module := module_key(path)) and module[0] == "source"}
    stub_modules = {module[1] for path in paths if (module := module_key(path)) and module[0] == "stub" and module[1] != "_riposte_types"}
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
                   "source_symbols": sum(row["Path"].startswith("src/") for row in symbols),
                   "tool_functions": sum(row["Path"] == "typing/pacer_inventory.py" for row in symbols),
                   "symbol_dependency_edges": sum(len(row["Requires"].split(";")) for row in symbols),
                   "static_definitions": sum(len(row["Exports"].split(";")) for row in desired if row["Exports"]),
                   "local_dependency_edges": sum(len(row["Requires"].split(";")) for row in desired if row["Requires"])},
        "sources": hashes, "source_unchanged": source == baseline,
        "contracts_recorded_pass": not any(value is not True for value in results.values()) and set(results) == expected_stages,
        "files": [{"id": ids[row["Path"]], "path": row["Path"], "definitions": row["Exports"].split(";") if row["Exports"] else []} for row in desired],
        "symbols": symbols,
        "limits": ["Run typing/check.py immediately before acceptance; reading its old report is not a fresh test.",
                   "Static imports do not establish optional providers or dynamic dependency completeness.",
                   "Definition names are syntactic declarations; annotations and bodies require separate review.",
                   "Nested local closures and external-library declarations are represented by their owning declarations.",
                   "Source/stub pairing covers external declarations; symbol records describe application source only."]}
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
