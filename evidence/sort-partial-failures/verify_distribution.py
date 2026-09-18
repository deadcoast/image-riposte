"""Reuse the reviewed distribution probe without rewriting its historical evidence."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "sort_package_probe", ROOT / "evidence/sort-recovery/check_package.py"
)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.HERE = Path(__file__).resolve().parent
probe.INSTALLED = ROOT / "typing/.cache/sort-partial/installed"
probe.WHEEL = ROOT / "typing/.cache/sort-partial/dist/riposte_studio-0.5.0-py3-none-any.whl"
probe.SDIST = ROOT / "typing/.cache/sort-partial/dist/riposte_studio-0.5.0.tar.gz"
probe.main()
