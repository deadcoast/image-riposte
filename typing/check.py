"""Verify external declarations without editing or launching application source."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "typing"
STUBS = HERE / "stubs" / "riposte"
EVIDENCE = HERE / "evidence"
CONTRACT_CONFIG = "typing/mypy-contracts.ini"
REVIEWED_SOURCE = EVIDENCE / "source-reviewed-optional-categories.json"


def is_application_source(path: Path) -> bool:
    """Exclude generated installation metadata and bytecode, not application files."""
    return not any(part == "__pycache__" or part.endswith(".egg-info") for part in path.parts)


def source_hashes() -> dict[str, str]:
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "src").rglob("*"))
        if p.is_file() and is_application_source(p.relative_to(ROOT))
    }


def declarations(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    result = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[f"{node.name}.{method.name}"] = method
    return result


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[object, ...]:
    args = node.args
    return (
        tuple(a.arg for a in args.posonlyargs), tuple(a.arg for a in args.args),
        args.vararg.arg if args.vararg else None,
        tuple(a.arg for a in args.kwonlyargs),
        args.kwarg.arg if args.kwarg else None,
        len(args.defaults), tuple(d is not None for d in args.kw_defaults),
        tuple(ast.unparse(d) for d in node.decorator_list
              if ast.unparse(d) in {"staticmethod", "classmethod", "property"}),
    )


def check_parity() -> tuple[list[str], int, list[str]]:
    issues = []
    count = 0
    modules = []
    source_paths = {p.relative_to(ROOT / "src" / "riposte").with_suffix("")
                    for p in (ROOT / "src" / "riposte").rglob("*.py")}
    stub_paths = {p.relative_to(STUBS).with_suffix("") for p in STUBS.rglob("*.pyi")}
    for missing in sorted(source_paths - stub_paths):
        issues.append(f"Missing stub: {missing}")
    for extra in sorted(stub_paths - source_paths):
        issues.append(f"Stub has no source module: {extra}")
    for part in sorted(source_paths & stub_paths):
        source = ast.parse((ROOT / "src" / "riposte" / part.with_suffix(".py")).read_text(encoding="utf-8"))
        stub = ast.parse((STUBS / part.with_suffix(".pyi")).read_text(encoding="utf-8"))
        implementations, contracts = declarations(source), declarations(stub)
        for name, node in implementations.items():
            count += 1
            if name not in contracts:
                issues.append(f"{part}:{name}: missing declaration")
            elif signature(node) != signature(contracts[name]):
                issues.append(f"{part}:{name}: source/stub parameter mismatch")
        # stubtest recursively discovers packages. Pass leaf modules once and
        # exclude __main__, whose import launches the application.
        if part.name not in {"__main__", "__init__"}:
            modules.append("riposte." + ".".join(part.parts))
    return issues, count, modules


def run(name: str, arguments: list[str], *, executable: Path | None = None,
        timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("MYPYPATH", None)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(executable) if executable else sys.executable, *arguments], cwd=ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
        check=False, timeout=timeout,
    )
    (EVIDENCE / f"{name}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result


def source_interpreter(explicit: Path | None = None) -> Path:
    """Audit implementation in the application environment, independent of runner."""
    candidate = explicit or ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    candidate = candidate.absolute()
    if not candidate.is_file():
        raise ValueError("Application Python is missing; synchronize the existing uv project or pass --source-python.")
    return candidate


def negative_check() -> tuple[bool, str]:
    template = (HERE / "checks" / "rejected.py.txt").read_text(encoding="utf-8")
    path = HERE / ".cache" / "rejected.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    expected: Counter[tuple[int, str]] = Counter()
    for line, text in enumerate(template.splitlines(), 1):
        if "# error: " in text:
            for code in text.split("# error: ", 1)[1].split(","):
                expected[(line, code)] += 1
    result = run("negative-consumers", ["-m", "mypy", "--config-file", CONTRACT_CONFIG, str(path)])
    actual = Counter((int(line), code) for line, code in re.findall(
        r"rejected\.py:(\d+):\d+: error: .*\[([a-z][a-z-]+)\]\r?$", result.stdout, re.MULTILINE))
    other_errors = sum(": error:" in line for line in result.stdout.splitlines()) != sum(actual.values())
    success = result.returncode == 1 and actual == expected and not other_errors
    return success, f"{sum(actual.values())}/{sum(expected.values())} expected diagnostics; exact line/code match={success}"


def dynamic_inventory() -> list[dict[str, object]]:
    rows = []
    for path in sorted((HERE / "stubs").rglob("*.pyi")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        dynamic_names = {"Any"}
        if path.name == "_riposte_types.pyi":
            dynamic_names.update({"Report", "ModelTensor"})
        for imported in tree.body:
            if isinstance(imported, ast.ImportFrom) and imported.module == "_riposte_types":
                dynamic_names.update(alias.asname or alias.name for alias in imported.names
                                     if alias.name in {"Report", "ModelTensor"})
        for node in ast.walk(tree):
            annotations = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                annotations = [node.returns, *(arg.annotation for arg in (
                    *node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs))]
                for vararg in (node.args.vararg, node.args.kwarg):
                    if vararg:
                        annotations.append(vararg.annotation)
            elif isinstance(node, ast.AnnAssign):
                annotations = [node.annotation]
                if ast.unparse(node.annotation) == "TypeAlias":
                    annotations.append(node.value)
            else:
                continue
            names = {part.id for annotation in annotations if annotation is not None
                     for part in ast.walk(annotation) if isinstance(part, ast.Name)}
            if names & dynamic_names:
                rows.append({"file": path.relative_to(ROOT).as_posix(), "line": node.lineno,
                             "declaration": ast.unparse(node).splitlines()[0]})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Audit implementation bodies using the application .venv, without external stubs.")
    parser.add_argument("--source-python", type=Path, help="Explicit interpreter for --source comparisons; defaults to the application .venv.")
    args = parser.parse_args()
    if args.source_python and not args.source:
        parser.error("--source-python requires --source")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.source:
        try:
            executable = source_interpreter(args.source_python)
        except ValueError as exc:
            parser.error(str(exc))
        environment = run("source-environment", ["-c",
            "import sys,json,importlib.metadata as m; "
            "names=('mypy','numpy','Pillow','torch','diffusers','transformers'); "
            "installed={d.metadata['Name'].lower():d.version for d in m.distributions()}; "
            "print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,'python':sys.version,"
            "'dependencies':{n:installed.get(n.lower()) for n in names}},indent=2))"], executable=executable)
        if environment.returncode:
            print(environment.stderr, file=sys.stderr)
            return environment.returncode
        (EVIDENCE / "source-environment.json").write_text(environment.stdout, encoding="utf-8")
        arguments = ["-m", "mypy", "--config-file", "typing/mypy-source.ini", "--python-version", "3.13", "src/riposte"]
        result = run("source-current", arguments, executable=executable, timeout=300)
        (EVIDENCE / "source-current-command.json").write_text(json.dumps({
            "command": [str(executable), *arguments], "exit_code": result.returncode,
            "environment": json.loads(environment.stdout), "sources": source_hashes(),
        }, indent=2) + "\n", encoding="utf-8")
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    before = source_hashes()
    reviewed = json.loads(REVIEWED_SOURCE.read_text(encoding="utf-8"))
    # Optional category review covers shared matching, planning and UI reports.
    # Earlier reviewed snapshots remain historical; no source-body typing claim.
    reviewed = {path: value for path, value in reviewed.items() if is_application_source(Path(path))}
    drift = sorted(k for k in before.keys() | reviewed.keys() if before.get(k) != reviewed.get(k))
    issues, signatures, modules = check_parity()
    if drift:
        issues.append("Source differs from the reviewed snapshot; re-review these contracts: " + ", ".join(drift))
    print(f"Source/stub parity: {signatures} signatures, {len(modules)} importable leaf modules")
    if issues:
        print("\n".join(issues))
        return 1

    results = {}
    stages = [
        ("mypy-contracts", ["-m", "mypy", "--config-file", CONTRACT_CONFIG]),
        ("mypy-tooling", ["-m", "mypy", "--config-file", CONTRACT_CONFIG,
                          "typing/check.py", "typing/pacer_inventory.py", "typing/test_tooling.py"]),
        ("stubtest", ["-m", "mypy.stubtest", "--mypy-config-file", CONTRACT_CONFIG, "--allowlist", "typing/stubtest-allowlist.txt", *modules]),
        ("runtime-contracts", [str(HERE / "runtime_contracts.py")]),
        ("tooling-regressions", [str(HERE / "test_tooling.py")]),
    ]
    for name, arguments in stages:
        result = run(name, arguments)
        results[name] = result.returncode == 0
        print(f"{name}: {'PASS' if results[name] else 'FAIL'}")
        if not results[name]:
            print(result.stdout + result.stderr)
    results["negative-consumers"], description = negative_check()
    print("negative-consumers: " + description)
    after = source_hashes()
    results["source-stable"] = before == after
    inventory = dynamic_inventory()
    (EVIDENCE / "dynamic-boundaries.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    summary = {
        "scope": "External declarations, consumer typing, signatures, and offline record fixtures; not source-body or model-execution certification",
        "python": sys.version,
        "versions": {name: importlib.metadata.version(name) for name in ("mypy", "numpy", "Pillow", "typer", "fastapi", "rich")},
        "source_files": len(before), "source_signatures": signatures,
        "stubtest_leaf_modules": len(modules), "stubtest_allowlist_entries": 4,
        "dynamic_declarations": len(inventory), "results": results,
    }
    (EVIDENCE / "verification.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "source-after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
