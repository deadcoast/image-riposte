"""Fresh distribution equality and real source/wheel application-root checks."""
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

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / ".tmp/application-roots/dist"
INSTALLED = ROOT / ".tmp/application-roots/installed"


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"riposte_studio-{version}"
    sources = {p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    with ZipFile(DIST / f"{name}-py3-none-any.whl") as wheel, tarfile.open(DIST / f"{name}.tar.gz") as sdist:
        assert {n for n in wheel.namelist() if n.startswith("riposte/")} == set(sources)
        installed_sources = {p.relative_to(INSTALLED).as_posix() for p in (INSTALLED / "riposte").rglob("*")
                             if p.is_file() and "__pycache__" not in p.parts}
        assert installed_sources == set(sources)
        for path, data in sources.items():
            assert wheel.read(path) == sdist.extractfile(f"{name}/src/{path}").read() == (INSTALLED / path).read_bytes() == data
        for path in ("INSTALL.ps1", "INSTALL.sh", "START.ps1", "START.sh", "START.cmd", "riposte.cmd", "uv.lock",
                     "README.md", "docs/DESIGN.md", "docs/UX-CONTRACT.md", "docs/CLI.md", "docs/REBUILD.md"):
            assert sdist.extractfile(f"{name}/{path}").read() == (ROOT / path).read_bytes()

    source_program = """
import json,sys
from pathlib import Path
from typer.testing import CliRunner
from riposte.cli import app
from riposte.store import application_directory,check_root
from riposte.errors import RiposteError
root=Path(sys.argv[1]); scratch=Path(sys.argv[2])
assert application_directory()==root
for path in (root,root.parent,scratch):
    try: check_root(path)
    except RiposteError as exc: assert exc.code=='IMAGE_FOLDER_OVERLAPS_APPLICATION'
    else: raise AssertionError('accepted source overlap')
original=scratch/'original.png'; original.write_bytes(b'synthetic source guard fixture')
before=original.read_bytes(),original.stat().st_mtime_ns
result=CliRunner().invoke(app,['--json','sort',str(scratch),'--apply'])
assert result.exit_code==2 and json.loads(result.stderr)=={'error':'IMAGE_FOLDER_OVERLAPS_APPLICATION'}
assert not result.stdout and (original.read_bytes(),original.stat().st_mtime_ns)==before
assert sorted(p.name for p in scratch.iterdir())==['original.png']
print(json.dumps({'source_checkout':'PASS','cli_apply_descendant':'PASS'}))
"""
    installed_program = """
import json,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
from typer.testing import CliRunner
import riposte.store as store
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.server import create_app
from riposte.terminal.paths import validate_workspace,application_directory
from riposte.terminal.service import Request,execute
target=Path(sys.argv[1]); sibling=Path(sys.argv[2]); package=target/'riposte'
assert Path(store.__file__).resolve()==package/'store.py'
assert store.application_directory()==application_directory()==package
temporary=tempfile.TemporaryDirectory(prefix='root-probe-',dir=package)
child=Path(temporary.name)
original=child/'original.png'; Image.new('RGB',(24,16),(30,60,100)).save(original)
before=original.read_bytes(),original.stat().st_mtime_ns
for root in (package,target,child):
    for call in (lambda:store.check_root(root),lambda:validate_workspace(root),lambda:create_app(root),
                 lambda:organize(root),lambda:execute(Request('sort-riposte',root,{'all_images':True}))):
        try:call()
        except RiposteError as exc:assert exc.code=='IMAGE_FOLDER_OVERLAPS_APPLICATION',exc.code
        else:raise AssertionError('accepted installed overlap')
    result=CliRunner().invoke(app,['--json','sort',str(root),'--apply'])
    assert result.exit_code==2 and json.loads(result.stderr)=={'error':'IMAGE_FOLDER_OVERLAPS_APPLICATION'}
    assert not result.stdout and str(root) not in result.stderr
    assert not (root/'.riposte').exists() and not (root/'.riposte-operation.lease').exists()
assert (original.read_bytes(),original.stat().st_mtime_ns)==before
assert sorted(p.name for p in child.iterdir())==['original.png']
source=sibling/'original.png'; source.write_bytes(original.read_bytes())
before=source.read_bytes(),source.stat().st_mtime_ns
assert validate_workspace(sibling)==sibling
assert execute(Request('organize',sibling))['ready']
assert sorted(p.name for p in sibling.iterdir())==['original.png']
with TestClient(create_app(sibling,token='test')) as client:
    response=client.post('/api/category-rules',headers={'x-riposte-token':'test'},json={'review':True})
    assert response.status_code==200
result=CliRunner().invoke(app,['--json','sort',str(sibling),'--apply','--date-mode','modified'])
assert result.exit_code==0 and json.loads(result.stdout)['checkpoint']=='COMPLETE'
assert not source.exists()
preview=execute(Request('undo-sort',sibling))
assert execute(Request('undo-sort-apply',sibling,{'sort_id':preview['sort_id']}))['checkpoint']=='COMPLETE'
assert (source.read_bytes(),source.stat().st_mtime_ns)==before
temporary.cleanup()
print(json.dumps({'wheel_roots':'PASS','source_preserved':'PASS','sibling_sort_exact_undo':'PASS','api':'PASS'}))
"""
    checks = {}
    for key, program, import_path, first_arg in (
        ("source", source_program, ROOT / "src", ROOT),
        ("installed", installed_program, INSTALLED, INSTALLED),
    ):
        with tempfile.TemporaryDirectory(prefix=f"{key}-", dir=DIST.parent) as directory:
            completed = subprocess.run([sys.executable, "-c", program, str(first_arg), directory],
                                       cwd=directory, env={**os.environ, "PYTHONPATH": str(import_path), "PYTHONDONTWRITEBYTECODE": "1"},
                                       capture_output=True, text=True, encoding="utf-8", timeout=45)
            assert completed.returncode == 0, completed.stdout + completed.stderr
            checks[key] = json.loads(completed.stdout)
    return {"result": "PASS", "version": version, "application_files": len(sources), "checks": checks,
            "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DIST.iterdir()) if p.suffix in {".whl", ".gz"}},
            "scope": "Source/sdist/wheel/isolated-target equality; real source and installed package root/ancestor/descendant rejection; installed CLI/API/service/terminal and independent sibling sort/exact undo. Existing Windows Python/dependencies; not clean bootstrap or native Linux/macOS qualification."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
