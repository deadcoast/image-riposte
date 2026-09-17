"""Regression checks for discovery scope and source identity, using temporary files."""
from __future__ import annotations

import os
import contextlib
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import check
import pacer_inventory as inventory


class TypingToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(dir=check.HERE / ".cache")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / "src/riposte").mkdir(parents=True)
        (self.root / "src/riposte/__init__.py").write_text("", encoding="utf-8")
        self.source = self.root / "src/riposte/value.py"
        self.source.write_text('answer: int = "bad"\n', encoding="utf-8")

    def test_default_and_dot_reach_source_errors_despite_build_and_stub_copies(self) -> None:
        (self.root / "mypy.ini").write_bytes((check.ROOT / "mypy.ini").read_bytes())
        for folder in ("build/lib", "history/v0", "packages/old"):
            package = self.root / folder / "riposte"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
        stubs = self.root / "typing/stubs/riposte"
        stubs.mkdir(parents=True)
        (stubs / "__init__.pyi").write_text("", encoding="utf-8")
        (stubs / "value.pyi").write_text("answer: int\n", encoding="utf-8")
        env = os.environ.copy()
        env.pop("MYPYPATH", None)
        env.pop("PYTHONPATH", None)
        for targets in ([], ["."], ["src/riposte"]):
            with self.subTest(targets=targets):
                result = subprocess.run(
                    [sys.executable, "-m", "mypy", *targets], cwd=self.root,
                    env=env, text=True, capture_output=True, timeout=60,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("[assignment]", result.stdout)
                self.assertIn("value.py:1:", result.stdout)
                self.assertIn("checked 2 source files", result.stdout)
                self.assertNotIn("Duplicate module", result.stdout)
                self.assertNotIn("errors prevented further checking", result.stdout)

    def test_generated_metadata_is_not_application_identity(self) -> None:
        with patch.object(check, "ROOT", self.root):
            before = check.source_hashes()
            metadata = self.root / "src/riposte_studio.egg-info"
            metadata.mkdir()
            requires = metadata / "requires.txt"
            requires.write_text("mypy>=2.3.1\n", encoding="utf-8")
            self.assertEqual(check.source_hashes(), before)
            requires.write_text("mypy>=2.4\n", encoding="utf-8")
            self.assertEqual(check.source_hashes(), before)

    def test_changed_application_file_is_detected(self) -> None:
        with patch.object(check, "ROOT", self.root):
            before = check.source_hashes()
            self.source.write_text("answer: int = 1\n", encoding="utf-8")
            self.assertNotEqual(check.source_hashes(), before)

    def test_added_application_file_is_detected(self) -> None:
        with patch.object(check, "ROOT", self.root):
            before = check.source_hashes()
            (self.root / "src/riposte/new.py").write_text("value = 1\n", encoding="utf-8")
            self.assertNotEqual(check.source_hashes(), before)

    def test_removed_application_file_is_detected(self) -> None:
        with patch.object(check, "ROOT", self.root):
            before = check.source_hashes()
            self.source.unlink()
            self.assertNotEqual(check.source_hashes(), before)

    def test_structured_report_is_not_a_dynamic_report_alias(self) -> None:
        stubs = self.root / "stubs"
        stubs.mkdir()
        (stubs / "reports.pyi").write_text(
            "from _riposte_types import Report as DynamicReport\n"
            "from typing import Any\n"
            "class Report:\n    title: str\n"
            "def structured() -> Report: ...\n"
            "def extension() -> DynamicReport: ...\n"
            "def opaque() -> Any: ...\n",
            encoding="utf-8",
        )
        with patch.object(check, "ROOT", self.root), patch.object(check, "HERE", self.root):
            declarations = [str(row["declaration"]) for row in check.dynamic_inventory()]
        self.assertEqual(len(declarations), 2)
        self.assertTrue(any("extension" in row for row in declarations))
        self.assertTrue(any("opaque" in row for row in declarations))

    def test_source_audit_uses_project_environment_and_explicit_override(self) -> None:
        application = self.root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        application.parent.mkdir(parents=True)
        application.touch()
        with patch.object(check, "ROOT", self.root):
            self.assertEqual(check.source_interpreter(), application)
            self.assertEqual(check.source_interpreter(Path(sys.executable)), Path(sys.executable).absolute())
            application.unlink()
            with self.assertRaisesRegex(ValueError, "Application Python is missing"):
                check.source_interpreter()

    def test_symbols_cover_public_private_class_and_async_dependencies(self) -> None:
        provider = self.root / "src/riposte/provider.py"
        provider.write_text("LIMIT = 3\ndef _private(): return LIMIT\n", encoding="utf-8")
        self.source.write_text(
            "from .provider import _private as invoke\n"
            "class Controller:\n"
            "    def refresh(self): return invoke()\n"
            "    async def run(self): return self.refresh()\n", encoding="utf-8")
        tool = self.root / "typing/pacer_inventory.py"
        tool.parent.mkdir()
        tool.write_text("def tool(): pass\n", encoding="utf-8")
        paths = ["src/riposte/value.py", "src/riposte/provider.py"]
        with patch.object(inventory, "ROOT", self.root):
            records = inventory.symbol_inventory(paths)
        rows = {f"{r['Path']}:{r['Symbol']}": r for r in records}
        refresh = rows["src/riposte/value.py:Controller.refresh"]
        self.assertIn("src/riposte/provider.py:_private", refresh["Requires"])
        self.assertIn("src/riposte/value.py:Controller.refresh", rows["src/riposte/value.py:Controller.run"]["Requires"])
        self.assertEqual(rows["src/riposte/provider.py:LIMIT"]["AssetType"], "CONFIG")
        self.assertIn("src/riposte/provider.py:LIMIT", rows["src/riposte/provider.py:_private"]["Requires"])

    def test_symbol_local_shadow_does_not_invent_import_dependency(self) -> None:
        provider = self.root / "src/riposte/provider.py"
        provider.write_text("def run(): pass\n", encoding="utf-8")
        self.source.write_text("from .provider import run\ndef caller(run): return run()\n", encoding="utf-8")
        tool = self.root / "typing/pacer_inventory.py"
        tool.parent.mkdir()
        tool.write_text("", encoding="utf-8")
        with patch.object(inventory, "ROOT", self.root):
            rows = inventory.symbol_inventory(["src/riposte/value.py", "src/riposte/provider.py"])
        self.assertEqual(next(r for r in rows if r["Symbol"] == "caller")["Requires"], "src/riposte/value.py")

    def test_reconciliation_rejects_missing_symbol_and_dependency(self) -> None:
        tool = self.root / "typing/pacer_inventory.py"
        tool.parent.mkdir()
        tool.write_text("def tool(): pass\n", encoding="utf-8")
        evidence = self.root / "typing/evidence"
        evidence.mkdir()
        reviewed = evidence / "reviewed.json"
        reviewed.write_text(json.dumps({p.relative_to(self.root).as_posix(): inventory.digest(p)
                                       for p in (self.root / 'src').rglob('*.py')}), encoding="utf-8")
        stages = {name: True for name in ("mypy-contracts", "mypy-tooling", "stubtest", "runtime-contracts",
                                         "tooling-regressions", "negative-consumers", "source-stable")}
        (evidence / "verification.json").write_text(json.dumps({"results": stages}), encoding="utf-8")
        stubs = self.root / "typing/stubs/riposte"
        stubs.mkdir(parents=True)
        (stubs / "__init__.pyi").write_text("", encoding="utf-8")
        (stubs / "value.pyi").write_text("answer: int\n", encoding="utf-8")
        columns = ["ID", "AssetType", "Path", "Symbol", "Purpose", "Exports", "Imports", "Requires", "Tags"]

        def save(rows: list[dict[str, str]]) -> None:
            with (self.root / "overlord.PACER.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)

        plan = self.root / "plan.json"
        report = evidence / "inventory.json"
        with patch.object(inventory, "ROOT", self.root), patch.object(inventory, "REPORT", report), \
             patch.object(inventory, "REVIEWED_SOURCE", reviewed), \
             patch.object(inventory, "INPUTS", ("typing/pacer_inventory.py",)), contextlib.redirect_stdout(io.StringIO()):
            save([])
            self.assertFalse(inventory.reconcile(plan))
            rows = [op["row"] for op in json.loads(plan.read_text(encoding="utf-8")) if op["op"] == "add"]
            save(rows)
            self.assertTrue(inventory.reconcile())
            symbol = next(row for row in rows if row.get("Symbol") == "answer")
            save([row for row in rows if row is not symbol])
            self.assertFalse(inventory.reconcile())
            self.assertIn("Unregistered symbol: src/riposte/value.py:answer", json.loads(report.read_text(encoding="utf-8"))["issues"])
            symbol["Requires"] = ""
            save(rows)
            self.assertFalse(inventory.reconcile())
            self.assertTrue(any("Stale symbol: src/riposte/value.py:answer" in issue for issue in json.loads(report.read_text(encoding="utf-8"))["issues"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
