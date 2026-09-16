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


def source_hashes() -> dict[str, str]:
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "src").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
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


def run(name: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("MYPYPATH", None)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, *arguments], cwd=ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
        check=False, timeout=120,
    )
    (EVIDENCE / f"{name}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result


def negative_check() -> tuple[bool, str]:
    template = (HERE / "checks" / "rejected.py.txt").read_text(encoding="utf-8")
    path = HERE / ".cache" / "rejected.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    expected = Counter()
    for line, text in enumerate(template.splitlines(), 1):
        if "# error: " in text:
            for code in text.split("# error: ", 1)[1].split(","):
                expected[(line, code)] += 1
    result = run("negative-consumers", ["-m", "mypy", "--config-file", "mypy.ini", str(path)])
    actual = Counter((int(line), code) for line, code in re.findall(
        r"rejected\.py:(\d+):\d+: error: .*\[([a-z][a-z-]+)\]\r?$", result.stdout, re.MULTILINE))
    other_errors = sum(": error:" in line for line in result.stdout.splitlines()) != sum(actual.values())
    success = result.returncode == 1 and actual == expected and not other_errors
    return success, f"{sum(actual.values())}/{sum(expected.values())} expected diagnostics; exact line/code match={success}"


def dynamic_inventory() -> list[dict[str, object]]:
    rows = []
    for path in sorted((HERE / "stubs").rglob("*.pyi")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
            names = {part.id for annotation in annotations if annotation is not None
                     for part in ast.walk(annotation) if isinstance(part, ast.Name)}
            if names & {"Any", "Report", "ModelTensor"}:
                rows.append({"file": path.relative_to(ROOT).as_posix(), "line": node.lineno,
                             "declaration": ast.unparse(node).splitlines()[0]})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Audit implementation bodies without the stub path; existing errors remain nonzero.")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.source:
        result = run("source-current", ["-m", "mypy", "--config-file", "typing/mypy-source.ini", "--python-version", "3.13", "src/riposte"])
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    before = source_hashes()
    reviewed = json.loads((EVIDENCE / "source-before.json").read_text(encoding="utf-8"))
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
        ("mypy-contracts", ["-m", "mypy", "--config-file", "mypy.ini"]),
        ("stubtest", ["-m", "mypy.stubtest", "--mypy-config-file", "mypy.ini", "--allowlist", "typing/stubtest-allowlist.txt", *modules]),
        ("runtime-contracts", [str(HERE / "runtime_contracts.py")]),
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
