"""Check fresh source/sdist/wheel/target equality and installed crash/undo."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIST = ROOT / ".tmp/workspace-lease/dist"
INSTALLED = ROOT / ".tmp/workspace-lease/installed"


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"riposte_studio-{version}"
    sources = {p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    with ZipFile(DIST / f"{name}-py3-none-any.whl") as wheel, tarfile.open(DIST / f"{name}.tar.gz") as sdist:
        assert {n for n in wheel.namelist() if n.startswith("riposte/")} == set(sources)
        for path, data in sources.items():
            assert wheel.read(path) == data
            assert sdist.extractfile(f"{name}/src/{path}").read() == data
            assert (INSTALLED / path).read_bytes() == data
        for path in ("INSTALL.ps1", "INSTALL.sh", "START.ps1", "START.sh", "START.cmd", "riposte.cmd", "uv.lock",
                     "README.md", "docs/DESIGN.md", "docs/UX-CONTRACT.md", "docs/CLI.md", "docs/REBUILD.md"):
            assert sdist.extractfile(f"{name}/{path}").read() == (ROOT / path).read_bytes()
    env = {**os.environ, "PYTHONPATH": str(INSTALLED)}
    with tempfile.TemporaryDirectory(dir=ROOT / ".tmp/workspace-lease") as directory:
        root = Path(directory)
        source = root / "private-original.png"
        Image.new("RGB", (48, 32), (40, 70, 110)).save(source)
        original, modified = source.read_bytes(), source.stat().st_mtime_ns
        origin = subprocess.check_output([sys.executable, "-c", "import riposte.locking; print(riposte.locking.__file__)"],
                                         cwd=root, env=env, text=True).strip()
        assert Path(origin).is_relative_to(INSTALLED)
        program = """
import os,sys
from pathlib import Path
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.sort_history import SortHistory
original=SortHistory.remove_source
def stopped(self,entry):
    original(self,entry)
    os._exit(23)
SortHistory.remove_source=stopped
organize(Path(sys.argv[1]),Policy(date_mode='modified'))
"""
        killed = subprocess.run([sys.executable, "-c", program, str(root)], cwd=root, env=env,
                                capture_output=True, text=True, timeout=20)
        assert killed.returncode == 23 and not source.exists(), killed.stderr
        def invoke(command, *options):
            run = subprocess.run([sys.executable, "-m", "riposte", "--json", command, str(root), *options],
                                 cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
            assert run.returncode == 0, run.stdout + run.stderr
            return json.loads(run.stdout)
        preview = invoke("undo-sort")
        assert preview["ready"]
        assert invoke("undo-sort", "--apply", "--sort-id", preview["sort_id"])["checkpoint"] == "COMPLETE"
        assert source.read_bytes() == original and source.stat().st_mtime_ns == modified
        assert not invoke("list")
        (root / ".riposte").rename(root / ".shroud")
        (root / ".shroud/WORKSPACE").write_text("SHROUD_WORKSPACE_1\n")
        assert invoke("upgrade")["status"] == "UPGRADED"
        assert invoke("sort")["ready"]
    return {"result": "PASS", "version": version, "application_files": len(sources),
            "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DIST.iterdir()) if p.suffix in {".whl", ".gz"}},
            "scope": "57-file source/sdist/wheel/isolated-target byte equality; shipping install/start/lockfile/README and declared documentation equality; installed child hard-exit, exact CLI undo and legacy upgrade. Existing Windows Python/dependencies; not a clean bootstrap or model qualification."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
