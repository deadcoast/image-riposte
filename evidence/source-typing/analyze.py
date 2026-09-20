"""Compare diagnostic classes and review the limited executable statement changes."""
from pathlib import Path
import ast
from collections import Counter
import copy
import hashlib
import json
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def diagnostics(path):
    result = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"(.+?):\d+:\d+: error: .*?  \[([^]]+)\]$", line)
        if match:
            result[(match[1].replace("\\", "/"), match[2])] += 1
    return result


class WithoutTypes(ast.NodeTransformer):
    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None

    def visit_If(self, node):
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            return None
        return self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value is None:
            return None
        return ast.Assign(targets=[node.target], value=self.visit(node.value))

    def visit_arg(self, node):
        node.annotation = None
        return node

    def visit_FunctionDef(self, node):
        node.returns = None
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "cast":
            return self.visit(node.args[1])
        return self.generic_visit(node)


def functions(tree):
    rows = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            rows[node.name] = node
        if isinstance(node, ast.ClassDef):
            rows.update({f"{node.name}.{n.name}": n for n in node.body if isinstance(n, ast.FunctionDef)})
    return rows


def capture():
    before = diagnostics(HERE / "baseline.txt")
    after = diagnostics(HERE / "source-third.txt")
    assert sum(before.values()) == 1100 and sum(after.values()) == 876
    changes = [{"module": path, "code": code, "before": before[path, code], "after": after[path, code]}
               for path, code in sorted(before.keys() | after.keys()) if before[path, code] != after[path, code]]
    assert all(row["after"] < row["before"] for row in changes)
    modified = []
    statements = []
    casts = []
    with ZipFile(HERE / "source-before.zip") as archive:
        original = {name: archive.read(name) for name in archive.namelist()}
    baseline = json.loads((HERE / "baseline-command.json").read_text(encoding="utf-8-sig"))["sources"]
    assert {name: hashlib.sha256(value).hexdigest() for name, value in original.items()} == baseline
    for name, old in original.items():
        new = (ROOT / name).read_bytes()
        if old == new:
            continue
        modified.append(name)
        old_tree, new_tree = ast.parse(old), ast.parse(new)
        # No new Any expressions, ignores, deleted definitions.
        assert sum(isinstance(n, ast.Name) and n.id == "Any" for n in ast.walk(new_tree)) <= sum(
            isinstance(n, ast.Name) and n.id == "Any" for n in ast.walk(old_tree)), name
        assert new.count(b"type: ignore") <= old.count(b"type: ignore"), name
        old_functions, new_functions = functions(old_tree), functions(new_tree)
        assert old_functions.keys() == new_functions.keys(), name
        for key in old_functions:
            left = WithoutTypes().visit(copy.deepcopy(old_functions[key]))
            right = WithoutTypes().visit(copy.deepcopy(new_functions[key]))
            if ast.dump(left) != ast.dump(right):
                statements.append(f"{name}:{key}")
        for node in ast.walk(new_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "cast":
                casts.append({"path": name, "line": node.lineno, "type": ast.unparse(node.args[0])})
    expected = ["src/riposte/sort_history.py:_check", "src/riposte/terminal/controller.py:Controller._key",
                "src/riposte/terminal/service.py:execute", "src/riposte/terminal/service.py:image_selection"]
    assert sorted(statements) == sorted(expected), statements
    assert all(row["type"] not in {"Any", "object"} for row in casts)
    return {"result": "PASS", "baseline_diagnostics": 1100, "after_diagnostics": 876, "reduction": 224,
            "baseline_modules": len({p for p, _ in before}), "after_modules": len({p for p, _ in after}),
            "module_error_class_changes": changes, "modified_existing_sources": sorted(modified),
            "new_source": "src/riposte/records.py", "localized_casts": casts,
            "statement_changes_after_type_erasure": sorted(statements),
            "statement_review": {
                "sort_history._check": "Read-only Mapping alias of the same catalog row before comparing all expected keys; comparison and undo ordering retained.",
                "controller._key": "Distinct local name for report-view choices; two call-and-return branches return None, as the called existing batch/inspect_item methods do.",
                "service.execute": "Separate inspected/apply call branches retain identical policy and option values; explicit missing-destination check equals the preceding empty-dict lookup for validated CatalogRow values; filter fields remain year/month/size.",
                "service.image_selection": "Explicit year/month/size fields preserve the prior comprehension order and values."},
            "limits": ["AST erasure is a review aid, not proof of semantic equivalence; full runtime tests remain required.",
                       "Request default_factory changes from dict to the all-optional TypedDict constructor; both produce independent ordinary empty dictionaries.",
                       "Localized casts preserve producer-validated records and caller-established page/workspace/editor invariants; they add no runtime validation.",
                       "876 source diagnostics remain; diagnostic counts are not runtime defect counts."]}


if __name__ == "__main__":
    (HERE / "analysis.json").write_text(json.dumps(capture(), indent=2) + "\n", encoding="utf-8")
