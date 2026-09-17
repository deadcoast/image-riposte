"""Regression checks for discovery scope and source identity, using temporary files."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import check


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
